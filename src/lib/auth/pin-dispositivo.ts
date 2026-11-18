import { createHash, randomBytes } from "node:crypto";
import type { AuthContext, BetterAuthPlugin } from "better-auth";
import { APIError, createAuthEndpoint, createAuthMiddleware } from "better-auth/api";
import { deleteSessionCookie, setSessionCookie } from "better-auth/cookies";
import { aggiungiEventi, type NuovoEvento } from "@/lib/archivio-azienda";
import {
  bloccoAttivo,
  dopoTentativo,
  pinValido,
  PIN_BLOCCHI_DISATTIVA,
  PIN_ERRORI_DISPOSITIVO,
  PIN_ERRORI_DISPOSITIVO_GIORNO,
  PIN_FINESTRA_DISPOSITIVO_MS,
  type StatoPinDispositivo,
  type StatoPinUtente,
} from "@/lib/accesso/pin";
import { PIN_TURNO_MS } from "@/lib/accesso/regole";
import { chiudiAssistenzeAperte } from "./assistenza-chiusura";
import type { Accesso } from "@/lib/accesso/regole";

// Dispositivi condivisi dell'azienda (tablet del piazzale) e accesso con nome + PIN.
// Il dispositivo riceve un cookie casuale di lunga durata; sul server c'è solo il suo hash SHA-256.
// Senza quel cookie (valido e non revocato) nessun endpoint PIN dice nulla: né nomi né azienda.

export const COOKIE_DISPOSITIVO = "dispositivo";
const DISPOSITIVO_MAX_AGE_S = 400 * 24 * 60 * 60; // 400 giorni, il massimo dei browser
const NOME_MAX = 60;

type RigaDispositivo = {
  id: string;
  organizationId: string;
  nome: string;
  tokenHash: string;
  creatoDa: string;
  creato: Date | string;
  revocato?: Date | string | null;
  bloccato: boolean | number;
  erroriPin: string;
};
type RigaPin = {
  id: string;
  userId: string;
  organizationId: string;
  pinHash: string;
  errori: number;
  bloccatoFino?: Date | string | null;
  blocchi?: string | null; // JSON: istanti dei blocchi di 15 minuti nelle ultime 24 ore
  pinDisattivato?: boolean | number | null;
};
type RigaUtente = { id: string; name: string; role?: string | null; banned?: boolean | null; banExpires?: Date | string | null };

const ms = (d: Date | string | null | undefined): number | null => (d === null || d === undefined ? null : new Date(d).getTime());
const hashToken = (t: string) => createHash("sha256").update(t).digest("hex");

function erroriDa(json: string | null | undefined): number[] {
  try {
    const v = JSON.parse(json ?? "[]") as unknown;
    return Array.isArray(v) ? v.filter((x): x is number => typeof x === "number") : [];
  } catch {
    return [];
  }
}

function utenteUtilizzabile(u: RigaUtente | null, ora: number): u is RigaUtente {
  if (!u) return false;
  // Il super admin non entra mai con un PIN
  if ((u.role ?? "").split(",").map((r) => r.trim()).includes("superadmin")) return false;
  if (u.banned) {
    const fine = ms(u.banExpires);
    if (fine === null || fine > ora) return false;
  }
  return true;
}

// I tentativi di PIN di un'azienda vanno in fila: due richieste parallele non leggono lo stesso contatore
// (altrimenti si proverebbero molti PIN prima che il blocco scatti). Un solo processo Node: basta in memoria.
const CODA = Symbol.for("gestionale.pin-dispositivo.code");
const g = globalThis as typeof globalThis & { [CODA]?: Map<string, Promise<unknown>> };
const code = (g[CODA] ??= new Map());
// Esportata come inFilaPin: anche lo sblocco dalla Piattaforma passa da questa fila (non si azzera un contatore a metà tentativo).
export const inFilaPin = <T>(aziendaId: string, fn: () => Promise<T>): Promise<T> => inFila(aziendaId, fn);
function inFila<T>(chiave: string, fn: () => Promise<T>): Promise<T> {
  const run = (code.get(chiave) ?? Promise.resolve()).then(fn);
  const coda = run.catch(() => undefined);
  code.set(chiave, coda);
  void coda.then(() => {
    if (code.get(chiave) === coda) code.delete(chiave);
  });
  return run;
}

