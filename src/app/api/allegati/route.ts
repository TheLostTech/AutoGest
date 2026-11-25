// Allegati PDF della pratica (es. ricevuta di avvenuta radiazione): si salvano nella cartella dell'azienda della sessione,
// nel veicolo resta solo l'indirizzo. Contengono dati personali: li carica solo chi fa le pratiche.
import { randomBytes } from "node:crypto";
import { connection } from "next/server";
import { accessoDaRichiesta, soloRuoli } from "@/lib/accesso/server";
import { richiestaDellApp } from "@/lib/collegamenti-server";
import { rispostaModuloSpento } from "@/lib/moduli-server";
import { deposito } from "@/lib/deposito";
import { controllaDimensione, MAX_FILE_BYTES, MESSAGGIO_TROPPO_GRANDE } from "@/lib/limiti-file";

const PREFIX = "data:application/pdf;base64,";

export async function POST(req: Request) {
  await connection();
  if (!richiestaDellApp(req)) return Response.json({ error: "Richiesta non consentita" }, { status: 403 });
  const acc = await accessoDaRichiesta(req);
  if (acc instanceof Response) return acc;
  const vietato = soloRuoli(acc, "accettazione", "responsabile");
  if (vietato) return vietato;
  // Le ricevute sono della pratica, cioè del modulo Accettazione: spento, non si caricano nemmeno per vie traverse
  const spento = await rispostaModuloSpento(acc.azienda, "accettazione", "Accettazione");
  if (spento) return spento;
  const { data } = (await req.json().catch(() => ({}))) as { data?: unknown };
  if (typeof data !== "string" || !data.startsWith(PREFIX)) return Response.json({ error: "Serve un file PDF" }, { status: 400 });
  // Prima di decodificare: una stringa enorme non deve diventare un buffer enorme
  if (data.length - PREFIX.length > Math.ceil((MAX_FILE_BYTES * 4) / 3) + 4) return Response.json({ error: MESSAGGIO_TROPPO_GRANDE }, { status: 413 });
  const bytes = Buffer.from(data.slice(PREFIX.length), "base64");
  const dim = controllaDimensione(bytes.length);
  if (!dim.ok) return Response.json({ error: dim.messaggio }, { status: 413 });
  if (bytes.subarray(0, 4).toString() !== "%PDF") return Response.json({ error: "Il file non è un PDF" }, { status: 400 });
  const name = `${Date.now().toString(36)}${randomBytes(9).toString("hex")}.pdf`;
  await deposito().salvaFile(acc.azienda.id, "allegati", name, bytes);
  return Response.json({ url: `/api/allegati/${name}` }, { headers: { "Cache-Control": "no-store" } });
}
