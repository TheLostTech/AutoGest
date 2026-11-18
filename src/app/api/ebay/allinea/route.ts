// Allinea un annuncio con eBay (o con il ponte simulato). Le credenziali restano sul server.
import { connection } from "next/server";
import { altroSito } from "@/lib/collegamenti-server";
import { scegliPonte } from "@/lib/ebay/server";
import { validaRichiesta } from "@/lib/ebay/valida";

const json = (body: unknown, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "no-store" } });

export async function POST(req: Request) {
  await connection();
  if (altroSito(req)) return json({ error: "Richiesta da un altro sito" }, 403);
  const r = validaRichiesta(await req.json().catch(() => null));
  if (!r) return json({ error: "Richiesta non valida" }, 400);
  try {
    return json(await (await scegliPonte()).allinea(r));
  } catch (e) {
    return json({ stato: "errore", avvisi: [], errore: e instanceof Error ? e.message : "eBay non risponde" });
  }
}
