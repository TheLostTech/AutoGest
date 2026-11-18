// Negozio pubblico, lato server: quale azienda vende online e come si leggono le richieste dei visitatori. Solo server.
import type { AuthContext } from "better-auth";
import { auth } from "@/lib/auth/server";
import { rispostaNonPronta } from "@/lib/accesso/pronta";
import { idAziendaValido } from "@/lib/accesso/id-azienda";
import { richiestaDellApp } from "@/lib/collegamenti-server";

const NO_STORE = { "Cache-Control": "no-store" };
export const risposta = (body: unknown, status = 200) => Response.json(body, { status, headers: NO_STORE });

const MAX_CORPO = 2048;
const g = globalThis as typeof globalThis & { __aziendaNegozio?: { dati: DatiNegozio | null; fino: number } };

export type DatiNegozio = { id: string; demo: boolean };

const eDemo = (metadata: unknown): boolean => {
  try {
    const m = typeof metadata === "string" ? JSON.parse(metadata) : metadata;
    return typeof m === "object" && m !== null && (m as { demo?: unknown }).demo === true;
  } catch {
    return false;
  }
};

/**
 * L'azienda del negozio: NEGOZIO_AZIENDA (id dell'azienda); se manca, l'azienda demo (metadata {"demo":true}).
 * Nessuna delle due: null (catalogo vuoto, ordini 503). Si ricorda per 10 secondi (l'azienda demo può nascere con il server acceso).
 * demo: il pagamento simulato vale solo se l'azienda del negozio è la demo.
 */
export async function datiNegozio(): Promise<DatiNegozio | null> {
  const c = g.__aziendaNegozio;
  if (rispostaNonPronta()) return null; // avvio non riuscito: come senza negozio (catalogo vuoto, ordini 503)
  if (c && c.fino > Date.now()) return c.dati;
  let dati: DatiNegozio | null = null;
  try {
    const ctx = (await auth.$context) as unknown as AuthContext;
    const env = process.env.NEGOZIO_AZIENDA?.trim();
    if (env) {
      if (idAziendaValido(env)) {
        const o = await ctx.adapter.findOne<{ id: string; metadata?: unknown }>({ model: "organization", where: [{ field: "id", value: env }] });
        dati = { id: env, demo: o ? eDemo(o.metadata) : false };
      }
    } else {
      const righe = await ctx.adapter.findMany<{ id: string; metadata?: unknown }>({ model: "organization" });
      const d = righe.find((o) => eDemo(o.metadata));
      dati = d ? { id: d.id, demo: true } : null;
    }
  } catch (e) {
    console.error("Azienda del negozio non trovata", e);
  }
  g.__aziendaNegozio = { dati, fino: Date.now() + 10_000 };
  return dati;
}

export async function aziendaNegozio(): Promise<string | null> {
  return (await datiNegozio())?.id ?? null;
}

const troppoGrande = () => risposta({ error: "Richiesta troppo grande." }, 413);

/**
 * Le richieste pubbliche che scrivono (ordine, pagamento): stesso sito, JSON, al massimo 2 KB.
 * Il corpo si legge a pezzi e si conta: oltre 2048 byte si smette subito, senza tenere in memoria il resto.
 * Restituisce il corpo già letto o la risposta di errore.
 */
export async function corpoPubblico(req: Request): Promise<Record<string, unknown> | Response> {
  if (!richiestaDellApp(req)) return risposta({ error: "Richiesta non consentita." }, 403);
  if (Number(req.headers.get("content-length") ?? 0) > MAX_CORPO) return troppoGrande();
  const pezzi: Uint8Array[] = [];
  let totale = 0;
  if (req.body) {
    const lettore = req.body.getReader();
    try {
      for (;;) {
        const { done, value } = await lettore.read();
        if (done) break;
        totale += value.byteLength;
        if (totale > MAX_CORPO) {
          await lettore.cancel().catch(() => undefined);
          return troppoGrande();
        }
        pezzi.push(value);
      }
    } catch {
      return risposta({ error: "Richiesta non valida." }, 400);
    }
  }
  try {
    const b = JSON.parse(Buffer.concat(pezzi).toString("utf8"));
    if (b && typeof b === "object" && !Array.isArray(b)) return b as Record<string, unknown>;
  } catch {
    // sotto
  }
  return risposta({ error: "Richiesta non valida." }, 400);
}
