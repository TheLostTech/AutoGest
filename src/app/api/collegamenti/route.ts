// Credenziali dei collegamenti esterni (Impostazioni → Collegamenti).
// Restano sul server, fuori dall'archivio condiviso con i telefoni: password, token e certificati sono
// cifrati su disco (AES-256-GCM) e non tornano mai al browser, che vede solo se ci sono.
// Chiave: variabile CHIAVE_COLLEGAMENTI (64 caratteri esadecimali) o, se manca, un file generato nella
// cartella dati. Nel prodotto vero la chiave va in un archivio di segreti, non accanto ai dati.
import { connection } from "next/server";
import { accessoDaRichiesta, soloRuoli } from "@/lib/accesso/server";
import { servizioById } from "@/lib/collegamenti";
import {
  altroSito,
  erroreSalvataggio,
  load,
  modificaServizio,
  pubblico,
  scollegaServizio,
  type ModificaCollegamento,
} from "@/lib/collegamenti-server";

const json = (body: unknown, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "no-store" } });

export async function GET(req: Request) {
  await connection();
  const acc = await accessoDaRichiesta(req);
  if (acc instanceof Response) return acc;
  try {
    const a = await load(acc.azienda.id);
    return json(Object.fromEntries(Object.entries(a).map(([id, s]) => [id, pubblico(s)])));
  } catch (e) {
    console.error("Collegamenti non leggibili", e);
    return json({ error: "Il file dei collegamenti non si legge: non è stato modificato. Avvisa l'assistenza." }, 500);
  }
}

async function soloResponsabile(req: Request) {
  const acc = await accessoDaRichiesta(req);
  if (acc instanceof Response) return acc;
  return soloRuoli(acc, "responsabile") ?? acc;
}

// Lettura, modifica e scrittura stanno in un solo aggiornamento del deposito (modificaServizio): due salvataggi
// insieme, anche da istanze diverse, vanno uno dopo l'altro e nessuno perde le credenziali dell'altro.
export async function PUT(req: Request) {
  const acc = await soloResponsabile(req);
  if (acc instanceof Response) return acc;
  if (altroSito(req)) return json({ error: "Richiesta da un altro sito" }, 403);
  const body = (await req.json().catch(() => null)) as ModificaCollegamento | null;
  const serv = body && servizioById(String(body.id));
  if (!body || !serv) return json({ error: "Servizio sconosciuto" }, 400);
  try {
    return json(await modificaServizio(acc.azienda.id, serv, body));
  } catch (e) {
    const r = erroreSalvataggio(e);
    return json({ error: r.error }, r.status);
  }
}

// Scollega: cancella tutti i dati salvati del servizio
export async function DELETE(req: Request) {
  const acc = await soloResponsabile(req);
  if (acc instanceof Response) return acc;
  if (altroSito(req)) return json({ error: "Richiesta da un altro sito" }, 403);
  const id = new URL(req.url).searchParams.get("id") ?? "";
  if (!servizioById(id)) return json({ error: "Servizio sconosciuto" }, 400);
  try {
    await scollegaServizio(acc.azienda.id, id);
  } catch (e) {
    console.error("Collegamenti non leggibili", e);
    return json({ error: "Il file dei collegamenti non si legge: non è stato modificato. Avvisa l'assistenza." }, 500);
  }
  return json({ ok: true });
}
