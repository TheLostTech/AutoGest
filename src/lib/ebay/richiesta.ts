// Dall'annuncio alla richiesta per eBay. Modulo puro: niente import di codice, quindi tutto ciò che
// dipende dal catalogo o dai pezzi arriva già calcolato nel contesto `ctx`.
//
// Chi chiama (il sincronizzatore del Task 9, lato browser, dove gli import di codice sono ammessi) calcola:
//  - quantita: quantityOf(a, parts) da annunci.ts;
//  - foto: quelle di nextToShip(a, parts)[0] oppure, a zero pezzi, dell'ultimo pezzo entrato;
//  - compatibilita: compatVehicles(...);
//  - categoriaQuery: EBAY_CATEGORY_QUERY[a.typeId];
//  - typeShippable: il flag `shippable` del tipo di pezzo.
import type { Annuncio, VeicoloCompat } from "../types";
import type { RichiestaAllinea, SpedizioneEbay } from "./contratto";

export interface ContestoRichiesta {
  quantita: number;
  foto: string[];
  compatibilita: VeicoloCompat[];
  categoriaQuery: string;
  typeShippable: boolean;
}

export function richiestaPer(a: Annuncio, ctx: ContestoRichiesta, online: (base: number) => number): RichiestaAllinea {
  const spedizione: SpedizioneEbay = !a.spedibile ? "ritiro" : ctx.typeShippable ? "corriere" : "voluminoso";
  return {
    sku: a.id,
    attivo: a.ebay?.stato !== "ritirato",
    quantita: ctx.quantita,
    prezzo: online(a.price),
    titolo: a.titolo,
    descrizione: a.descrizione,
    categoriaQuery: ctx.categoriaQuery,
    categoriaId: a.ebay?.categoria?.id,
    condizione: a.condition,
    caratteristiche: a.caratteristiche,
    foto: ctx.foto,
    compatibilita: ctx.compatibilita,
    spedizione,
    gpsr: a.gpsr,
  };
}
