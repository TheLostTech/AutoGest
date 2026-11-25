// Foto dei ricambi e dei veicoli: si salvano come file, nel telefono resta solo l'indirizzo.
// Vanno nella cartella dell'azienda della sessione (vedi server-data.ts): sul PC server dell'azienda o, più avanti, nel cloud.
import { randomBytes } from "node:crypto";
import { accessoDaRichiesta } from "@/lib/accesso/server";
import { deposito } from "@/lib/deposito";
import { controllaDimensione, MAX_FILE_BYTES, MESSAGGIO_TROPPO_GRANDE } from "@/lib/limiti-file";

const PREFIX = "data:image/jpeg;base64,";

export async function POST(req: Request) {
  const a = await accessoDaRichiesta(req);
  if (a instanceof Response) return a;
  const { data } = (await req.json().catch(() => ({}))) as { data?: unknown };
  if (typeof data !== "string" || !data.startsWith(PREFIX)) return Response.json({ error: "Serve una foto JPEG" }, { status: 400 });
  // Prima di decodificare: una stringa enorme non deve diventare un buffer enorme
  if (data.length - PREFIX.length > Math.ceil((MAX_FILE_BYTES * 4) / 3) + 4) return Response.json({ error: MESSAGGIO_TROPPO_GRANDE }, { status: 413 });
  const bytes = Buffer.from(data.slice(PREFIX.length), "base64");
  const dim = controllaDimensione(bytes.length);
  if (!dim.ok) return Response.json({ error: dim.messaggio }, { status: 413 });
  const name = `${Date.now().toString(36)}${randomBytes(6).toString("hex")}.jpg`;
  await deposito().salvaFile(a.azienda.id, "foto", name, bytes);
  return Response.json({ url: `/api/foto/${name}` }, { headers: { "Cache-Control": "no-store" } });
}
