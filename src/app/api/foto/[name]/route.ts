import { readFile } from "node:fs/promises";
import path from "node:path";
import { connection } from "next/server";
import { PHOTO_DIR } from "@/lib/server-data";

export async function GET(_req: Request, { params }: { params: Promise<{ name: string }> }) {
  await connection();
  const { name } = await params;
  // Solo nomi generati dal server: niente percorsi verso altre cartelle
  if (!/^[a-z0-9]+\.jpg$/.test(name)) return new Response("Foto non trovata", { status: 404 });
  try {
    const bytes = await readFile(path.join(PHOTO_DIR, name));
    return new Response(new Uint8Array(bytes), { headers: { "Content-Type": "image/jpeg", "Cache-Control": "public, max-age=31536000, immutable" } });
  } catch {
    return new Response("Foto non trovata", { status: 404 });
  }
}
