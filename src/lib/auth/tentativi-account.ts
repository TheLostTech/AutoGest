import { randomUUID } from "node:crypto";
import type { AuthContext, BetterAuthPlugin } from "better-auth";
import { APIError, createAuthMiddleware } from "better-auth/api";
import { aggiungiEventi } from "@/lib/archivio-azienda";
import { chiaveAccount, chiudi, prenota, tentativoSconosciuto, type Esito, type StatoAccount } from "@/lib/accesso/tentativi-account";
import { deposito } from "@/lib/deposito";

// Blocco per account dell'accesso con email (regole in accesso/tentativi-account.ts). Lo stato di ogni account sta nel
// deposito (aggiornaContoAccount: lettura e scrittura insieme, per chiave), così vale anche con più istanze del server.
// Il contatore comune delle email inesistenti resta in memoria per istanza: protegge solo dalla raffica.
// Prima dell'endpoint (hook "before"): si cerca l'utente; per un account vero si prenota il tentativo con un gettone
// legato a QUESTA richiesta (WeakMap sulla Request), per un'email inesistente si conta nel contatore comune.
// Dopo l'endpoint (hook "after", che gira anche quando l'endpoint risponde con un errore): si chiude proprio quel gettone.
// Se l'esito non arriva (errore imprevisto), il gettone scade da solo dopo 60 secondi.
const CHIAVE = Symbol.for("gestionale.tentativi-account");
const g = globalThis as typeof globalThis & { [CHIAVE]?: { sconosciuti: number[]; inCorso: WeakMap<Request, { k: string; gettone: string; userId: string }> } };
const stato = (g[CHIAVE] ??= { sconosciuti: [], inCorso: new WeakMap() });

// Nel registro di ogni azienda dell'account: il responsabile vede che qualcuno prova la password di un collega
async function registraBlocco(c: AuthContext, userId: string) {
  const u = await c.internalAdapter.findUserById(userId).catch(() => null);
  if (!u) return;
  const membri = await c.adapter.findMany<{ organizationId: string }>({ model: "member", where: [{ field: "userId", value: userId }] });
  for (const m of membri) {
    await aggiungiEventi(m.organizationId, [
      { user: u.name, role: "sistema", device: "Server", entity: "sistema", entityId: userId, action: "Accesso bloccato per 15 minuti", detail: "10 password sbagliate in 15 minuti" },
    ]).catch((e) => console.error("[tentativi] registro non scritto", e));
  }
}

// Stessa risposta per email inesistenti e account bloccati: il rifiuto non dice se l'account esiste
const troppi = () => new APIError("TOO_MANY_REQUESTS", { message: "Troppi tentativi di accesso: riprova più tardi.", code: "TROPPI_TENTATIVI" });

const codice = (r: unknown): number | undefined => (r && typeof r === "object" && "statusCode" in r ? Number((r as { statusCode: unknown }).statusCode) : undefined);
const vuoto = (): StatoAccount => ({ errori: [], bloccatoFino: null, inVolo: new Map() });
// prenota/chiudi lavorano su una Map: si passa quella con il solo conto di questa chiave e si rimette il risultato
function sulConto<R>(k: string, op: (conti: Map<string, StatoAccount>, ora: number) => R) {
  return deposito().aggiornaContoAccount(k, (prima) => {
    const conti = new Map<string, StatoAccount>(prima ? [[k, prima]] : []);
    const risultato = op(conti, Date.now()); // l'ora si prende col lock in mano, non prima dell'attesa
    return { stato: conti.get(k) ?? vuoto(), risultato };
  });
}
/**
 * Dopo l'accesso: chiude il gettone di questa richiesta e, se scatta il blocco, lo scrive nel registro. Non lancia mai:
 * a questo punto la sessione è già creata, e un errore qui diventerebbe un 500 con la password giusta (e una sessione
 * rimasta senza nessuno). Se il deposito non risponde l'errore va nel log: il blocco lo controlla comunque l'hook
 * "before", e il gettone rimasto aperto scade da solo dopo 60 secondi.
 */
