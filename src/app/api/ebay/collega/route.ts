// Collega il conto eBay (Sandbox): porta alla pagina di consenso di eBay. DELETE scollega.
// Il ritorno arriva su /api/ebay/ritorno, l'indirizzo collegato al RuName nel portale eBay Developers
// (deve essere l'indirizzo HTTPS del tunnel del prototipo: eBay non accetta http né localhost).
import { connection } from "next/server";
import { altroSito } from "@/lib/collegamenti-server";
import { avviaCollegamento, scollega } from "@/lib/ebay/sandbox";
import type { CodiceCollegamento } from "@/lib/ebay/codici";
import { credenzialiSandbox, messaggioPerUtente } from "@/lib/ebay/server";

const json = (body: unknown, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "no-store" } });
const vaiA = (dove: string) => new Response(null, { status: 303, headers: { Location: dove, "Cache-Control": "no-store" } });
// Nell'indirizzo solo un codice fisso: la pagina lo traduce con testoErroreCollegamento (codici.ts)
const errore = (codice: CodiceCollegamento) => vaiA(`/impostazioni/collegamenti?ebay=errore&codice=${codice}`);

export async function GET(req: Request) {
  await connection();
  if (altroSito(req)) return json({ error: "Richiesta da un altro sito" }, 403);
  const cred = await credenzialiSandbox();
  if (!cred) return errore("chiavi");
  try {
    return vaiA(await avviaCollegamento(cred));
  } catch (e) {
    messaggioPerUtente(e); // solo per il registro del server
    return errore("imprevisto");
  }
}

export async function DELETE(req: Request) {
  await connection();
  if (altroSito(req)) return json({ error: "Richiesta da un altro sito" }, 403);
  await scollega();
  return json({ ok: true });
}
