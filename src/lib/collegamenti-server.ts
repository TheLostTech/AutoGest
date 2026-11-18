// Archivio dei collegamenti sul server: lettura, scrittura e segreti decifrati. Solo server.
// Lo usano la route /api/collegamenti e il ponte eBay (le route Next non possono esportare altro che gli handler).
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { DATA_DIR } from "@/lib/server-data";
import { decifra } from "@/lib/cifratura";

const FILE = path.join(DATA_DIR, "collegamenti.json");
export const MAX_TEXT = 4000;

export interface Salvato {
  valori: Record<string, string | string[]>;
  segreti: Record<string, string>; // cifrati
  file: Record<string, { nome: string; byte: number; dati: string }>; // dati cifrati
  aggiornato?: string;
}
export type Archivio = Record<string, Salvato>;

export async function load(): Promise<Archivio> {
  try {
    return JSON.parse(await readFile(FILE, "utf8")) as Archivio;
  } catch {
    return {};
  }
}

export async function save(a: Archivio) {
  await mkdir(DATA_DIR, { recursive: true });
  await writeFile(FILE, JSON.stringify(a), { mode: 0o600 });
}

/** Valori salvati di un servizio più i segreti decifrati. Mai da mandare al browser. */
export async function leggiValori(id: string): Promise<Record<string, string | string[]>> {
  const s = (await load())[id];
  const out: Record<string, string | string[]> = { ...(s?.valori ?? {}) };
  for (const [k, v] of Object.entries(s?.segreti ?? {})) {
    try {
      out[k] = (await decifra(v)).toString("utf8");
    } catch {
      // segreto illeggibile (chiave cambiata): come se mancasse
    }
  }
  return out;
}

// Nessun login vero nel prototipo: chiunque raggiunga il server può chiamare questa API.
// Intanto si bloccano le richieste partite da pagine di altri siti (il browser manda sempre Origin
// su PUT e DELETE). Prima della produzione: login con ruolo responsabile verificato qui sul server.
export function altroSito(req: Request) {
  const origin = req.headers.get("origin");
  if (!origin) return false;
  try {
    return new URL(origin).host !== req.headers.get("host");
  } catch {
    return true;
  }
}

/**
 * Più severo di altroSito, per le richieste che cambiano dati condivisi: Origin deve esserci ed essere questo sito,
 * e il corpo deve essere JSON. Un'altra pagina non può mandare JSON senza il permesso CORS, che qui non si dà.
 */
export function richiestaDellApp(req: Request) {
  if (!req.headers.get("origin") || altroSito(req)) return false;
  return (req.headers.get("content-type") ?? "").toLowerCase().startsWith("application/json");
}