async function dispositivoDaToken(c: AuthContext, token: string | null | undefined): Promise<RigaDispositivo | null> {
  if (!token || token.length > 200) return null;
  const d = await c.adapter.findOne<RigaDispositivo>({ model: "dispositivo", where: [{ field: "tokenHash", value: hashToken(token) }] });
  if (!d || d.revocato) return null;
  return d;
}

/** Il valore del cookie del dispositivo da un'intestazione Cookie (senza Better Auth: serve anche ad accessoDaRichiesta). */
function cookieDispositivo(cookie: string | null | undefined): string | null {
  for (const parte of (cookie ?? "").split(";")) {
    const i = parte.indexOf("=");
    if (i < 0 || parte.slice(0, i).trim() !== COOKIE_DISPOSITIVO) continue;
    try {
      return decodeURIComponent(parte.slice(i + 1).trim()) || null;
    } catch {
      return null;
    }
  }
  return null;
}

/** Il browser è un dispositivo condiviso registrato e non revocato (cookie valido)? Per il blocco di inattività di ogni sessione su di esso. */
export async function dispositivoDelBrowser(c: AuthContext, intestazioneCookie: string | null | undefined): Promise<{ id: string; organizationId: string } | null> {
  const d = await dispositivoDaToken(c, cookieDispositivo(intestazioneCookie));
  return d ? { id: d.id, organizationId: d.organizationId } : null;
}

/** Chiude la sessione di questo browser (con le eventuali assistenze aperte del suo utente) e toglie il cookie. */
async function chiudiSessioneDelBrowser(ctx: { context: AuthContext; getSignedCookie: (n: string, s: string) => Promise<string | null | false> }, motivo: string) {
  const c = ctx.context;
  const token = await ctx.getSignedCookie(c.authCookies.sessionToken.name, c.secret);
  if (!token) return;
  const s = await c.adapter.findOne<{ userId: string }>({ model: "session", where: [{ field: "token", value: token }] });
  if (s) await chiudiAssistenzeAperte(c, s.userId, motivo).catch(() => undefined);
  await c.internalAdapter.deleteSession(token).catch(() => undefined);
}

async function registra(aziendaId: string, eventi: NuovoEvento[]) {
  // Il registro è utile ma non deve far fallire l'accesso o il blocco
  await aggiungiEventi(aziendaId, eventi).catch((e) => console.error("[pin-dispositivo] registro non scritto", e));
}

// Responsabile dell'azienda (o super admin in assistenza, che ha tutti i ruoli), con la regola unica di accesso.
// Import dinamico: accesso/server importa `auth`, che a sua volta carica questo plugin.
async function responsabile(headers: Headers | undefined, conPassword: boolean): Promise<Accesso> {
  const { accessoDaRichiesta } = await import("@/lib/accesso/server");
  const a = await accessoDaRichiesta(new Request("http://localhost/", { headers: headers ?? new Headers() }));
  if (a instanceof Response) {
    const j = (await a.json().catch(() => ({}))) as { error?: string; motivo?: string };
    // Scheda partita con un'altra azienda: 409 come le altre API, così il browser si ferma e chiede di ricaricare
    if (a.status === 409) throw new APIError("CONFLICT", { message: j.error ?? "Azienda cambiata.", code: "AZIENDA_CAMBIATA" });
    throw new APIError(a.status === 401 ? "UNAUTHORIZED" : "FORBIDDEN", { message: j.error ?? "Accesso negato." });
  }
  if (!a.ruoli.includes("responsabile")) throw new APIError("FORBIDDEN", { message: "Solo il responsabile gestisce i dispositivi." });
  if (conPassword && a.tipo !== "password") throw new APIError("FORBIDDEN", { message: "Serve l'accesso con email e password." });
  return a;
}

