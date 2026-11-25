// Archivio condiviso di un'azienda: un documento "archivio" nel deposito (su disco: state.json). Solo server.
// Le scritture della stessa azienda vanno in fila nel deposito (così l'ordine del negozio e il salvataggio di
// un dispositivo non si sovrascrivono), quelle di aziende diverse non si aspettano.
import { ArchivioIlleggibile } from "@/lib/archivio-file";
import { deposito } from "@/lib/deposito";
import { DocumentoIlleggibile } from "@/lib/deposito/tipi";
import { STORE_SCHEMA } from "@/lib/schema";
import type { Rec, Stored } from "@/lib/archivio-unione";

// Archivio assente: state null, versione 0
const VUOTO: Stored = { schema: "", version: 0, state: null };

const comeArchivio = (aziendaId: string, e: unknown): unknown => (e instanceof DocumentoIlleggibile && !(e instanceof ArchivioIlleggibile) ? new ArchivioIlleggibile(e.cause, aziendaId) : e);
const controlla = (aziendaId: string, v: Stored | null): Stored | null => {
  if (v !== null && (!v || typeof v !== "object")) throw new ArchivioIlleggibile(new Error("non è un oggetto"), aziendaId);
  return v;
};

// Sempre dal deposito: anche altri processi sullo stesso Mac leggono e scrivono qui
// Archivio assente: state null. Presente ma illeggibile o corrotto: errore (ArchivioIlleggibile), mai da sovrascrivere.
export async function leggiStato(aziendaId: string): Promise<Stored> {
  try {
    return controlla(aziendaId, await deposito().leggiDocumento<Stored>(aziendaId, "archivio")) ?? VUOTO;
  } catch (e) {
    throw comeArchivio(aziendaId, e);
  }
}

export async function aggiornaStato<T>(aziendaId: string, fn: (s: Stored) => { stored: Stored; risultato: T; nonScrivere?: boolean }): Promise<T> {
  try {
    return await deposito().aggiornaDocumento<Stored, T>(aziendaId, "archivio", (prima) => {
      const { stored, risultato, nonScrivere } = fn(controlla(aziendaId, prima) ?? VUOTO);
      return { dati: stored, risultato, nonScrivere };
    });
  } catch (e) {
    throw comeArchivio(aziendaId, e);
  }
}

/** Crea l'archivio di un'azienda nuova; se c'è già non tocca nulla. */
export async function creaStatoAzienda(aziendaId: string, stato: Record<string, unknown>): Promise<void> {
  const stored: Stored = { schema: STORE_SCHEMA, version: 1, state: stato };
  await deposito().creaDocumento(aziendaId, "archivio", stored);
}

export interface NuovoEvento {
  user: string;
  role: string;
  device: string;
  entity: string;
  entityId: string;
  action: string;
  detail?: string;
}

/** Aggiunge righe al registro attività nello stesso blocco delle altre scritture. */
export async function aggiungiEventi(aziendaId: string, eventi: NuovoEvento[]): Promise<void> {
  if (!eventi.length) return;
  await aggiornaStato(aziendaId, (s) => {
    // Senza archivio non c'è dove scrivere: meglio un errore che un evento perso in silenzio
    if (!s.state) throw new Error("Archivio dell'azienda assente: registro attività non aggiornato.");
    const st = { ...s.state };
    const counters = { ...((st.counters as Record<string, number> | undefined) ?? {}) };
    const audit = [...((st.audit as Rec[] | undefined) ?? [])];
    for (const e of eventi) {
      counters.event = (counters.event ?? 0) + 1;
      audit.push({ id: `E-${String(counters.event).padStart(6, "0")}`, at: new Date().toISOString(), ...e });
    }
    st.counters = counters;
    st.audit = audit;
    return { stored: { ...s, version: s.version + 1, state: st }, risultato: undefined };
  });
}
