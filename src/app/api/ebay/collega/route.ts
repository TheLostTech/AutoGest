// Collega il conto eBay (Sandbox): porta alla pagina di consenso di eBay. DELETE scollega.
// Il ritorno arriva su /api/ebay/ritorno, l'indirizzo collegato al RuName nel portale eBay Developers
// (deve essere l'indirizzo HTTPS del tunnel del prototipo: eBay non accetta http né localhost).
import { connection } from "next/server";
import { altroSito } from "@/lib/collegamenti-server";
import { avviaCollegamento, scollega } from "@/lib/ebay/sandbox";
import { credenzialiSandbox, messaggioPerUtente } from "@/lib/ebay/server";

const json = (body: unknown, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "no-store" } });
const vaiA = (dove: string) => new Response(null, { status: 303, headers: { Location: dove, "Cache-Control": "no-store" } });
const errore = (msg: string) => vaiA(`/impostazioni/collegamenti?ebay=errore&msg=${encodeURIComponent(msg)}`);

export async function GET(req: Request) {
  await connection();
  if (altroSito(req)) return json({ error: "Richiesta da un altro sito" }, 403);
  const cred = await credenzialiSandbox();
  if (!cred) return errore("Prima scegli l'ambiente Sandbox e salva App ID, Cert ID e RuName.");
  try {
    return vaiA(await avviaCollegamento(cred));
  } catch (e) {
    return errore(messaggioPerUtente(e));
  }
}

export async function DELETE(req: Request) {
  await connection();
  if (altroSito(req)) return json({ error: "Richiesta da un altro sito" }, 403);
  await scollega();
  return json({ ok: true });
}
