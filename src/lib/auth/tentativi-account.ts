import { randomUUID } from "node:crypto";
import type { AuthContext, BetterAuthPlugin } from "better-auth";
import { APIError, createAuthMiddleware } from "better-auth/api";
import { aggiungiEventi } from "@/lib/archivio-azienda";
import { chiaveAccount, chiudi, prenota, tentativoSconosciuto, type Conti, type Esito } from "@/lib/accesso/tentativi-account";

// Blocco per account dell'accesso con email (regole in accesso/tentativi-account.ts). In memoria sulla globalThis,
// un solo processo Node: un riavvio azzera i conti (come il limite per IP).
// Prima dell'endpoint (hook "before"): si cerca l'utente; per un account vero si prenota il tentativo con un gettone
// legato a QUESTA richiesta (WeakMap sulla Request), per un'email inesistente si conta nel contatore comune.
// Dopo l'endpoint (hook "after", che gira anche quando l'endpoint risponde con un errore): si chiude proprio quel gettone.
// Se l'esito non arriva (errore imprevisto), il gettone scade da solo dopo 60 secondi.
const CHIAVE = Symbol.for("gestionale.tentativi-account");
const g = globalThis as typeof globalThis & { [CHIAVE]?: { conti: Conti; sconosciuti: number[]; inCorso: WeakMap<Request, { k: string; gettone: string; userId: string }> } };
const stato = (g[CHIAVE] ??= { conti: new Map(), sconosciuti: [], inCorso: new WeakMap() });

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

const codice = (r: unknown): number | undefined => (r && typeof r === "object" && "statusCode" in r ? Number((r as { statusCode: unknown }).statusCode) : undefined);
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
          // Da qui in poi nessun await fino al conteggio: le richieste parallele si vedono a vicenda
          const ora = Date.now();
          if (!u?.user) {
            if (!tentativoSconosciuto(stato.sconosciuti, ora)) throw new APIError("TOO_MANY_REQUESTS", { message: "Troppi tentativi di accesso: riprova tra un minuto.", code: "TROPPI_TENTATIVI" });
            return;
          }
          const k = `u:${u.user.id}`;
          const gettone = randomUUID();
          if (prenota(stato.conti, k, gettone, ora) === "bloccato") {
            throw new APIError("TOO_MANY_REQUESTS", { message: "Troppe password sbagliate per questo account: riprova tra 15 minuti.", code: "ACCOUNT_BLOCCATO" });
          }
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
          if (chiudi(stato.conti, p.k, p.gettone, Date.now(), esito)) await registraBlocco(ctx.context, p.userId);
        }),
      },
    ],
  },
} satisfies BetterAuthPlugin;
