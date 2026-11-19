// Moduli attivi letti sul server dall'archivio dell'azienda: i servizi che costano li controllano
// prima di chiamare l'esterno. Archivio assente o illeggibile = tutti attivi (come per i dati salvati prima dei moduli).
import { readFile } from "node:fs/promises";
import path from "node:path";
import { DATA_DIR } from "./server-data";
import { moduliDaArchivio, type Modulo } from "./moduli";

export async function moduloAttivoSulServer(m: Modulo): Promise<boolean> {
  let raw: unknown = null;
  try {
    raw = JSON.parse(await readFile(path.join(DATA_DIR, "state.json"), "utf8"));
  } catch {
    /* archivio assente: tutti attivi */
  }
  return moduliDaArchivio(raw).has(m);
}
