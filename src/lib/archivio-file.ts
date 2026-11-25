import { readFile } from "node:fs/promises";
import type { Stored } from "./archivio-unione.ts";
import { DocumentoIlleggibile } from "./deposito/tipi.ts";

/** Errore di un archivio che esiste ma non si legge o non è JSON valido: mai da sovrascrivere. */
export class ArchivioIlleggibile extends DocumentoIlleggibile {
  constructor(causa: unknown, aziendaId = "") {
    super("archivio", aziendaId, causa);
    this.message = "L'archivio dell'azienda non si legge (file danneggiato o non accessibile).";
  }
}

/** File assente -> archivio vuoto (state null). File presente ma illeggibile o corrotto -> errore, così nessuno lo sovrascrive. */
export async function leggiStatoDaFile(file: string): Promise<Stored> {
  let testo: string;
  try {
    testo = await readFile(file, "utf8");
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") return { schema: "", version: 0, state: null };
    throw new ArchivioIlleggibile(e);
  }
  try {
    const v = JSON.parse(testo) as Stored;
    if (!v || typeof v !== "object") throw new Error("non è un oggetto");
    return v;
  } catch (e) {
    throw new ArchivioIlleggibile(e);
  }
}
