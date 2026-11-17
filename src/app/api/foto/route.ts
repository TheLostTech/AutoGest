// Foto dei ricambi e dei veicoli: si salvano come file, nel telefono resta solo l'indirizzo.
// Vanno nella cartella dati del server (vedi server-data.ts): sul PC server dell'azienda o, più avanti, nel cloud.
import { randomBytes } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { PHOTO_DIR } from "@/lib/server-data";

const PREFIX = "data:image/jpeg;base64,";
const MAX_BYTES = 4 * 1024 * 1024;

export async function POST(req: Request) {
  const { data } = (await req.json().catch(() => ({}))) as { data?: unknown };
  if (typeof data !== "string" || !data.startsWith(PREFIX)) return Response.json({ error: "Serve una foto JPEG" }, { status: 400 });
  const bytes = Buffer.from(data.slice(PREFIX.length), "base64");
  if (bytes.length === 0 || bytes.length > MAX_BYTES) return Response.json({ error: "Foto vuota o troppo grande" }, { status: 413 });
  const name = `${Date.now().toString(36)}${randomBytes(6).toString("hex")}.jpg`;
  await mkdir(PHOTO_DIR, { recursive: true });
  await writeFile(path.join(PHOTO_DIR, name), bytes);
  return Response.json({ url: `/api/foto/${name}` }, { headers: { "Cache-Control": "no-store" } });
}
