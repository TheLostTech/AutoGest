// Abbonamento di un'azienda: un documento "abbonamento" nel deposito (su disco: abbonamento.json). Solo server.
import { deposito } from "@/lib/deposito";
import { DocumentoIlleggibile } from "@/lib/deposito/tipi";
import type { Abbonamento } from "@/lib/abbonamento";

/** Per il browser quando l'abbonamento non si legge adesso (database o rete): il dettaglio resta nel log. */
export const ABBONAMENTO_NON_LEGGIBILE = "Non riesco a leggere l'abbonamento: riprova tra poco.";

/**
 * Assente: null. Corrotto (DocumentoIlleggibile): errore nel log e null (si tratta da nuovo).
 * Ogni altro errore (database, rete) arriva a chi chiama: un'azienda che paga non deve sembrare senza abbonamento.
 */
export async function leggiAbbonamento(aziendaId: string): Promise<Abbonamento | null> {
  try {
    return await deposito().leggiDocumento<Abbonamento>(aziendaId, "abbonamento");
  } catch (e) {
    if (!(e instanceof DocumentoIlleggibile)) throw e;
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
