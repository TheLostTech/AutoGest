// Stato del collegamento con eBay: modo (Simulato o Sandbox) e se è pronto. Solo StatoPonte, nessun segreto.
import { connection } from "next/server";
import { altroSito } from "@/lib/collegamenti-server";
import { messaggioPerUtente, scegliPonte } from "@/lib/ebay/server";

const json = (body: unknown, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "no-store" } });

export async function GET(req: Request) {
  await connection();
  if (altroSito(req)) return json({ error: "Richiesta da un altro sito" }, 403);
  try {
    return json(await (await scegliPonte()).stato());
  } catch (e) {
    return json({ modo: "Simulato", collegato: false, errore: messaggioPerUtente(e) });
  }
}
