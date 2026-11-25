// Conferma dell'email del titolare che si è registrato da solo (spec prova-15-giorni, Task 5). Solo server.
// - L'email di conferma parte solo per un titolare "in attesa": email non verificata, responsabile di un'azienda
//   registrata con abbonamento "nuovo" e senza fine della prova. Per chiunque altro l'endpoint risponde uguale e non
//   manda nulla (niente email a dipendenti o account già confermati).
// - Il link porta a /conferma, che chiede la password scelta alla registrazione; /api/conferma la controlla (con il
//   blocco per account) e solo allora fa verificare l'email a Better Auth. Alla verifica (afterEmailVerification):
//   partono i 15 giorni, la scheda della registrazione segna la conferma, il registro lo scrive e si chiudono le
//   sessioni dell'utente; poi /api/conferma apre quella nuova.
// - Prima della conferma il titolare non entra con email e password (hook "before" su /sign-in/email). Gli altri utenti
//   (dipendenti con email non verificata, super admin) non sono toccati: niente requireEmailVerification.
import type { AuthContext, BetterAuthPlugin, User } from "better-auth";
import { APIError, createAuthMiddleware } from "better-auth/api";
import { avviaProva } from "@/lib/abbonamento";
import { aggiornaAbbonamento, leggiAbbonamento } from "@/lib/abbonamento-server";
import { CODICE_DA_CONFERMARE, linkConferma, MESSAGGIO_DA_CONFERMARE } from "@/lib/accesso/conferma";
import { ruoliDaStringa } from "@/lib/accesso/ruoli";
import { aggiungiEventi } from "@/lib/archivio-azienda";
import type { SchedaRegistrazione } from "@/lib/consensi";
import { deposito } from "@/lib/deposito";
import { inviaEmail } from "@/lib/email/invia";
import { emailConferma } from "@/lib/email/modelli";
import { chiudiTentativoDellaRichiesta } from "./tentativi-account";

/** Il link dell'email vale 48 ore (in secondi, come vuole Better Auth). */
export const DURATA_LINK_S = 48 * 3600;

const registrata = (metadata: unknown): boolean => {
  try {
    const m = typeof metadata === "string" ? JSON.parse(metadata) : metadata;
    return typeof m === "object" && m !== null && (m as { registrata?: unknown }).registrata === true;
  } catch {
    return false;
  }
};

type Membro = { organizationId: string; role: string };

/**
 * Aziende registrate di cui l'utente è responsabile e che aspettano la conferma: abbonamento "nuovo" senza fine della
 * prova. Serve l'abbonamento scritto (la registrazione lo scrive prima di creare il titolare): uno assente o illeggibile
 * non conta, così una nuova registrazione non può togliere un'azienda di cui non si sa lo stato. Un errore del
 * database arriva a chi chiama.
 */
export async function aziendeInAttesa(c: AuthContext, userId: string): Promise<string[]> {
  const membri = await c.adapter.findMany<Membro>({ model: "member", where: [{ field: "userId", value: userId }] });
  const esito: string[] = [];
  for (const m of membri) {
    if (!ruoliDaStringa(m.role).includes("responsabile")) continue;
    const org = await c.adapter.findOne<{ id: string; metadata?: unknown }>({ model: "organization", where: [{ field: "id", value: m.organizationId }] });
    if (!org || !registrata(org.metadata)) continue;
    const a = await leggiAbbonamento(org.id);
    if (a && a.stato === "nuovo" && a.fineProva === null) esito.push(org.id);
  }
  return esito;
}

/** Titolare che non ha ancora confermato l'email. */
export async function daConfermare(c: AuthContext, user: { id: string; emailVerified?: boolean | null }): Promise<boolean> {
  return user.emailVerified !== true && (await aziendeInAttesa(c, user.id)).length > 0;
}

/**
 * Registrazione rimasta in sospeso con questa email, che una nuova registrazione può sostituire: l'utente non ha
 * confermato, non è super admin e ogni sua azienda è una registrazione in attesa in cui è l'unico membro.
 * Restituisce le aziende da togliere, o null (email di un titolare confermato, di un dipendente, del super admin: 409).
 */
export async function registrazioneInSospeso(c: AuthContext, user: { id: string; emailVerified?: boolean | null; role?: string | null }): Promise<string[] | null> {
  if (user.emailVerified === true) return null;
  if ((user.role ?? "").split(",").map((r) => r.trim()).includes("superadmin")) return null;
  const membri = await c.adapter.findMany<Membro>({ model: "member", where: [{ field: "userId", value: user.id }] });
  if (!membri.length) return null;
  const inAttesa = new Set(await aziendeInAttesa(c, user.id));
  for (const m of membri) {
    if (!inAttesa.has(m.organizationId)) return null;
    const tutti = await c.adapter.findMany<Membro>({ model: "member", where: [{ field: "organizationId", value: m.organizationId }] });
    if (tutti.length !== 1) return null;
  }
  return [...inAttesa];
}

