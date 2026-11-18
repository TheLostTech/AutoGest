// Politiche eBay del conto collegato (spedizione, pagamento, reso) e magazzini, con le scelte del gestionale.
// GET le elenca (solo nomi e id), PUT salva le scelte.
import { connection } from "next/server";
import { accessoDaRichiesta } from "@/lib/accesso/server";
import { altroSito } from "@/lib/collegamenti-server";
import { politicheConScelte, salvaScelte } from "@/lib/ebay/sandbox";
import { credenzialiSandbox, messaggioPerUtente } from "@/lib/ebay/server";

const json = (body: unknown, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "no-store" } });
const SIMULATO = "eBay è in modo Simulato: non ci sono politiche da scegliere.";

export async function GET(req: Request) {
  await connection();
  const a = await accessoDaRichiesta(req);
  if (a instanceof Response) return a;
  if (altroSito(req)) return json({ error: "Richiesta da un altro sito" }, 403);
  const cred = await credenzialiSandbox(a.azienda.id);
  if (!cred) return json({ error: SIMULATO }, 409);
  try {
    return json(await politicheConScelte(cred));
  } catch (e) {
    return json({ error: messaggioPerUtente(e) }, 502);
  }
}

export async function PUT(req: Request) {
  await connection();
  const a = await accessoDaRichiesta(req);
  if (a instanceof Response) return a;
  if (altroSito(req)) return json({ error: "Richiesta da un altro sito" }, 403);
  const cred = await credenzialiSandbox(a.azienda.id);
  if (!cred) return json({ error: SIMULATO }, 409);
  const testo = await req.text().catch(() => "");
  if (testo.length > 4096) return json({ error: "Richiesta troppo grande" }, 413);
  let corpo: unknown;
  try {
    corpo = JSON.parse(testo);
  } catch {
    return json({ error: "Richiesta non valida" }, 400);
  }
  try {
    const r = await salvaScelte(cred, corpo);
    return r.ok ? json(await politicheConScelte(cred)) : json({ error: r.messaggio }, 400);
  } catch (e) {
    return json({ error: messaggioPerUtente(e) }, 502);
  }
}
