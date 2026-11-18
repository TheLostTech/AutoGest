// Vendite fatte su eBay dalla data indicata (?da=<iso>).
import { connection } from "next/server";
import { altroSito } from "@/lib/collegamenti-server";
import { messaggioPerUtente, scegliPonte } from "@/lib/ebay/server";

const json = (body: unknown, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "no-store" } });

export async function GET(req: Request) {
  await connection();
  if (altroSito(req)) return json({ error: "Richiesta da un altro sito" }, 403);
  const da = new URL(req.url).searchParams.get("da") ?? "";
  if (!da || da.length > 40 || Number.isNaN(Date.parse(da))) return json({ error: "Manca la data (da=...)" }, 400);
  try {
    return json({ vendite: await (await scegliPonte()).vendite(da) });
  } catch (e) {
    return json({ error: messaggioPerUtente(e) }, 502);
  }
}
