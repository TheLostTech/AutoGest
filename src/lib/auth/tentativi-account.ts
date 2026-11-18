import type { AuthContext, BetterAuthPlugin } from "better-auth";
import { APIError, createAuthMiddleware } from "better-auth/api";
import { aggiungiEventi } from "@/lib/archivio-azienda";
import { chiaveAccount, chiudi, prenota, type Conti, type Esito } from "@/lib/accesso/tentativi-account";

// Blocco per account dell'accesso con email (regole in accesso/tentativi-account.ts). In memoria sulla globalThis,
// un solo processo Node: un riavvio azzera i conti (come il limite per IP).
// Il tentativo si conta all'arrivo (hook "before", sincrono fra controllo e conteggio) e si chiude con l'esito (hook
// "after", che gira anche quando l'endpoint risponde con un errore); se l'esito non arriva, la prenotazione scade da sola.
const CHIAVE = Symbol.for("gestionale.tentativi-account");
const g = globalThis as typeof globalThis & { [CHIAVE]?: Conti };
const conti = (g[CHIAVE] ??= new Map());

// Nel registro di ogni azienda dell'account: il responsabile vede che qualcuno prova la password di un collega
async function registraBlocco(c: AuthContext, email: string) {
  const u = await c.internalAdapter.findUserByEmail(email).catch(() => null);
  if (!u?.user) return;
  const membri = await c.adapter.findMany<{ organizationId: string }>({ model: "member", where: [{ field: "userId", value: u.user.id }] });
  for (const m of membri) {
    await aggiungiEventi(m.organizationId, [
      { user: u.user.name, role: "sistema", device: "Server", entity: "sistema", entityId: u.user.id, action: "Accesso bloccato per 15 minuti", detail: "10 password sbagliate in 15 minuti" },
    ]).catch((e) => console.error("[tentativi] registro non scritto", e));
  }
}

const stato = (r: unknown): number | undefined => (r && typeof r === "object" && "statusCode" in r ? Number((r as { statusCode: unknown }).statusCode) : undefined);
const chiaveDi = (ctx: { body?: unknown }) => chiaveAccount((ctx.body as { email?: unknown } | undefined)?.email);

export const tentativiAccount = {
  id: "tentativi-account",
  hooks: {
    before: [
      {
        matcher: (ctx) => ctx.path === "/sign-in/email",
        handler: createAuthMiddleware(async (ctx) => {
          const k = chiaveDi(ctx);
          if (!k) return;
          // Nessun await fra controllo e conteggio: le richieste parallele si vedono a vicenda
          const p = prenota(conti, k, Date.now());
          if (p === "bloccato") throw new APIError("TOO_MANY_REQUESTS", { message: "Troppe password sbagliate per questo account: riprova tra 15 minuti.", code: "ACCOUNT_BLOCCATO" });
          if (p === "pieno") throw new APIError("TOO_MANY_REQUESTS", { message: "Troppi tentativi di accesso in corso: riprova tra qualche minuto.", code: "TROPPI_TENTATIVI" });
        }),
      },
    ],
    after: [
      {
        matcher: (ctx) => ctx.path === "/sign-in/email",
        handler: createAuthMiddleware(async (ctx) => {
          const k = chiaveDi(ctx);
          if (!k) return;
          const st = stato(ctx.context.returned);
          // 429 da questo stesso plugin: nessuna prenotazione da chiudere
          if (st === 429) return;
          const esito: Esito = st === 401 ? "sbagliata" : st === undefined || st < 400 ? "giusta" : "altro";
          if (chiudi(conti, k, Date.now(), esito)) await registraBlocco(ctx.context, k);
        }),
      },
    ],
  },
} satisfies BetterAuthPlugin;
