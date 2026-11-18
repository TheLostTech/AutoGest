// Archivio condiviso dell'azienda: tiene allineati telefoni e computer collegati alla stessa azienda.
// L'azienda arriva sempre dalla sessione. La fusione dei salvataggi sta in archivio-unione.ts.
import { connection } from "next/server";
import { accessoDaRichiesta } from "@/lib/accesso/server";
import { aggiornaStato, leggiStato } from "@/lib/archivio-azienda";
import { esitoPush, unisciPush, type Push, type Stored } from "@/lib/archivio-unione";

const NOSTORE = { "Cache-Control": "no-store" };

function erroreArchivio(e: unknown): Response {
  console.error("Archivio non leggibile", e);
  return Response.json({ error: "L'archivio dell'azienda non si legge: non è stato modificato. Avvisa l'assistenza.", motivo: "archivio" }, { status: 500, headers: NOSTORE });
}

export async function GET(req: Request) {
  await connection();
  const a = await accessoDaRichiesta(req);
  if (a instanceof Response) return a;
  try {
    const s = await leggiStato(a.azienda.id);
    return Response.json({ ...s, demo: a.azienda.demo }, { headers: NOSTORE });
  } catch (e) {
    return erroreArchivio(e);
  }
}

export async function PUT(req: Request) {
  const a = await accessoDaRichiesta(req);
  if (a instanceof Response) return a;
  const body = (await req.json().catch(() => null)) as Push | null;
  if (!body || typeof body.schema !== "string") return Response.json({ error: "Richiesta non valida" }, { status: 400, headers: NOSTORE });
  // La decisione si prende sull'archivio appena letto, dentro il blocco dell'azienda: nessuna corsa possibile.
  // Sostituire tutto (replace, archivio vuoto, schema diverso) solo sull'azienda demo e solo al responsabile.
  const ctx = { demo: a.azienda.demo, responsabile: a.ruoli.includes("responsabile") };
  let r: Stored | 403 | 409;
  try {
    r = await aggiornaStato<Stored | 403 | 409>(a.azienda.id, (cur) => {
      const esito = esitoPush(cur, body, ctx);
      if (esito === 403 || esito === 409) return { stored: cur, risultato: esito, nonScrivere: true };
      const stored = unisciPush(cur, body);
      return { stored, risultato: stored };
    });
  } catch (e) {
    return erroreArchivio(e);
  }
  if (r === 403) return Response.json({ error: "Il ripristino dei dati è permesso solo al responsabile dell'azienda demo.", motivo: "ruolo" }, { status: 403, headers: NOSTORE });
  if (r === 409) return Response.json({ error: "Archivio con versione diversa: serve un aggiornamento.", motivo: "versione" }, { status: 409, headers: NOSTORE });
  return Response.json({ version: r.version, schema: r.schema }, { headers: NOSTORE });
}
