// Archivio condiviso di un'azienda: un file state.json nella sua cartella. Solo server.
// Un blocco per azienda: le scritture della stessa azienda vanno in fila (così l'ordine del negozio e il
// salvataggio di un dispositivo non si sovrascrivono), quelle di aziende diverse non si aspettano.
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import path from "node:path";
import { cartellaAzienda } from "@/lib/server-data";
import { STORE_SCHEMA } from "@/lib/schema";
import type { Rec, Stored } from "@/lib/archivio-unione";

const code = (a: string) => path.join(cartellaAzienda(a), "state.json");
const blocchi = new Map<string, Promise<unknown>>();

// Sempre dal file: anche altri processi sullo stesso Mac leggono e scrivono qui
export async function leggiStato(aziendaId: string): Promise<Stored> {
  try {
    return JSON.parse(await readFile(code(aziendaId), "utf8")) as Stored;
  } catch {
    return { schema: "", version: 0, state: null };
  }
}

// Si scrive in un file temporaneo e poi lo si rinomina: un arresto a metà non lascia un file tronco
async function scrivi(aziendaId: string, s: Stored, soloSeNuovo = false) {
  const dir = cartellaAzienda(aziendaId);
  await mkdir(dir, { recursive: true });
  const file = path.join(dir, "state.json");
  if (soloSeNuovo) {
    await writeFile(file, JSON.stringify(s), { flag: "wx" });
    return;
  }
  const tmp = `${file}.${process.pid}.tmp`;
  await writeFile(tmp, JSON.stringify(s));
  await rename(tmp, file);
}

export function aggiornaStato<T>(aziendaId: string, fn: (s: Stored) => { stored: Stored; risultato: T }): Promise<T> {
  cartellaAzienda(aziendaId); // id non valido: errore subito
  const prima = blocchi.get(aziendaId) ?? Promise.resolve();
  const run = prima.then(async () => {
    const { stored, risultato } = fn(await leggiStato(aziendaId));
    await scrivi(aziendaId, stored);
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
    if (!s.state) return { stored: s, risultato: undefined };
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
