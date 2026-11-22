// Archivio dell'abbonamento di un'azienda: un file abbonamento.json nella sua cartella. Solo server.
// Stesso schema di archivio-azienda.ts: blocco in memoria per azienda e scrittura con file temporaneo + rinomina.
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import path from "node:path";
import { cartellaAzienda } from "@/lib/server-data";
import type { Abbonamento } from "@/lib/abbonamento";

const g = globalThis as typeof globalThis & { __blocchiAbbonamento?: Map<string, Promise<unknown>> };
const blocchi = (g.__blocchiAbbonamento ??= new Map<string, Promise<unknown>>());

const file = (id: string) => path.join(cartellaAzienda(id), "abbonamento.json");

/** File assente: null. File illeggibile o corrotto: errore nel log e null (si tratta da nuovo; la prossima sincronizzazione lo riscrive). */
export async function leggiAbbonamento(aziendaId: string): Promise<Abbonamento | null> {
  try {
    return JSON.parse(await readFile(file(aziendaId), "utf8")) as Abbonamento;
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") return null;
    console.error("Abbonamento non leggibile", aziendaId, e);
    return null;
  }
}

export function aggiornaAbbonamento(aziendaId: string, fn: (prima: Abbonamento | null) => Abbonamento): Promise<Abbonamento> {
  const f = file(aziendaId); // id non valido: errore subito
  const prima = blocchi.get(aziendaId) ?? Promise.resolve();
  const run = prima.then(async () => {
    const nuovo = fn(await leggiAbbonamento(aziendaId));
    await mkdir(path.dirname(f), { recursive: true });
    const tmp = `${f}.${process.pid}.tmp`;
    await writeFile(tmp, JSON.stringify(nuovo));
    await rename(tmp, f);
    return nuovo;
  });
  const coda = run.catch(() => undefined);
  blocchi.set(aziendaId, coda);
  void coda.then(() => {
    if (blocchi.get(aziendaId) === coda) blocchi.delete(aziendaId);
  });
  return run;
}
