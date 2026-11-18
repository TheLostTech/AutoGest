// Dall'annuncio alla richiesta per eBay. Modulo puro: il prezzo online si passa come funzione.
import type { Annuncio, Part } from "../types";
import type { RichiestaAllinea, SpedizioneEbay } from "./contratto";

export function richiestaPer(a: Annuncio, parts: Part[], typeShippable: boolean, online: (base: number) => number): RichiestaAllinea {
  // Stessa regola di annunci.ts (quantityOf, nextToShip), rifatta qui perché il modulo resta senza import di codice
  const suoi = parts.filter((p) => p.annuncioId === a.id);
  const disponibili = suoi.filter((p) => p.status === "disponibile");
  const quantita = disponibili.length;
  // Foto dal prossimo a partire o, a zero pezzi, dall'ultimo pezzo entrato
  const p = quantita > 0
    ? [...disponibili].sort((x, y) => x.createdAt.localeCompare(y.createdAt) || x.id.localeCompare(y.id))[0]
    : [...suoi].sort((x, y) => y.createdAt.localeCompare(x.createdAt))[0];
  const spedizione: SpedizioneEbay = !a.spedibile ? "ritiro" : typeShippable ? "corriere" : "voluminoso";
  return {
    sku: a.id,
    attivo: a.ebay?.stato !== "ritirato",
    quantita,
    prezzo: online(a.price),
    titolo: a.titolo,
    descrizione: a.descrizione,
    categoriaQuery: a.titolo,
    categoriaId: a.ebay?.categoria?.id,
    condizione: a.condition,
    caratteristiche: a.caratteristiche,
    foto: p?.photos ?? [],
    compatibilita: [],
    spedizione,
    gpsr: a.gpsr,
  };
}
