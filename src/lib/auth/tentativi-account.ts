import type { AuthContext, BetterAuthPlugin } from "better-auth";
import { APIError, createAuthMiddleware } from "better-auth/api";
import { aggiungiEventi } from "@/lib/archivio-azienda";
import { accountBloccato, chiaveAccount, daRicordare, dopoPasswordSbagliata, type StatoAccount } from "@/lib/accesso/tentativi-account";

// Blocco per account dell'accesso con email (regola in accesso/tentativi-account.ts). In memoria sulla globalThis,
// un solo processo Node: un riavvio azzera i conti (come il limite per IP). Al massimo MAX_VOCI account ricordati.
const MAX_VOCI = 10_000;
const CHIAVE = Symbol.for("gestionale.tentativi-account");
const g = globalThis as typeof globalThis & { [CHIAVE]?: Map<string, StatoAccount> };
const conti = (g[CHIAVE] ??= new Map());

function ricorda(k: string, s: StatoAccount, ora: number) {
  conti.delete(k);
  if (daRicordare(s, ora)) conti.set(k, s);
  if (conti.size <= MAX_VOCI) return;
  for (const [kk, ss] of conti) if (!daRicordare(ss, ora)) conti.delete(kk);
  // Ancora troppi: si dimenticano i più vecchi (inseriti per primi), mai quelli bloccati
  for (const [kk, ss] of conti) {
    if (conti.size <= MAX_VOCI) break;
    if (!accountBloccato(ss, ora)) conti.delete(kk);
  }
}

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

export const tentativiAccount = {
  id: "tentativi-account",
  hooks: {
    before: [
      {
        matcher: (ctx) => ctx.path === "/sign-in/email",
        handler: createAuthMiddleware(async (ctx) => {
          const k = chiaveAccount((ctx.body as { email?: unknown } | undefined)?.email);
          if (k && accountBloccato(conti.get(k), Date.now())) {
            throw new APIError("TOO_MANY_REQUESTS", { message: "Troppe password sbagliate per questo account: riprova tra 15 minuti.", code: "ACCOUNT_BLOCCATO" });
          }
        }),
      },
    ],
    after: [
      {
        matcher: (ctx) => ctx.path === "/sign-in/email",
        handler: createAuthMiddleware(async (ctx) => {
          const k = chiaveAccount((ctx.body as { email?: unknown } | undefined)?.email);
          if (!k) return;
          const ora = Date.now();
          const st = stato(ctx.context.returned);
          if (st === 401) {
            const r = dopoPasswordSbagliata(conti.get(k), ora);
            ricorda(k, r.stato, ora);
            if (r.appenaBloccato) await registraBlocco(ctx.context, k);
          } else if (st === undefined || st < 400) {
            // Password giusta: si riparte da zero (il secondo fattore ha il suo blocco per account)
            conti.delete(k);
          }
        }),
      },
    ],
  },
} satisfies BetterAuthPlugin;
