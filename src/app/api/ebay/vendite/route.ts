// Vendite fatte su eBay dalla data indicata (corpo JSON { da: <iso> }).
// È POST e non GET perché cambia dati condivisi: il server segna gli ordini passati e l'ora dell'ultimo controllo.
// Una GET la potrebbe far partire qualunque pagina (anche un'immagine), nascondendo gli ordini veri al gestionale.
import { connection } from "next/server";
import { accessoDaRichiesta } from "@/lib/accesso/server";
import { richiestaDellApp } from "@/lib/collegamenti-server";
import { messaggioPerUtente, scegliPonte } from "@/lib/ebay/server";

const json = (body: unknown, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "no-store" } });

export async function POST(req: Request) {
  await connection();
  const a = await accessoDaRichiesta(req);
  if (a instanceof Response) return a;
  if (!richiestaDellApp(req)) return json({ error: "Richiesta da un altro sito" }, 403);
  const testo = await req.text().catch(() => "");
  if (testo.length > 1024) return json({ error: "Richiesta troppo grande" }, 413);
  let da = "";
  try {
    const corpo = JSON.parse(testo) as { da?: unknown };
    if (typeof corpo?.da === "string") da = corpo.da;
  } catch {
    // corpo non JSON: rifiutato sotto
  }
  if (!da || da.length > 40 || Number.isNaN(Date.parse(da))) return json({ error: "Manca la data (da)" }, 400);
  try {
    return json({ vendite: await (await scegliPonte(a.azienda.id)).vendite(da) });
  } catch (e) {
    return json({ error: messaggioPerUtente(e) }, 502);
  }
}
