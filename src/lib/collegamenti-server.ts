// Archivio dei collegamenti sul server: lettura, scrittura e segreti decifrati. Solo server.
// Lo usano la route /api/collegamenti e il ponte eBay (le route Next non possono esportare altro che gli handler).
import { cifra, decifra } from "@/lib/cifratura";
import type { Servizio, StatoServizio } from "@/lib/collegamenti";
import { CollegamentiIlleggibili } from "@/lib/collegamenti-file";
import { deposito } from "@/lib/deposito";
import { DocumentoIlleggibile } from "@/lib/deposito/tipi";

export const MAX_TEXT = 4000;
const MAX_FILE = 64 * 1024; // un certificato .p12 pesa pochi KB

export interface Salvato {
  valori: Record<string, string | string[]>;
  segreti: Record<string, string>; // cifrati
  file: Record<string, { nome: string; byte: number; dati: string }>; // dati cifrati
  aggiornato?: string;
}
export type Archivio = Record<string, Salvato>;

// Documento assente: nessun collegamento. Illeggibile o corrotto: errore (CollegamentiIlleggibili), mai {} da riscrivere.
function archivioValido(v: unknown, aziendaId: string): Archivio {
  if (v === null) return {};
  if (!v || typeof v !== "object" || Array.isArray(v)) throw new CollegamentiIlleggibili(new Error("non è un oggetto"), aziendaId);
  return v as Archivio;
}
const comeIlleggibili = (e: unknown, aziendaId: string) =>
  e instanceof DocumentoIlleggibile && !(e instanceof CollegamentiIlleggibili) ? new CollegamentiIlleggibili(e.cause, aziendaId) : e;

export async function load(aziendaId: string): Promise<Archivio> {
  try {
    return archivioValido(await deposito().leggiDocumento<Archivio>(aziendaId, "collegamenti"), aziendaId);
  } catch (e) {
    throw comeIlleggibili(e, aziendaId);
  }
}

/**
 * Lettura, modifica e scrittura dei collegamenti in un solo aggiornamento del deposito: le modifiche della stessa
 * azienda vanno in fila anche tra istanze diverse (con Supabase la riga è bloccata fino alla fine). `fn` cambia
 * l'archivio sul posto; se lancia non si scrive nulla.
 */
export async function aggiornaCollegamenti<R>(aziendaId: string, fn: (a: Archivio) => R | Promise<R>): Promise<R> {
  try {
    return await deposito().aggiornaDocumento<Archivio, R>(aziendaId, "collegamenti", async (prima) => {
      const a = archivioValido(prima, aziendaId);
      const risultato = await fn(a);
      return { dati: a, risultato };
    });
  } catch (e) {
    throw comeIlleggibili(e, aziendaId);
  }
}

/** Errore di una modifica con un messaggio da mostrare così com'è (dati sbagliati nella richiesta). */
export class ErroreCollegamenti extends Error {
  constructor(messaggio: string) {
    super(messaggio);
    this.name = "ErroreCollegamenti";
  }
}

export function pubblico(s?: Salvato): StatoServizio {
  return {
    valori: s?.valori ?? {},
    segreti: Object.fromEntries(Object.keys(s?.segreti ?? {}).map((k) => [k, true])),
    file: Object.fromEntries(Object.entries(s?.file ?? {}).map(([k, f]) => [k, { nome: f.nome, byte: f.byte }])),
    aggiornato: s?.aggiornato,
  };
}

export interface ModificaCollegamento {
  id: string;
  valori?: Record<string, unknown>;
  segreti?: Record<string, unknown>; // solo quelli nuovi; vuoto = invariato
  file?: Record<string, { nome?: unknown; dati?: unknown }>; // dati in base64
  togli?: string[]; // segreti o file da cancellare
}

// Campi che dicono dove mandare le credenziali: se cambiano, la password salvata va reinserita,
// così nessuno può dirottarla verso un altro indirizzo senza conoscerla
const INDIRIZZI = ["endpoint"];

/** Applica la modifica di un servizio e la salva, tutto dentro lo stesso aggiornamento. Dati sbagliati: ErroreCollegamenti. */
export function modificaServizio(aziendaId: string, serv: Servizio, body: ModificaCollegamento): Promise<StatoServizio> {
  const campo = (k: string) => serv.campi.find((c) => c.key === k);
  return aggiornaCollegamenti(aziendaId, async (a) => {
    const s: Salvato = a[serv.id] ?? { valori: {}, segreti: {}, file: {} };

    // Valgono solo le password già salvate e reinserite tutte in questa richiesta
    const nuoviSegreti = Object.keys(s.segreti).every((k) => {
      const v = body.segreti?.[k];
      return typeof v === "string" && !!v;
    });
    const cambiaIndirizzo = INDIRIZZI.some((k) => {
      const v = body.valori?.[k];
      return typeof v === "string" && v.trim() !== (s.valori[k] ?? "");
    });
    if (cambiaIndirizzo && Object.keys(s.segreti).length && !nuoviSegreti) {
      throw new ErroreCollegamenti("Hai cambiato l'indirizzo del servizio: reinserisci la password per confermare.");
    }

    for (const [k, v] of Object.entries(body.valori ?? {})) {
      const c = campo(k);
      if (!c || c.tipo === "segreto" || c.tipo === "file") continue;
      if (c.tipo === "multipla") {
        if (Array.isArray(v)) s.valori[k] = v.filter((x): x is string => typeof x === "string" && !!c.opzioni?.includes(x));
      } else if (typeof v === "string") {
        if (c.tipo === "scelta" && v && !c.opzioni?.includes(v)) continue;
        s.valori[k] = v.trim().slice(0, MAX_TEXT);
      }
    }
    for (const [k, v] of Object.entries(body.segreti ?? {})) {
      if (campo(k)?.tipo !== "segreto" || typeof v !== "string" || !v) continue;
      s.segreti[k] = await cifra(Buffer.from(v.slice(0, MAX_TEXT), "utf8"));
    }
    for (const [k, f] of Object.entries(body.file ?? {})) {
      if (campo(k)?.tipo !== "file" || typeof f?.dati !== "string") continue;
      const bytes = Buffer.from(f.dati, "base64");
      if (!bytes.length || bytes.length > MAX_FILE) throw new ErroreCollegamenti("File vuoto o troppo grande (massimo 64 KB)");
      s.file[k] = { nome: String(f.nome ?? "certificato").slice(0, 200), byte: bytes.length, dati: await cifra(bytes) };
    }
    for (const k of body.togli ?? []) {
      delete s.segreti[k];
      delete s.file[k];
    }
    s.aggiornato = new Date().toISOString();
    a[serv.id] = s;
    return pubblico(s);
  });
}

/** Scollega: toglie tutti i dati salvati del servizio. */
export function scollegaServizio(aziendaId: string, id: string): Promise<void> {
  return aggiornaCollegamenti(aziendaId, (a) => {
    delete a[id];
  });
}

/**
 * Esito di un salvataggio non riuscito per il browser: i messaggi noti (dati sbagliati, documento illeggibile) così
 * come sono, tutto il resto (database, chiave di cifratura…) con un messaggio generico; l'errore vero va nel log.
 */
export function erroreSalvataggio(e: unknown): { status: number; error: string } {
  if (e instanceof ErroreCollegamenti || e instanceof CollegamentiIlleggibili) return { status: 400, error: e.message };
  console.error("Collegamenti non salvati", e);
  return { status: 500, error: "Salvataggio non riuscito: riprova tra poco. Se continua, avvisa l'assistenza." };
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
