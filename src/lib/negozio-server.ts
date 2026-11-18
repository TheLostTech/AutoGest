// Negozio pubblico, lato server: quale azienda vende online e come si leggono le richieste dei visitatori. Solo server.
import type { AuthContext } from "better-auth";
import { auth } from "@/lib/auth/server";
import { idAziendaValido } from "@/lib/accesso/id-azienda";
import { richiestaDellApp } from "@/lib/collegamenti-server";

const NO_STORE = { "Cache-Control": "no-store" };
export const risposta = (body: unknown, status = 200) => Response.json(body, { status, headers: NO_STORE });

const g = globalThis as typeof globalThis & { __aziendaDemo?: { id: string | null; fino: number } };

/**
 * L'azienda del negozio: NEGOZIO_AZIENDA (id dell'azienda); se manca, l'azienda demo (metadata {"demo":true}).
 * Nessuna delle due: null (catalogo vuoto, ordini 503). La demo si cerca nella tabella delle aziende e si ricorda
 * (se manca, si riprova dopo qualche secondo: l'azienda demo può nascere mentre il server è acceso).
 */
export async function aziendaNegozio(): Promise<string | null> {
  const env = process.env.NEGOZIO_AZIENDA?.trim();
  if (env) return idAziendaValido(env) ? env : null;
  const c = g.__aziendaDemo;
  if (c && (c.id || c.fino > Date.now())) return c.id;
  let id: string | null = null;
  try {
    const ctx = (await auth.$context) as unknown as AuthContext;
    const righe = await ctx.adapter.findMany<{ id: string; metadata?: unknown }>({ model: "organization" });
    id =
      righe.find((o) => {
        try {
          const m = typeof o.metadata === "string" ? JSON.parse(o.metadata) : o.metadata;
          return typeof m === "object" && m !== null && (m as { demo?: unknown }).demo === true;
        } catch {
          return false;
        }
      })?.id ?? null;
  } catch (e) {
    console.error("Azienda del negozio non trovata", e);
  }
  g.__aziendaDemo = { id, fino: Date.now() + 10_000 };
  return id;
}

/**
 * Le richieste pubbliche che scrivono (ordine, pagamento): stesso sito, JSON, al massimo 2 KB.
 * Restituisce il corpo già letto o la risposta di errore.
 */
export async function corpoPubblico(req: Request): Promise<Record<string, unknown> | Response> {
  if (!richiestaDellApp(req)) return risposta({ error: "Richiesta non consentita." }, 403);
  const dichiarata = Number(req.headers.get("content-length") ?? 0);
  if (dichiarata > 2048) return risposta({ error: "Richiesta troppo grande." }, 413);
  const testo = await req.text().catch(() => "");
  if (Buffer.byteLength(testo) > 2048) return risposta({ error: "Richiesta troppo grande." }, 413);
  try {
    const b = JSON.parse(testo);
    if (b && typeof b === "object" && !Array.isArray(b)) return b as Record<string, unknown>;
  } catch {
    // sotto
  }
  return risposta({ error: "Richiesta non valida." }, 400);
}