export async function chiudiTentativo(c: AuthContext, p: { k: string; gettone: string; userId: string }, esito: Esito): Promise<void> {
  try {
    if (await sulConto(p.k, (conti, adesso) => chiudi(conti, p.k, p.gettone, adesso, esito))) await registraBlocco(c, p.userId);
  } catch (e) {
    console.error("[tentativi] esito dell'accesso non registrato (il gettone scade da solo in 60 secondi)", e);
  }
}
/**
 * Per un hook "before" che gira dopo questo e rifiuta l'accesso (conferma-titolare.ts): l'hook "after" allora non
 * gira, e il gettone di questa richiesta si chiude da qui con il suo esito. Non lancia mai.
 */
export async function chiudiTentativoDellaRichiesta(c: AuthContext, request: Request | undefined, esito: Esito): Promise<void> {
  const p = request ? stato.inCorso.get(request) : undefined;
  if (!p || !request) return;
  stato.inCorso.delete(request);
  await chiudiTentativo(c, p, esito);
}
/**
 * Controllo di una password fuori da /sign-in/email (conferma dell'email, api/conferma) con lo stesso blocco per
 * account: prenota il tentativo, verifica, chiude con l'esito. 10 password sbagliate in 15 minuti → bloccato 15 minuti.
 */
export async function verificaConBlocco(c: AuthContext, userId: string, verifica: () => Promise<boolean>): Promise<"bloccato" | "sbagliata" | "giusta"> {
  const p = { k: `u:${userId}`, gettone: randomUUID(), userId };
  if ((await sulConto(p.k, (conti, adesso) => prenota(conti, p.k, p.gettone, adesso))) === "bloccato") return "bloccato";
  let giusta: boolean;
  try {
    giusta = await verifica();
  } catch (e) {
    await chiudiTentativo(c, p, "altro");
    throw e;
  }
  await chiudiTentativo(c, p, giusta ? "giusta" : "sbagliata");
  return giusta ? "giusta" : "sbagliata";
}
const chiaveDi = (ctx: { body?: unknown }) => chiaveAccount((ctx.body as { email?: unknown } | undefined)?.email);

export const tentativiAccount = {
  id: "tentativi-account",
  hooks: {
    before: [
      {
        matcher: (ctx) => ctx.path === "/sign-in/email",
        handler: createAuthMiddleware(async (ctx) => {
          const email = chiaveDi(ctx);
          if (!email || !ctx.request) return;
          const u = await ctx.context.internalAdapter.findUserByEmail(email).catch(() => null);
          // Il conteggio è atomico per account nel deposito: le richieste parallele si vedono a vicenda
          const ora = Date.now();
          if (!u?.user) {
            if (!tentativoSconosciuto(stato.sconosciuti, ora)) throw troppi();
            return;
          }
          const k = `u:${u.user.id}`;
          const gettone = randomUUID();
          if ((await sulConto(k, (conti, adesso) => prenota(conti, k, gettone, adesso))) === "bloccato") throw troppi();
          stato.inCorso.set(ctx.request, { k, gettone, userId: u.user.id });
        }),
      },
    ],
    after: [
      {
        matcher: (ctx) => ctx.path === "/sign-in/email",
        handler: createAuthMiddleware(async (ctx) => {
          const p = ctx.request ? stato.inCorso.get(ctx.request) : undefined;
          if (!p || !ctx.request) return;
          stato.inCorso.delete(ctx.request);
          const st = codice(ctx.context.returned);
          const esito: Esito = st === 401 ? "sbagliata" : st === undefined || st < 400 ? "giusta" : "altro";
          await chiudiTentativo(ctx.context, p, esito);
        }),
      },
    ],
  },
} satisfies BetterAuthPlugin;
