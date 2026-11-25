// Allegato PDF della pratica. Contiene dati personali: lo vede solo chi ha una sessione valida nell'azienda
// che lo ha caricato (l'azienda viene dalla sessione, mai dall'indirizzo: un'altra azienda non trova il file).
import { readFile } from "node:fs/promises";
import path from "node:path";
import { connection } from "next/server";
import { accessoDaRichiesta } from "@/lib/accesso/server";
import { altroSito } from "@/lib/collegamenti-server";
import { cartellaAllegatiAzienda } from "@/lib/server-data";

export async function GET(req: Request, { params }: { params: Promise<{ name: string }> }) {
  await connection();
  if (altroSito(req) || req.headers.get("sec-fetch-site") === "cross-site") return new Response("Richiesta non consentita", { status: 403 });
  const acc = await accessoDaRichiesta(req);
  if (acc instanceof Response) return acc;
  const { name } = await params;
  // Solo nomi generati dal server: niente percorsi verso altre cartelle
  if (!/^[a-z0-9]+\.pdf$/.test(name)) return new Response("Allegato non trovato", { status: 404 });
  const bytes = await readFile(path.join(cartellaAllegatiAzienda(acc.azienda.id), name)).catch(() => undefined);
  if (!bytes) return new Response("Allegato non trovato", { status: 404 });
  return new Response(new Uint8Array(bytes), {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `inline; filename="${name}"`,
      "Cache-Control": "private, no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