const firma = (a: Accesso) => ({ user: a.assistenza ? `${a.utente.nome} (assistenza)` : a.utente.nome, role: a.assistenza ? "sistema" : "responsabile", device: a.dispositivo?.nome ?? "Browser" });

function testo(v: unknown, max: number): string | null {
  return typeof v === "string" && v.trim() && v.length <= max ? v.trim() : null;
}

async function dispositivoDellAzienda(c: AuthContext, id: unknown, aziendaId: string): Promise<RigaDispositivo> {
  const d = typeof id === "string" ? await c.adapter.findOne<RigaDispositivo>({ model: "dispositivo", where: [{ field: "id", value: id }] }) : null;
  // Un dispositivo di un'altra azienda risponde come uno inesistente
  if (!d || d.organizationId !== aziendaId) throw new APIError("NOT_FOUND", { message: "Dispositivo non trovato." });
  return d;
}

/** Salva (o sostituisce) il PIN di un membro per un'azienda; azzera errori, blocchi e disattivazione. Per le pagine di gestione utenti. */
export async function impostaPin(c: AuthContext, userId: string, organizationId: string, pin: string): Promise<void> {
  if (!pinValido(pin)) throw new Error("PIN non valido: servono 4 cifre.");
  const pinHash = await c.password.hash(pin);
  const where = [
    { field: "userId", value: userId },
    { field: "organizationId", value: organizationId },
  ];
  const esiste = await c.adapter.findOne<RigaPin>({ model: "pinUtente", where });
  if (esiste) await c.adapter.update({ model: "pinUtente", where: [{ field: "id", value: esiste.id }], update: { pinHash, ...PIN_LIBERO } });
  else await c.adapter.create({ model: "pinUtente", data: { userId, organizationId, pinHash, ...PIN_LIBERO } });
}

const PIN_LIBERO = { errori: 0, bloccatoFino: null, blocchi: "[]", pinDisattivato: false };

// Con una sessione da PIN, dalle API di Better Auth si può solo uscire (e usare gli endpoint PIN): niente
// get-session (che rinnoverebbe la sessione a 7 giorni e azzererebbe l'inattività), cambio azienda, profilo, ecc.
const PERCORSI_PIN = (p: string) => p === "/sign-out" || p === "/ok" || p.startsWith("/pin-dispositivo/");

// Percorsi che aprono una sessione nuova (accesso con email, secondo passo col codice): permessi anche da un browser
// con una sessione da PIN, che però viene chiusa prima.
const APRE_SESSIONE = (p: string) => p.startsWith("/sign-in/") || p.startsWith("/two-factor/");

type SessioneConTipo = { tipoAccesso?: string | null };

// Hash di confronto per i tentativi su nomi inesistenti: stesso lavoro di una verifica vera.
let hashFinto: Promise<string> | null = null;