/** sendVerificationEmail: solo al titolare in attesa; per gli altri non parte nulla (la risposta resta la stessa). */
// Il link porta alla nostra pagina /conferma con il gettone di Better Auth (non al suo /verify-email): per confermare
// serve anche la password scelta alla registrazione (api/conferma). In produzione l'indirizzo è solo quello pubblico.
export async function inviaConferma(c: AuthContext, d: { user: User; token: string }, request?: Request): Promise<void> {
  if (!(await daConfermare(c, d.user))) return;
  const link = linkConferma(d.token, request ? new URL(request.url).origin : null);
  await inviaEmail({ ...emailConferma(d.user.name, link), a: d.user.email });
}

/**
 * afterEmailVerification: chiude le sessioni dell'utente (l'accesso automatico ne apre una nuova subito dopo) e fa
 * partire la prova delle sue aziende in attesa. Se non riesce, l'email torna "da confermare" e l'errore arriva a
 * Better Auth: lo stesso link si può riaprire. Scheda e registro, dopo, non fermano la conferma.
 */
export async function dopoConferma(c: AuthContext, user: User, ora = Date.now()): Promise<void> {
  const partite: string[] = [];
  try {
    await c.internalAdapter.deleteUserSessions(user.id);
    for (const id of await aziendeInAttesa(c, user.id)) {
      let partita = false;
      await aggiornaAbbonamento(id, (a) => {
        if (!a) throw new Error("Abbonamento non più presente");
        const dopo = avviaProva(a, ora);
        partita = a.fineProva === null && dopo.fineProva !== null;
        return dopo;
      });
      if (partita) partite.push(id);
    }
  } catch (e) {
    console.error("Conferma dell'email non completata: la prova non è partita", user.id, e);
    await c.internalAdapter.updateUser(user.id, { emailVerified: false }).catch((x: unknown) => console.error("Email non riportata a da confermare", user.id, x));
    throw new APIError("INTERNAL_SERVER_ERROR", { message: "Non è stato possibile confermare l'email adesso. Riapri il link tra qualche minuto." });
  }
  const quando = new Date(ora).toISOString();
  for (const id of partite) {
    try {
      await deposito().aggiornaDocumento<SchedaRegistrazione, null>(id, "registrazione", (s) =>
        s ? { dati: { ...s, confermata: s.confermata ?? quando }, risultato: null } : { dati: s as unknown as SchedaRegistrazione, risultato: null, nonScrivere: true },
      );
    } catch (e) {
      console.error("Scheda della registrazione non aggiornata", id, e);
    }
    try {
      await aggiungiEventi(id, [
        { user: user.name, role: "responsabile", device: "Email", entity: "sistema", entityId: id, action: "Email confermata: prova di 15 giorni iniziata", detail: user.email },
      ]);
    } catch (e) {
      console.error("Registro attività non aggiornato", id, e);
    }
  }
}

/** Opzioni emailVerification di Better Auth. `contesto` dà l'AuthContext (auth.$context) al momento della chiamata. */
export function opzioniConferma(contesto: () => Promise<AuthContext>) {
  return {
    sendVerificationEmail: async (d: { user: User; url: string; token: string }, request?: Request) => inviaConferma(await contesto(), d, request),
    expiresIn: DURATA_LINK_S,
    // L'accesso lo apre /api/conferma dopo la verifica (signInEmail), già nell'azienda del titolare
    autoSignInAfterVerification: false,
    afterEmailVerification: async (user: User) => dopoConferma(await contesto(), user),
  };
}

const daConfermareErrore = () => new APIError("FORBIDDEN", { message: MESSAGGIO_DA_CONFERMARE, code: CODICE_DA_CONFERMARE });

/**
 * Il titolare in attesa non entra con email e password. Gira dopo il blocco per account (tentativi-account), così un
 * account bloccato resta bloccato. Solo con la password giusta si dice di confermare: con quella sbagliata risponde
 * l'endpoint (401, contato), come per tutti, e la risposta non rivela che l'account aspetta la conferma.
 */
export const confermaTitolare = {
  id: "conferma-titolare",
  hooks: {
    before: [
      {
        matcher: (ctx) => ctx.path === "/sign-in/email",
        handler: createAuthMiddleware(async (ctx) => {
          const b = (ctx.body ?? {}) as { email?: unknown; password?: unknown };
          const email = typeof b.email === "string" ? b.email.trim().toLowerCase() : "";
          if (!email || typeof b.password !== "string") return;
          let rifiuta = false;
          try {
            const u = await ctx.context.internalAdapter.findUserByEmail(email, { includeAccounts: true });
            if (!u || u.user.emailVerified || !(await aziendeInAttesa(ctx.context, u.user.id)).length) return;
            const hash = u.accounts.find((a) => a.providerId === "credential")?.password;
            rifiuta = !!hash && (await ctx.context.password.verify({ hash, password: b.password }));
          } catch (e) {
            await chiudiTentativoDellaRichiesta(ctx.context, ctx.request, "altro");
            throw e;
          }
          if (!rifiuta) return;
          await chiudiTentativoDellaRichiesta(ctx.context, ctx.request, "giusta");
          throw daConfermareErrore();
        }),
      },
    ],
  },
} satisfies BetterAuthPlugin;
