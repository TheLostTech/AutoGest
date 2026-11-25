// Abbonamento di un'azienda: un documento "abbonamento" nel deposito (su disco: abbonamento.json). Solo server.
import { deposito } from "@/lib/deposito";
import type { Abbonamento } from "@/lib/abbonamento";

/** Assente: null. Illeggibile o corrotto: errore nel log e null (si tratta da nuovo). */
export async function leggiAbbonamento(aziendaId: string): Promise<Abbonamento | null> {
  try {
    return await deposito().leggiDocumento<Abbonamento>(aziendaId, "abbonamento");
  } catch (e) {
    console.error("Abbonamento non leggibile", aziendaId, e);
    return null;
  }
}

export function aggiornaAbbonamento(aziendaId: string, fn: (prima: Abbonamento | null) => Abbonamento): Promise<Abbonamento> {
  return deposito().aggiornaDocumento<Abbonamento, Abbonamento>(aziendaId, "abbonamento", (prima) => {
    const nuovo = fn(prima);
    return { dati: nuovo, risultato: nuovo };
  });
}
