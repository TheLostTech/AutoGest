// Archivio condiviso di un'azienda: un file state.json nella sua cartella. Solo server.
// Un blocco per azienda: le scritture della stessa azienda vanno in fila (così l'ordine del negozio e il
// salvataggio di un dispositivo non si sovrascrivono), quelle di aziende diverse non si aspettano.
import { mkdir, rename, writeFile } from "node:fs/promises";
import path from "node:path";
import { leggiStatoDaFile } from "@/lib/archivio-file";
import { creaUnaVolta } from "@/lib/file-una-volta";
import { cartellaAzienda } from "@/lib/server-data";
import { STORE_SCHEMA } from "@/lib/schema";
import type { Rec, Stored } from "@/lib/archivio-unione";

const code = (a: string) => path.join(cartellaAzienda(a), "state.json");
// Sulla globalThis: le route di Next possono avere ognuna la propria copia di questo modulo, ma il blocco deve essere uno solo
// (l'ordine del negozio e il salvataggio di un dispositivo passano da route diverse).
const g = globalThis as typeof globalThis & { __blocchiArchivio?: Map<string, Promise<unknown>> };
const blocchi = (g.__blocchiArchivio ??= new Map<string, Promise<unknown>>());

// Sempre dal file: anche altri processi sullo stesso Mac leggono e scrivono qui
// File assente: state null. File presente ma illeggibile o corrotto: errore (ArchivioIlleggibile), mai da sovrascrivere.
export function leggiStato(aziendaId: string): Promise<Stored> {
  return leggiStatoDaFile(code(aziendaId));
}

// Si scrive in un file temporaneo e poi lo si rinomina: un arresto a metà non lascia un file tronco
async function scrivi(aziendaId: string, s: Stored, soloSeNuovo = false) {
  const dir = cartellaAzienda(aziendaId);
  await mkdir(dir, { recursive: true });
  const file = path.join(dir, "state.json");
  if (soloSeNuovo) {
    // Già completo quando compare: chi legge in quel momento non lo trova a metà (e non lo crede corrotto)
    if (!(await creaUnaVolta(file, JSON.stringify(s), 0o644))) throw Object.assign(new Error("Archivio già presente"), { code: "EEXIST" });
    return;
  }
  const tmp = `${file}.${process.pid}.tmp`;
  await writeFile(tmp, JSON.stringify(s));
  await rename(tmp, file);
}

export function aggiornaStato<T>(aziendaId: string, fn: (s: Stored) => { stored: Stored; risultato: T; nonScrivere?: boolean }): Promise<T> {
  cartellaAzienda(aziendaId); // id non valido: errore subito
  const prima = blocchi.get(aziendaId) ?? Promise.resolve();
  const run = prima.then(async () => {
    const { stored, risultato, nonScrivere } = fn(await leggiStato(aziendaId));
    if (!nonScrivere) await scrivi(aziendaId, stored);
    return risultato;
  });
  const coda = run.catch(() => undefined);
  blocchi.set(aziendaId, coda);
  void coda.then(() => {
    if (blocchi.get(aziendaId) === coda) blocchi.delete(aziendaId);
  });
  return run;
}

/** Crea l'archivio di un'azienda nuova; se il file c'è già non tocca nulla. */
export async function creaStatoAzienda(aziendaId: string, stato: Record<string, unknown>): Promise<void> {
  const prima = blocchi.get(aziendaId) ?? Promise.resolve();
  const run = prima.then(async () => {
    try {
      await scrivi(aziendaId, { schema: STORE_SCHEMA, version: 1, state: stato }, true);
    } catch (e) {
      if ((e as NodeJS.ErrnoException).code !== "EEXIST") throw e;
    }
  });
  const coda = run.catch(() => undefined);
  blocchi.set(aziendaId, coda);
  void coda.then(() => {
    if (blocchi.get(aziendaId) === coda) blocchi.delete(aziendaId);
  });
  await run;
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
