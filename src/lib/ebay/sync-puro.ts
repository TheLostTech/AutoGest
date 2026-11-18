// Scelta e applicazione dei risultati del riallineamento eBay. Modulo puro: solo import di tipi.
import type { Annuncio, AnnuncioEbay } from "../types";
import type { EsitoAllinea } from "./contratto";

export interface Inviato {
  quantita: number;
  prezzo: number;
  /** Se la richiesta chiedeva l'annuncio attivo (false = ritiro) */
  attivo?: boolean;
  titolo?: string;
}

/**
 * Il prossimo annuncio da mandare a eBay: solo quelli già pensati per eBay (stato diverso da "non pubblicato")
 * e da riallineare; prima quelli senza errore, così un errore non blocca gli altri.
 */
export function nextToSync(annunci: Annuncio[]): Annuncio | undefined {
  const da = annunci.filter((a) => a.ebay && a.ebay.daRiallineare === true && a.ebay.stato !== "non pubblicato");
  return da.find((a) => !a.ebay?.errore) ?? da[0];
}

/** Il nuovo stato eBay dell'annuncio dopo la risposta del ponte. In errore resta da riallineare. */
export function applyEsito(a: Annuncio, esito: EsitoAllinea, inviato: Inviato, at: string): AnnuncioEbay {
  const prev: AnnuncioEbay = a.ebay ?? { stato: "non pubblicato", daRiallineare: true };
  if (esito.stato === "errore") {
    return {
      ...prev,
      // Un ritiro fallito resta un ritiro: al giro dopo non deve rimettere l'annuncio online
      stato: prev.stato === "ritirato" ? "ritirato" : "errore",
      daRiallineare: true,
      errore: esito.errore || "eBay ha rifiutato l'annuncio",
      avvisi: esito.avvisi,
      aggiornatoAt: at,
    };
  }
  return {
    stato: esito.stato,
    daRiallineare: false,
    listingId: esito.listingId ?? prev.listingId,
    url: esito.url ?? prev.url,
    categoria: esito.categoria ?? prev.categoria,
    quantitaInviata: inviato.quantita,
    prezzoInviato: inviato.prezzo,
    errore: undefined,
    avvisi: esito.avvisi,
    aggiornatoAt: at,
  };
}
