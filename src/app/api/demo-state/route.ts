// Archivio condiviso dell'azienda: tiene allineati telefoni e computer collegati alla stessa azienda.
// L'azienda arriva sempre dalla sessione. La fusione dei salvataggi sta in archivio-unione.ts.
import { connection } from "next/server";
import { accessoDaRichiesta, soloRuoli } from "@/lib/accesso/server";
import { aggiornaStato, leggiStato } from "@/lib/archivio-azienda";
import { unisciPush, type Push } from "@/lib/archivio-unione";

const NOSTORE = { "Cache-Control": "no-store" };

export async function GET(req: Request) {
  await connection();
  const a = await accessoDaRichiesta(req);
  if (a instanceof Response) return a;
  const s = await leggiStato(a.azienda.id);
  return Response.json({ ...s, demo: a.azienda.demo }, { headers: NOSTORE });
}

export async function PUT(req: Request) {
  const a = await accessoDaRichiesta(req);
  if (a instanceof Response) return a;
  const body = (await req.json().catch(() => null)) as Push | null;
  if (!body || typeof body.schema !== "string") return Response.json({ error: "Richiesta non valida" }, { status: 400, headers: NOSTORE });
  // Ripristino dei dati demo: solo sull'azienda demo e solo per chi ne ha la responsabilità
  if (body.replace) {
    if (!a.azienda.demo) return Response.json({ error: "Il ripristino è permesso solo sull'azienda demo.", motivo: "non-demo" }, { status: 403, headers: NOSTORE });
    const no = soloRuoli(a, "responsabile");
    if (no) return no;
  }
  const s = await aggiornaStato(a.azienda.id, (cur) => {
    const stored = unisciPush(cur, body);
    return { stored, risultato: stored };
  });
  return Response.json({ version: s.version, schema: s.schema }, { headers: NOSTORE });
}
