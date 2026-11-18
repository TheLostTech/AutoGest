"use client";

// L'azienda con cui questa scheda è partita. Si fissa una volta, all'avvio della gestione (Hydrator), e va in ogni
// chiamata alle API dell'azienda (intestazione x-azienda). Se la sessione nel frattempo è passata a un'altra azienda
// (ingresso di assistenza aperto in un'altra scheda), il server risponde 409 "azienda-cambiata": questa scheda smette di
// leggere e scrivere (sincronizzazione, eBay, modifiche in sospeso) e chiede di ricaricare.
// L'azienda la decide sempre la sessione: l'intestazione serve solo a far rifiutare una richiesta fuori posto.
import { INTESTAZIONE_AZIENDA, MOTIVO_AZIENDA_CAMBIATA } from "./regole";

let fissata: string | null = null;
let cambiata = false;
const ascoltatori = new Set<() => void>();

/** Una volta sola per pagina: la prima azienda vince (una scheda non cambia azienda senza ricaricare). */
export function fissaAzienda(id: string): void {
  fissata ??= id;
}
export const aziendaFissata = (): string | null => fissata;
export const aziendaCambiataQui = (): boolean => cambiata;

export function intestazioniAzienda(): Record<string, string> {
  return fissata ? { [INTESTAZIONE_AZIENDA]: fissata } : {};
}

/** Segnala (una volta) che la sessione non è più dell'azienda di questa scheda. */
export function segnalaAziendaCambiata(): void {
  if (cambiata) return;
  cambiata = true;
  ascoltatori.forEach((f) => f());
}
export function suAziendaCambiata(f: () => void): () => void {
  ascoltatori.add(f);
  return () => void ascoltatori.delete(f);
}

/** Risposta 409 del server per una scheda partita con un'altra azienda? (legge una copia del corpo) */
export async function eAziendaCambiata(r: Response): Promise<boolean> {
  if (r.status !== 409) return false;
  const j = (await r.clone().json().catch(() => null)) as { motivo?: unknown; code?: unknown } | null;
  return j?.motivo === MOTIVO_AZIENDA_CAMBIATA || j?.code === "AZIENDA_CAMBIATA";
}

/** fetch per le API dell'azienda: aggiunge x-azienda e, se il server risponde "azienda cambiata", lo segnala. */
export async function fetchAzienda(input: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  for (const [k, v] of Object.entries(intestazioniAzienda())) headers.set(k, v);
  const r = await fetch(input, { ...init, headers });
  if (await eAziendaCambiata(r)) segnalaAziendaCambiata();
  return r;
}

// Avviso alle altre schede dello stesso browser: l'azienda della sessione è cambiata (ingresso o uscita di assistenza).
// Le schede della gestione partite con un'altra azienda si fermano e si ricaricano (vedi Hydrator).
export const CHIAVE_AZIENDA_SESSIONE = "gestionale-azienda-sessione";

export function annunciaAziendaSessione(aziendaId: string | null): void {
  try {
    localStorage.setItem(CHIAVE_AZIENDA_SESSIONE, JSON.stringify({ azienda: aziendaId, at: Date.now() }));
  } catch {}
}

/** Dall'evento `storage`: l'azienda annunciata da un'altra scheda, se la chiave è quella giusta (undefined: altro evento). */
export function aziendaDaAnnuncio(e: StorageEvent): string | null | undefined {
  if (e.key !== CHIAVE_AZIENDA_SESSIONE || !e.newValue) return undefined;
  try {
    const v = JSON.parse(e.newValue) as { azienda?: unknown };
    return typeof v.azienda === "string" ? v.azienda : null;
  } catch {
    return undefined;
  }
}
