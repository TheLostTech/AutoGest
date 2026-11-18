// Allinea un annuncio con eBay (o con il ponte simulato). Le credenziali restano sul server.
import { connection } from "next/server";
import { altroSito } from "@/lib/collegamenti-server";
import { messaggioPerUtente, scegliPonte } from "@/lib/ebay/server";
import { validaRichiesta } from "@/lib/ebay/valida";

const json = (body: unknown, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "no-store" } });
const MAX_CORPO = 256 * 1024;

export async function POST(req: Request) {
  await connection();
  if (altroSito(req)) return json({ error: "Richiesta da un altro sito" }, 403);
  const testo = await req.text().catch(() => "");
  if (testo.length > MAX_CORPO) return json({ error: "Richiesta troppo grande" }, 413);
  let corpo: unknown = null;
  try {
    corpo = JSON.parse(testo);
  } catch {
    // corpo non JSON: rifiutato sotto
  }
  const r = validaRichiesta(corpo);
  if (!r) return json({ error: "Richiesta non valida" }, 400);
  try {
    return json(await (await scegliPonte()).allinea(r));
  } catch (e) {
    return json({ stato: "errore", avvisi: [], errore: messaggioPerUtente(e) });
  }
}
