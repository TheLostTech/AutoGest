// Allegati PDF della pratica (es. ricevuta di avvenuta radiazione): si salvano nella cartella dell'azienda della sessione,
// nel veicolo resta solo l'indirizzo. Contengono dati personali: li carica solo chi fa le pratiche.
import { randomBytes } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { connection } from "next/server";
import { accessoDaRichiesta, soloRuoli } from "@/lib/accesso/server";
import { richiestaDellApp } from "@/lib/collegamenti-server";
import { moduloAttivoSulServer } from "@/lib/moduli-server";
import { cartellaAllegatiAzienda } from "@/lib/server-data";

const PREFIX = "data:application/pdf;base64,";
const MAX_BYTES = 8 * 1024 * 1024;

export async function POST(req: Request) {
  await connection();
  if (!richiestaDellApp(req)) return Response.json({ error: "Richiesta non consentita" }, { status: 403 });
  const acc = await accessoDaRichiesta(req);
  if (acc instanceof Response) return acc;
  const vietato = soloRuoli(acc, "accettazione", "responsabile");
  if (vietato) return vietato;
  // Le ricevute sono della pratica, cioè del modulo Accettazione: spento, non si caricano nemmeno per vie traverse
  if (!(await moduloAttivoSulServer(acc.azienda, "accettazione"))) return Response.json({ error: "Il modulo Accettazione non è attivo" }, { status: 403 });
  const { data } = (await req.json().catch(() => ({}))) as { data?: unknown };
  if (typeof data !== "string" || !data.startsWith(PREFIX)) return Response.json({ error: "Serve un file PDF" }, { status: 400 });
  const bytes = Buffer.from(data.slice(PREFIX.length), "base64");
  if (bytes.length === 0 || bytes.length > MAX_BYTES) return Response.json({ error: "PDF vuoto o più grande di 8 MB" }, { status: 413 });
  if (bytes.subarray(0, 4).toString() !== "%PDF") return Response.json({ error: "Il file non è un PDF" }, { status: 400 });
  const name = `${Date.now().toString(36)}${randomBytes(9).toString("hex")}.pdf`;
  const dir = cartellaAllegatiAzienda(acc.azienda.id);
  await mkdir(dir, { recursive: true });
  await writeFile(path.join(dir, name), bytes, { mode: 0o600 });
  return Response.json({ url: `/api/allegati/${name}` }, { headers: { "Cache-Control": "no-store" } });
}
