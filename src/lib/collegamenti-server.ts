// Archivio dei collegamenti sul server: lettura, scrittura e segreti decifrati. Solo server.
// Lo usano la route /api/collegamenti e il ponte eBay (le route Next non possono esportare altro che gli handler).
import path from "node:path";
import { cartellaAzienda } from "@/lib/server-data";
import { decifra } from "@/lib/cifratura";
import { leggiCollegamentiDaFile, scriviCollegamentiSuFile } from "@/lib/collegamenti-file";
import { inFilaPer } from "@/lib/fila";

const file = (aziendaId: string) => path.join(cartellaAzienda(aziendaId), "collegamenti.json");
export const MAX_TEXT = 4000;

export interface Salvato {
  valori: Record<string, string | string[]>;
  segreti: Record<string, string>; // cifrati
  file: Record<string, { nome: string; byte: number; dati: string }>; // dati cifrati
  aggiornato?: string;
}
export type Archivio = Record<string, Salvato>;

// File assente: nessun collegamento. File illeggibile o corrotto: errore (CollegamentiIlleggibili), mai {} da riscrivere.
export function load(aziendaId: string): Promise<Archivio> {
  return leggiCollegamentiDaFile<Archivio>(file(aziendaId));
}

export function save(aziendaId: string, a: Archivio): Promise<void> {
  return scriviCollegamentiSuFile(file(aziendaId), a);
}

/** Le modifiche ai collegamenti di un'azienda vanno in fila (coda sulla globalThis, una sola per processo). */
export function inFilaCollegamenti<T>(aziendaId: string, fn: () => Promise<T>): Promise<T> {
  return inFilaPer("collegamenti", aziendaId, fn);
}

/** Valori salvati di un servizio più i segreti decifrati. Mai da mandare al browser. */
export async function leggiValori(aziendaId: string, id: string): Promise<Record<string, string | string[]>> {
  const s = (await load(aziendaId))[id];
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

// Il login vero c'è: ogni route chiama prima accessoDaRichiesta, che ricava azienda e ruoli dalla sessione (mai dalla richiesta).
// Limite noto: il server controlla l'accesso, la separazione tra aziende e, per ruolo, alcune azioni delicate (collegamenti, collegamento e politiche eBay, richiesta della visura PRA, ripristino dei dati, gestione dei dispositivi, Piattaforma); tutto il resto è limitato per ruolo solo nelle schermate fino al database dei dati (A1).
// In più si bloccano le richieste partite da pagine di altri siti (il browser manda sempre Origin su PUT e DELETE).
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
