// Moduli attivi letti sul server dall'archivio dell'azienda: i servizi che costano li controllano
// prima di chiamare l'esterno. Archivio assente o illeggibile = tutti attivi (come per i dati salvati prima dei moduli).
import { leggiStato } from "./archivio-azienda";
import { moduliDaArchivio, type Modulo } from "./moduli";

export async function moduloAttivoSulServer(aziendaId: string, m: Modulo): Promise<boolean> {
  let stored: unknown = null;
  try {
    stored = await leggiStato(aziendaId);
  } catch {
    /* archivio illeggibile: tutti attivi */
  }
  return moduliDaArchivio(stored).has(m);
}
