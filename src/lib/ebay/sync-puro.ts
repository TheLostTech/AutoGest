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

/** Quantità e prezzo online di adesso, per confrontarli con quelli mandati a eBay. */
export interface Attuale {
  quantita: number;
  prezzo: number;
}

/**
 * Il prossimo annuncio da mandare a eBay: solo quelli già pensati per eBay (stato diverso da "non pubblicato")
 * e da riallineare; prima quelli senza errore, così un errore non blocca gli altri.
 * Con `attuale` valgono da riallineare anche gli annunci attivi su eBay con quantità o prezzo di adesso diversi da
 * quelli mandati: il segno "da riallineare" si può perdere quando due dispositivi scrivono insieme (vince l'ultimo),
 * così la differenza si corregge da sola.
 */
export function nextToSync(annunci: Annuncio[], attuale?: (a: Annuncio) => Attuale): Annuncio | undefined {
  const da = annunci.filter((a) => {
    const e = a.ebay;
    if (!e || e.stato === "non pubblicato") return false;
    if (e.daRiallineare === true) return true;
    if (!attuale || e.stato === "ritirato") return false;
    const ora = attuale(a);
    return e.quantitaInviata !== ora.quantita || e.prezzoInviato !== ora.prezzo;
  });
  return da.find((a) => !a.ebay?.errore) ?? da[0];
}

/**
 * Risposta del ponte non riuscita (stato HTTP; 0 = niente rete):
 * - 4xx: è la richiesta che non va (troppo grande, non valida): errore salvato sull'annuncio, si passa agli altri;
 * - 5xx: server in difficoltà su questo annuncio: "salta", si prova il prossimo e questo riparte al giro dei 60 secondi;
 * - 0: niente rete, inutile provare gli altri: "fermati".
 */
export function esitoDaStato(status: number): EsitoAllinea | "salta" | "fermati" {
  if (status === 413) return { stato: "errore", avvisi: [], errore: "La richiesta per eBay è troppo grande. Cosa fare: accorcia la descrizione dell'annuncio." };
  if (status === 400) return { stato: "errore", avvisi: [], errore: "La richiesta per eBay non è valida: controlla titolo, prezzo e foto" };
  if (status >= 400 && status < 500)
    return { stato: "errore", avvisi: [], errore: `Il gestionale ha rifiutato la richiesta per eBay (codice ${status}). Cosa fare: ricarica la pagina; se si ripete, chiedi assistenza.` };
  if (status === 0) return "fermati";
  return "salta";
}

const ORA = 3600_000;
/** Sovrapposizione del controllo vendite: un ordine che eBay mostra in ritardo, o un orologio un po' avanti, non si perde. */
export const SOVRAPPOSIZIONE_VENDITE = ORA;

/** Da quando chiedere le vendite: ultimo controllo meno un'ora (le già importate si scartano per numero d'ordine); al primo controllo, 7 giorni. */
export function daPerVendite(ultimo: string | null | undefined, ora: number): string {
  const t = ultimo ? Date.parse(ultimo) : NaN;
  return new Date(Number.isNaN(t) ? ora - 7 * 24 * ORA : t - SOVRAPPOSIZIONE_VENDITE).toISOString();
}

/**
 * Il nuovo stato eBay dell'annuncio dopo la risposta del ponte. In errore resta da riallineare.
 * `cambiato`: nel frattempo l'annuncio è cambiato (quantità, prezzo, titolo) rispetto alla richiesta.
 * Se è cambiato il ritiro/ripubblicazione, lo stato di adesso vince sulla risposta a una richiesta vecchia.
 */
export function applyEsito(a: Annuncio, esito: EsitoAllinea, inviato: Inviato, at: string, cambiato = false): AnnuncioEbay {
  const prev: AnnuncioEbay = a.ebay ?? { stato: "non pubblicato", daRiallineare: true };
  if (esito.stato === "errore") {
    return {
      ...prev,
      // Categoria rifiutata da eBay: quella proposta da eBay si dimentica (al giro dopo se ne cerca un'altra);
      // quella scritta dall'operatore resta finché non la cambia lui
      categoria: esito.categoriaRifiutata && !prev.categoria?.manuale ? undefined : prev.categoria,
      // Un ritiro fallito resta un ritiro; un annuncio già online resta com'era, con l'errore accanto
      stato: prev.stato === "ritirato" || prev.listingId ? prev.stato : "errore",
      daRiallineare: true,
      errore: esito.errore || "eBay ha rifiutato l'annuncio",
      avvisi: esito.avvisi,
      aggiornatoAt: at,
    };
  }
  const attivoOra = prev.stato !== "ritirato";
  const attivoCambiato = inviato.attivo !== undefined && inviato.attivo !== attivoOra;
  return {
    stato: attivoCambiato ? prev.stato : esito.stato,
    daRiallineare: attivoCambiato || cambiato,
    listingId: esito.listingId ?? prev.listingId,
    url: esito.url ?? prev.url,
    categoria: categoriaDopo(prev, esito),
    quantitaInviata: inviato.quantita,
    prezzoInviato: inviato.prezzo,
    errore: undefined,
    avvisi: esito.avvisi,
    aggiornatoAt: at,
  };
}

/** La categoria scritta dall'operatore resta sua (con il nome di eBay, se arriva); altrimenti vale quella usata da eBay. */
function categoriaDopo(prev: AnnuncioEbay, esito: EsitoAllinea): AnnuncioEbay["categoria"] {
  const p = prev.categoria;
  if (p?.manuale) return esito.categoria?.id === p.id ? { ...p, nome: esito.categoria.nome } : p;
  return esito.categoria ?? p;
}
