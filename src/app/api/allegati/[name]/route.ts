// Allegato PDF della pratica. Contiene dati personali: nel prototipo su main non c'è login,
// prima della produzione va servito solo a una sessione autorizzata a vedere il veicolo.
import { readFile } from "node:fs/promises";
import path from "node:path";
import { connection } from "next/server";
import { altroSito } from "@/lib/collegamenti-server";
import { ALLEGATI_DIR } from "@/lib/server-data";

export async function GET(req: Request, { params }: { params: Promise<{ name: string }> }) {
  await connection();
  if (altroSito(req) || req.headers.get("sec-fetch-site") === "cross-site") return new Response("Richiesta non consentita", { status: 403 });
  const { name } = await params;
  // Solo nomi generati dal server: niente percorsi verso altre cartelle
  if (!/^[a-z0-9]+\.pdf$/.test(name)) return new Response("Allegato non trovato", { status: 404 });
  const bytes = await readFile(path.join(ALLEGATI_DIR, name)).catch(() => undefined);
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
