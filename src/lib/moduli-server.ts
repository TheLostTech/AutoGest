// Moduli attivi letti sul server: i servizi che costano li controllano prima di chiamare l'esterno.
// Azienda registrata: decide l'abbonamento (file assente = nuovo). Le altre: l'archivio dell'azienda;
// archivio assente o illeggibile = tutti attivi (come per i dati salvati prima dei moduli).
import { leggiStato } from "./archivio-azienda";
import { ABBONAMENTO_NUOVO, moduliDaAbbonamento } from "./abbonamento";
import { ABBONAMENTO_NON_LEGGIBILE, leggiAbbonamento } from "./abbonamento-server";
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

/**
 * null se il modulo è attivo per l'azienda. Altrimenti la risposta: 403 se è spento, 503 se adesso l'abbonamento non
 * si legge (database o rete): un errore passeggero non deve far sembrare spento un modulo pagato, né lasciarlo passare.
 */
export async function rispostaModuloSpento(azienda: { id: string; registrata: boolean }, m: Modulo, nome: string): Promise<Response | null> {
  const headers = { "Cache-Control": "no-store" };
  try {
    if (await moduloAttivoSulServer(azienda, m)) return null;
  } catch (e) {
    console.error("Moduli attivi non letti", azienda.id, e);
    return Response.json({ error: ABBONAMENTO_NON_LEGGIBILE }, { status: 503, headers });
  }
  return Response.json({ error: `Il modulo ${nome} non è attivo` }, { status: 403, headers });
}
