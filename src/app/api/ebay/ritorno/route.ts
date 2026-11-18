// Ritorno dalla pagina di consenso di eBay (?code=…&state=…). Qui arriva il browser mandato da eBay,
// quindi niente controllo di Origin: la protezione è il valore `state` casuale, salvato da /api/ebay/collega
// e valido una volta sola per 10 minuti.
import { connection } from "next/server";
import { accessoDaRichiesta } from "@/lib/accesso/server";
import type { CodiceCollegamento } from "@/lib/ebay/codici";
import { completaCollegamento } from "@/lib/ebay/sandbox";
import { credenzialiSandbox } from "@/lib/ebay/server";

// no-referrer: l'indirizzo con il codice di eBay non passa alla pagina dopo
const vaiA = (dove: string) => new Response(null, { status: 303, headers: { Location: dove, "Cache-Control": "no-store", "Referrer-Policy": "no-referrer" } });
// Nell'indirizzo solo un codice fisso; il dettaglio resta in archivio.errore (StatoPonte.errore)
const errore = (codice: CodiceCollegamento) => vaiA(`/impostazioni/collegamenti?ebay=errore&codice=${codice}`);

export async function GET(req: Request) {
  await connection();
  const a = await accessoDaRichiesta(req);
  if (a instanceof Response) return a;
  const q = new URL(req.url).searchParams;
  const cred = await credenzialiSandbox(a.azienda.id);
  if (!cred) return errore("chiavi");
  const code = (q.get("code") ?? "").slice(0, 2000);
  const state = (q.get("state") ?? "").slice(0, 200);
  const r = await completaCollegamento(cred, code, state);
  return r.ok ? vaiA("/impostazioni/collegamenti?ebay=ok") : errore(r.codice);
}