export const pinDispositivo = () =>
  ({
    id: "pin-dispositivo",
    schema: {
      dispositivo: {
        modelName: "dispositivo",
        fields: {
          organizationId: { type: "string", required: true, references: { model: "organization", field: "id", onDelete: "cascade" }, index: true },
          nome: { type: "string", required: true },
          tokenHash: { type: "string", required: true, unique: true },
          creatoDa: { type: "string", required: true },
          creato: { type: "date", required: true },
          revocato: { type: "date", required: false },
          bloccato: { type: "boolean", required: true, defaultValue: false },
          erroriPin: { type: "string", required: true, defaultValue: "[]" },
        },
      },
      pinUtente: {
        modelName: "pinUtente",
        fields: {
          userId: { type: "string", required: true, references: { model: "user", field: "id", onDelete: "cascade" }, index: true },
          organizationId: { type: "string", required: true, references: { model: "organization", field: "id", onDelete: "cascade" }, index: true },
          pinHash: { type: "string", required: true },
          errori: { type: "number", required: true, defaultValue: 0 },
          bloccatoFino: { type: "date", required: false },
          blocchi: { type: "string", required: false, defaultValue: "[]" },
          pinDisattivato: { type: "boolean", required: false, defaultValue: false },
        },
      },
    },
    init() {
      return {
        options: {
          databaseHooks: {
            session: {
              update: {
                // Rinnovo di Better Auth (scrive expiresAt + updatedAt): mai per una sessione da PIN, che ha un turno
                // fisso di 10 ore e la sua inattività la segna solo accessoDaRichiesta (che scrive soltanto updatedAt).
                async before(data: Record<string, unknown>, ctx: unknown) {
                  if (!("expiresAt" in data)) return;
                  const sessione = (ctx as { context?: { session?: { session?: SessioneConTipo } | null } } | null)?.context?.session?.session;
                  if (sessione?.tipoAccesso === "pin") return false;
                },
              },
            },
          },
        },
      };
    },
    hooks: {
      before: [
        {
          // Solo richieste HTTP: le chiamate interne (auth.api da accessoDaRichiesta) non passano di qui
          matcher: (ctx) => !!ctx.request && !PERCORSI_PIN(ctx.path ?? ""),
          handler: createAuthMiddleware(async (ctx) => {
            const token = await ctx.getSignedCookie(ctx.context.authCookies.sessionToken.name, ctx.context.secret);
            if (!token) return;
            const s = await ctx.context.adapter.findOne<SessioneConTipo>({ model: "session", where: [{ field: "token", value: token }] });
            if (s?.tipoAccesso !== "pin") return;
            // Accesso con email (o secondo passo col codice) da un browser con una sessione da PIN: chi sceglie di
            // entrare con l'account esce dal PIN. La sessione PIN si chiude subito, prima che ne nasca una nuova, così
            // non ne resta nessuna vecchia (nemmeno se la password è sbagliata). Il responsabile può sempre entrare.
            if (APRE_SESSIONE(ctx.path ?? "")) {
              await ctx.context.internalAdapter.deleteSession(token);
              return;
            }
            throw new APIError("FORBIDDEN", { message: "Con l'accesso a PIN questa funzione non è disponibile.", code: "SESSIONE_PIN" });
          }),
        },
      ],
    },
    endpoints: {
      registraDispositivo: createAuthEndpoint("/pin-dispositivo/registra", { method: "POST" }, async (ctx) => {
        const a = await responsabile(ctx.headers, true);
        const nome = testo((ctx.body as { nome?: unknown } | undefined)?.nome, NOME_MAX);
        if (!nome) throw new APIError("BAD_REQUEST", { message: `Dai un nome al dispositivo (al massimo ${NOME_MAX} caratteri).` });
        const c = ctx.context;
        // Se il browser era già un dispositivo registrato, quello vecchio si revoca: un browser, un dispositivo.
        const vecchio = await dispositivoDaToken(c, ctx.getCookie(COOKIE_DISPOSITIVO));
        if (vecchio) await c.adapter.update({ model: "dispositivo", where: [{ field: "id", value: vecchio.id }], update: { revocato: new Date() } });

        const token = randomBytes(32).toString("base64url");
        const d = await c.adapter.create<Record<string, unknown>, RigaDispositivo>({
          model: "dispositivo",
          data: { organizationId: a.azienda.id, nome, tokenHash: hashToken(token), creatoDa: a.utente.id, creato: new Date(), bloccato: false, erroriPin: "[]" },
        });
        ctx.setCookie(COOKIE_DISPOSITIVO, token, { httpOnly: true, sameSite: "lax", path: "/", maxAge: DISPOSITIVO_MAX_AGE_S });
        await registra(a.azienda.id, [{ ...firma(a), entity: "sistema", entityId: d.id, action: "Dispositivo registrato", detail: nome }]);
        // Da ora il browser è un dispositivo condiviso: la sessione con password del responsabile si chiude qui,
        // così il prossimo che lo prende in mano trova l'elenco dei nomi e non il suo account.
        await chiudiSessioneDelBrowser(ctx, "dispositivo registrato");
        deleteSessionCookie(ctx);
        return ctx.json({ id: d.id, nome });
      }),

      nomiDispositivo: createAuthEndpoint("/pin-dispositivo/nomi", { method: "GET" }, async (ctx) => {
        const c = ctx.context;
        const cookie = ctx.getCookie(COOKIE_DISPOSITIVO);
        const d = await dispositivoDaToken(c, cookie);
        if (!d) {
          // Cookie revocato o sconosciuto: si toglie, così il browser torna all'accesso con email
          if (cookie) ctx.setCookie(COOKIE_DISPOSITIVO, "", { httpOnly: true, sameSite: "lax", path: "/", maxAge: 0 });
          throw new APIError("UNAUTHORIZED", { message: "Questo browser non è un dispositivo dell'azienda." });
        }
        const ora = Date.now();
        const org = await c.adapter.findOne<{ name: string }>({ model: "organization", where: [{ field: "id", value: d.organizationId }] });
        const pin = await c.adapter.findMany<RigaPin>({ model: "pinUtente", where: [{ field: "organizationId", value: d.organizationId }] });
        const membri = await c.adapter.findMany<{ userId: string }>({ model: "member", where: [{ field: "organizationId", value: d.organizationId }] });
        const ids = new Set(membri.map((m) => m.userId));
        const conPin = pin.filter((p) => ids.has(p.userId));
        const utenti = conPin.length
          ? await c.adapter.findMany<RigaUtente>({ model: "user", where: [{ field: "id", operator: "in", value: conPin.map((p) => p.userId) }] })
          : [];
        const perId = new Map(utenti.map((u) => [u.id, u]));
        const nomi = conPin
          .flatMap((p) => {
            const u = perId.get(p.userId) ?? null;
            if (!utenteUtilizzabile(u, ora)) return [];
            const fino = ms(p.bloccatoFino);
            return [{ userId: u.id, nome: u.name, bloccato: !!p.pinDisattivato || (fino !== null && fino > ora) }];
          })
          .sort((x, y) => x.nome.localeCompare(y.nome, "it"));
        ctx.setHeader("Cache-Control", "no-store");
        return ctx.json({ azienda: org?.name ?? "", dispositivo: d.nome, bloccato: !!d.bloccato, nomi });
      }),

      entraConPin: createAuthEndpoint("/pin-dispositivo/entra", { method: "POST" }, async (ctx) => {
        const body = (ctx.body ?? {}) as { userId?: unknown; pin?: unknown };
        const userId = testo(body.userId, 200);
        const pin = typeof body.pin === "string" ? body.pin : "";
        if (!userId || !pinValido(pin)) throw new APIError("BAD_REQUEST", { message: "Scegli il nome e scrivi le 4 cifre del PIN." });
        const c = ctx.context;
        const primo = await dispositivoDaToken(c, ctx.getCookie(COOKIE_DISPOSITIVO));
        if (!primo) throw new APIError("UNAUTHORIZED", { message: "Questo browser non è un dispositivo dell'azienda." });
        const aziendaId = primo.organizationId;

        const esito = await inFila(aziendaId, async () => {
          const ora = Date.now();
          // Riletto dentro la fila: errori e blocco aggiornati dal tentativo precedente
          const d = await c.adapter.findOne<RigaDispositivo>({ model: "dispositivo", where: [{ field: "id", value: primo.id }] });
          if (!d || d.revocato) throw new APIError("UNAUTHORIZED", { message: "Questo browser non è un dispositivo dell'azienda." });
          const riga = await c.adapter.findOne<RigaPin>({
            model: "pinUtente",
            where: [
              { field: "userId", value: userId },
              { field: "organizationId", value: aziendaId },
            ],
          });
          const membro = riga
            ? await c.adapter.findOne<{ id: string }>({
                model: "member",
                where: [
                  { field: "userId", value: userId },
                  { field: "organizationId", value: aziendaId },
                ],
              })
            : null;
          const utente = membro ? await c.adapter.findOne<RigaUtente>({ model: "user", where: [{ field: "id", value: userId }] }) : null;
          const valido = !!riga && !!membro && utenteUtilizzabile(utente, ora);

          const stato: { utente: StatoPinUtente; dispositivo: StatoPinDispositivo } = {
            utente: valido
              ? { errori: riga!.errori ?? 0, bloccatoFino: ms(riga!.bloccatoFino), blocchi: erroriDa(riga!.blocchi), disattivato: !!riga!.pinDisattivato }
              : { errori: 0, bloccatoFino: null, blocchi: [], disattivato: false },
            dispositivo: { errori: erroriDa(d.erroriPin), bloccato: !!d.bloccato },
          };
          const blocco = bloccoAttivo(stato, ora);
          if (blocco) return { esito: blocco, d, utente: valido ? utente : null, appena: null, disattivato: stato.utente.disattivato } as const;

          // Confronto a tempo costante dell'hasher di Better Auth; per i nomi non validi si fa lo stesso lavoro
          let corretto: boolean;
          if (valido) corretto = await c.password.verify({ hash: riga!.pinHash, password: pin });
          else {
            hashFinto ??= c.password.hash("0000");
            await c.password.verify({ hash: await hashFinto, password: pin });
            corretto = false;
          }
          const r = dopoTentativo(stato, corretto, ora);

          if (r.dispositivo.errori.join() !== stato.dispositivo.errori.join() || r.dispositivo.bloccato !== stato.dispositivo.bloccato) {
            await c.adapter.update({
              model: "dispositivo",
              where: [{ field: "id", value: d.id }],
              update: { erroriPin: JSON.stringify(r.dispositivo.errori), bloccato: r.dispositivo.bloccato },
            });
          }
          if (valido && JSON.stringify(r.utente) !== JSON.stringify(stato.utente)) {
            await c.adapter.update({
              model: "pinUtente",
              where: [{ field: "id", value: riga!.id }],
              update: {
                errori: r.utente.errori,
                bloccatoFino: r.utente.bloccatoFino === null ? null : new Date(r.utente.bloccatoFino),
                blocchi: JSON.stringify(r.utente.blocchi),
                pinDisattivato: r.utente.disattivato,
              },
            });
          }
          const eventi: NuovoEvento[] = [];
          const nomeAppenaBloccato = valido && r.utente.bloccatoFino !== null && stato.utente.bloccatoFino !== r.utente.bloccatoFino;
          const dispositivoAppenaBloccato = r.dispositivo.bloccato && !stato.dispositivo.bloccato;
          const pinAppenaDisattivato = valido && r.utente.disattivato && !stato.utente.disattivato;
          if (pinAppenaDisattivato) {
            eventi.push({ user: utente!.name, role: "sistema", device: d.nome, entity: "sistema", entityId: userId, action: "PIN disattivato", detail: `${PIN_BLOCCHI_DISATTIVA} blocchi in 24 ore: serve un nuovo PIN dal responsabile` });
          } else if (nomeAppenaBloccato) {
            eventi.push({ user: utente!.name, role: "sistema", device: d.nome, entity: "sistema", entityId: userId, action: "Nome bloccato per 15 minuti", detail: "5 PIN sbagliati di fila" });
          }
          if (dispositivoAppenaBloccato) {
            const inBreve = r.dispositivo.errori.filter((t) => ora - t < PIN_FINESTRA_DISPOSITIVO_MS).length >= PIN_ERRORI_DISPOSITIVO;
            const perche = inBreve ? `${PIN_ERRORI_DISPOSITIVO} PIN sbagliati in 15 minuti` : `${PIN_ERRORI_DISPOSITIVO_GIORNO} PIN sbagliati in 24 ore`;
            eventi.push({ user: "Sistema", role: "sistema", device: d.nome, entity: "sistema", entityId: d.id, action: "Dispositivo bloccato", detail: `${perche}: serve lo sblocco del responsabile` });
          }
          if (eventi.length) await registra(aziendaId, eventi);
          const appena = dispositivoAppenaBloccato ? "dispositivo" : pinAppenaDisattivato ? "disattivato" : nomeAppenaBloccato ? "nome" : null;
          return { esito: r.esito, d, utente: valido ? utente : null, appena, disattivato: false } as const;
        });

        // Il tentativo che fa scattare un blocco lo dice subito (il nome bloccato compare comunque nell'elenco)
        if (esito.appena === "dispositivo") throw new APIError("FORBIDDEN", { message: "PIN non corretto. Dispositivo bloccato per troppi PIN sbagliati: serve il responsabile.", code: "DISPOSITIVO_BLOCCATO" });
        if (esito.appena === "disattivato") throw new APIError("FORBIDDEN", { message: "PIN non corretto. Troppi blocchi oggi: il PIN è disattivato, chiedi al responsabile un PIN nuovo.", code: "PIN_DISATTIVATO" });
        if (esito.appena === "nome") throw new APIError("FORBIDDEN", { message: "PIN non corretto. Nome bloccato per 15 minuti.", code: "NOME_BLOCCATO" });
        if (esito.esito === "dispositivo-bloccato") throw new APIError("FORBIDDEN", { message: "Dispositivo bloccato per troppi PIN sbagliati: serve il responsabile.", code: "DISPOSITIVO_BLOCCATO" });
        if (esito.esito === "utente-bloccato" && esito.disattivato) throw new APIError("FORBIDDEN", { message: "PIN disattivato per troppi errori: chiedi al responsabile un PIN nuovo.", code: "PIN_DISATTIVATO" });
        if (esito.esito === "utente-bloccato") throw new APIError("FORBIDDEN", { message: "Nome bloccato per troppi PIN sbagliati: riprova tra 15 minuti.", code: "NOME_BLOCCATO" });
        if (esito.esito !== "ok" || !esito.utente) throw new APIError("UNAUTHORIZED", { message: "PIN non corretto.", code: "PIN_SBAGLIATO" });

        // Una sessione già aperta su questo browser (es. il responsabile che ha registrato il tablet) si chiude.
        await chiudiSessioneDelBrowser(ctx, "accesso con PIN sullo stesso browser");

        const ora = Date.now();
        const session = await c.internalAdapter.createSession(
          esito.utente.id,
          false,
          {
            activeOrganizationId: aziendaId,
            tipoAccesso: "pin",
            dispositivoId: esito.d.id,
            dueFattoriVerificato: false,
            expiresAt: new Date(ora + PIN_TURNO_MS),
          },
          true, // overrideAll: la scadenza di 10 ore resta quella scritta qui
        );
        if (!session) throw new APIError("INTERNAL_SERVER_ERROR", { message: "Non riesco ad aprire la sessione." });
        const user = await c.internalAdapter.findUserById(esito.utente.id);
        if (!user) throw new APIError("UNAUTHORIZED", { message: "PIN non corretto.", code: "PIN_SBAGLIATO" });
        await setSessionCookie(ctx, { session, user }, false, { maxAge: Math.floor(PIN_TURNO_MS / 1000) });
        return ctx.json({ ok: true });
      }),

      elencoDispositivi: createAuthEndpoint("/pin-dispositivo/elenco", { method: "GET" }, async (ctx) => {
        const a = await responsabile(ctx.headers, false);
        const c = ctx.context;
        const righe = await c.adapter.findMany<RigaDispositivo>({
          model: "dispositivo",
          where: [{ field: "organizationId", value: a.azienda.id }],
          sortBy: { field: "creato", direction: "desc" },
        });
        const questo = ctx.getCookie(COOKIE_DISPOSITIVO);
        const hashQuesto = questo ? hashToken(questo) : null;
        const autori = righe.length
          ? await c.adapter.findMany<{ id: string; name: string }>({ model: "user", where: [{ field: "id", operator: "in", value: [...new Set(righe.map((r) => r.creatoDa))] }] })
          : [];
        const nomeAutore = new Map(autori.map((u) => [u.id, u.name]));
        ctx.setHeader("Cache-Control", "no-store");
        return ctx.json({
          passwordSession: a.tipo === "password",
          dispositivi: righe.map((r) => ({
            id: r.id,
            nome: r.nome,
            creato: new Date(r.creato).toISOString(),
            creatoDa: nomeAutore.get(r.creatoDa) ?? "",
            revocato: r.revocato ? new Date(r.revocato).toISOString() : null,
            bloccato: !!r.bloccato,
            questo: r.tokenHash === hashQuesto,
          })),
        });
      }),

      revocaDispositivo: createAuthEndpoint("/pin-dispositivo/revoca", { method: "POST" }, async (ctx) => {
        const a = await responsabile(ctx.headers, true);
        const c = ctx.context;
        const d = await dispositivoDellAzienda(c, (ctx.body as { dispositivoId?: unknown } | undefined)?.dispositivoId, a.azienda.id);
        if (!d.revocato) {
          await c.adapter.update({ model: "dispositivo", where: [{ field: "id", value: d.id }], update: { revocato: new Date() } });
          // Le sessioni da PIN aperte su quel dispositivo finiscono subito
          const aperte = await c.adapter.findMany<{ token: string }>({ model: "session", where: [{ field: "dispositivoId", value: d.id }] });
          for (const s of aperte) await c.internalAdapter.deleteSession(s.token);
          await registra(a.azienda.id, [{ ...firma(a), entity: "sistema", entityId: d.id, action: "Dispositivo revocato", detail: d.nome }]);
        }
        return ctx.json({ ok: true });
      }),

      sbloccaDispositivo: createAuthEndpoint("/pin-dispositivo/sblocca", { method: "POST" }, async (ctx) => {
        const a = await responsabile(ctx.headers, true);
        const c = ctx.context;
        const d = await dispositivoDellAzienda(c, (ctx.body as { dispositivoId?: unknown } | undefined)?.dispositivoId, a.azienda.id);
        if (d.revocato) throw new APIError("BAD_REQUEST", { message: "Il dispositivo è revocato: va registrato di nuovo." });
        await inFila(d.organizationId, () =>
          c.adapter.update({ model: "dispositivo", where: [{ field: "id", value: d.id }], update: { bloccato: false, erroriPin: "[]" } }),
        );
        await registra(a.azienda.id, [{ ...firma(a), entity: "sistema", entityId: d.id, action: "Dispositivo sbloccato", detail: d.nome }]);
        // Sbloccato proprio questo browser (il responsabile è entrato con la password sul tablet bloccato): la sua
        // sessione si chiude qui, così il tablet torna all'elenco dei nomi e non resta aperto sul suo account.
        const questo = ctx.getCookie(COOKIE_DISPOSITIVO);
        if (questo && hashToken(questo) === d.tokenHash) {
          await chiudiSessioneDelBrowser(ctx, "dispositivo sbloccato");
          deleteSessionCookie(ctx);
          return ctx.json({ ok: true, esci: true });
        }
        return ctx.json({ ok: true });
      }),
    },
  }) satisfies BetterAuthPlugin;
