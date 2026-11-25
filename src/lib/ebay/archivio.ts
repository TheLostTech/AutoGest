// Archivio del ponte eBay sul server: file ebay.json nella cartella di ogni azienda (aziende/<id>/ebay.json), leggibile solo dal processo (0600).
// Token di accesso e di rinnovo cifrati con cifra(); niente di questo file va mai al browser.
// Solo server.
import { deposito } from "@/lib/deposito";
import { DocumentoIlleggibile } from "@/lib/deposito/tipi";
import type { SpedizioneEbay } from "./contratto";

export type RuoloPolitica = "pagamento" | "reso" | SpedizioneEbay;

export interface ArchivioEbay {
  /** App ID a cui appartengono i token: se cambia, il conto va ricollegato */
  conto?: string;
  /** access e refresh cifrati; scadenze in ISO */
  token?: { access: string; scade: string; refresh: string; refreshScade: string };
  /** Valore casuale del consenso in corso (anti-CSRF), valido pochi minuti e solo per chi lo ha avviato (userId) */
  state?: { valore: string; userId: string; scade: string };
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

/** Assente o corrotto (DocumentoIlleggibile): archivio vuoto. Ogni altro errore (database, rete) arriva a chi chiama. */
export async function leggiArchivio(aziendaId: string): Promise<ArchivioEbay> {
  try {
    return { ...vuoto(), ...((await deposito().leggiDocumento<Partial<ArchivioEbay>>(aziendaId, "ebay")) ?? {}) };
  } catch (e) {
    if (!(e instanceof DocumentoIlleggibile)) throw e;
    console.error("[ebay] archivio non leggibile", aziendaId, e);
    return vuoto();
  }
}

/** Legge, modifica e riscrive l'archivio, una modifica alla volta (la fila per azienda è del deposito). */
export function aggiornaArchivio<T>(aziendaId: string, fn: (a: ArchivioEbay) => T | Promise<T>): Promise<T> {
  return deposito().aggiornaDocumento<ArchivioEbay, T>(aziendaId, "ebay", async (prima) => {
    const a: ArchivioEbay = { ...vuoto(), ...(prima ?? {}) };
    const risultato = await fn(a);
    return { dati: a, risultato };
  });
}
