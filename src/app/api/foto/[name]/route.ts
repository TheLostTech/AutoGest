import { readFile } from "node:fs/promises";
import path from "node:path";
import { connection } from "next/server";
import { accessoDaRichiesta } from "@/lib/accesso/server";
import { cartellaFotoAzienda } from "@/lib/server-data";

export async function GET(req: Request, { params }: { params: Promise<{ name: string }> }) {
  await connection();
  const a = await accessoDaRichiesta(req);
  if (a instanceof Response) return a;
  const { name } = await params;
  // Solo nomi generati dal server: niente percorsi verso altre cartelle
  if (!/^[a-z0-9]+\.jpg$/.test(name)) return new Response("Foto non trovata", { status: 404 });
  try {
    const bytes = await readFile(path.join(cartellaFotoAzienda(a.azienda.id), name));
    return new Response(new Uint8Array(bytes), { headers: { "Content-Type": "image/jpeg", "Cache-Control": "private, max-age=31536000, immutable" } });
  } catch {
    return new Response("Foto non trovata", { status: 404 });
  }
}
