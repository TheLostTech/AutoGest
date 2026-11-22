// Moduli attivi letti sul server: i servizi che costano li controllano prima di chiamare l'esterno.
// Azienda registrata: decide l'abbonamento (file assente = nuovo). Le altre: l'archivio dell'azienda;
// archivio assente o illeggibile = tutti attivi (come per i dati salvati prima dei moduli).
import { leggiStato } from "./archivio-azienda";
import { ABBONAMENTO_NUOVO, moduliDaAbbonamento } from "./abbonamento";
import { leggiAbbonamento } from "./abbonamento-server";
import { moduliDaArchivio, type Modulo } from "./moduli";

export async function moduloAttivoSulServer(azienda: { id: string; registrata: boolean }, m: Modulo): Promise<boolean> {
  if (azienda.registrata) {
    return moduliDaAbbonamento((await leggiAbbonamento(azienda.id)) ?? ABBONAMENTO_NUOVO(true, Date.now())).includes(m);
  }
  let stored: unknown = null;
  try {
    stored = await leggiStato(azienda.id);
  } catch {
    /* archivio illeggibile: tutti attivi */
  }
  return moduliDaArchivio(stored).has(m);
}
