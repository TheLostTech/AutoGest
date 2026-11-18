// File collegamenti.json di un'azienda: lettura e scrittura sicure. Solo server; senza alias "@/" per i test.
// Stessa regola dell'archivio (archivio-file.ts): file assente = nessun collegamento; file presente ma illeggibile o
// non JSON valido = errore, mai un archivio vuoto (il salvataggio dopo cancellerebbe le credenziali di tutti i servizi).
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import path from "node:path";

export class CollegamentiIlleggibili extends Error {
  constructor(causa: unknown) {
    super("Il file dei collegamenti non si legge (danneggiato o non accessibile).", { cause: causa });
  }
}

export async function leggiCollegamentiDaFile<T extends object>(file: string): Promise<T> {
  let testo: string;
  try {
    testo = await readFile(file, "utf8");
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") return {} as T;
    throw new CollegamentiIlleggibili(e);
  }
  try {
    const v = JSON.parse(testo) as unknown;
    if (!v || typeof v !== "object" || Array.isArray(v)) throw new Error("non è un oggetto");
    return v as T;
  } catch (e) {
    throw new CollegamentiIlleggibili(e);
  }
}

/** File temporaneo (solo per il proprietario) e poi rinomina: un arresto a metà non lascia un file tronco. */
export async function scriviCollegamentiSuFile(file: string, dati: object): Promise<void> {
  await mkdir(path.dirname(file), { recursive: true });
  const tmp = `${file}.${process.pid}.${Date.now()}.tmp`;
  await writeFile(tmp, JSON.stringify(dati), { mode: 0o600 });
  await rename(tmp, file);
}
