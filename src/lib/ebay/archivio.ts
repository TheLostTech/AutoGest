// Archivio del ponte eBay sul server: file ebay.json nella cartella dati, leggibile solo dal processo (0600).
// Token di accesso e di rinnovo cifrati con cifra(); niente di questo file va mai al browser.
// Solo server.
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import path from "node:path";
import { DATA_DIR } from "@/lib/server-data";
import type { SpedizioneEbay } from "./contratto";

const FILE = path.join(DATA_DIR, "ebay.json");

export type RuoloPolitica = "pagamento" | "reso" | SpedizioneEbay;

export interface ArchivioEbay {
  /** App ID a cui appartengono i token: se cambia, il conto va ricollegato */
  conto?: string;
  /** access e refresh cifrati; scadenze in ISO */
  token?: { access: string; scade: string; refresh: string; refreshScade: string };
  /** Valore casuale del consenso in corso (anti-CSRF), valido pochi minuti */
  state?: { valore: string; scade: string };
  /** Inizio dell'ultimo controllo delle vendite (da qualunque dispositivo): i controlli dopo non guardano prima di questa data meno un'ora */
  ultimoControllo?: string;
  /** Numeri d'ordine eBay già passati a un dispositivo → quando (gli ultimi 500), per non importarli due volte */
  consegnati: Record<string, string>;
  /** Foto già caricate su eBay: indirizzo nel gestionale → indirizzo eBay (EPS) */
  foto: Record<string, { url: string; scade?: string }>;
  /** Categoria trovata per ogni parola di ricerca (in minuscolo), con la data: dopo 30 giorni si cerca di nuovo */
  categorie: Record<string, { id: string; nome: string; at?: string }>;
  politiche: Partial<Record<RuoloPolitica, { id: string; nome: string }>>;
  magazzino?: { id: string; nome: string };
  esauritoAttivo?: boolean;
  /** SKU → numero dell'annuncio eBay, per riconoscere un annuncio chiuso da eBay */
  pubblicati: Record<string, string>;
  /** SKU ritirati da noi (non da eBay) */
  ritirati: Record<string, boolean>;
  /** Ultimo errore del collegamento, già in italiano semplice */
  errore?: string;
}

const vuoto = (): ArchivioEbay => ({ consegnati: {}, foto: {}, categorie: {}, politiche: {}, pubblicati: {}, ritirati: {} });

export async function leggiArchivio(): Promise<ArchivioEbay> {
  try {
    return { ...vuoto(), ...(JSON.parse(await readFile(FILE, "utf8")) as Partial<ArchivioEbay>) };
  } catch {
    return vuoto();
  }
}

async function scrivi(a: ArchivioEbay) {
  await mkdir(DATA_DIR, { recursive: true });
  const tmp = `${FILE}.${process.pid}.tmp`;
  await writeFile(tmp, JSON.stringify(a), { mode: 0o600 });
  await rename(tmp, FILE);
}

let lock: Promise<unknown> = Promise.resolve();

/** Legge, modifica e riscrive l'archivio, una modifica alla volta. */
export function aggiornaArchivio<T>(fn: (a: ArchivioEbay) => T | Promise<T>): Promise<T> {
  const run = lock.then(async () => {
    const a = await leggiArchivio();
    const out = await fn(a);
    await scrivi(a);
    return out;
  });
  lock = run.catch(() => undefined);
  return run;
}
