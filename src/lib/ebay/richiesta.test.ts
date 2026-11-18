// Richiesta per eBay costruita da un annuncio. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { richiestaPer, type ContestoRichiesta } from "./richiesta.ts";
import { onlinePrice } from "../pricing.ts";
import type { Annuncio } from "../types.ts";

function annuncio(over: Partial<Annuncio> = {}): Annuncio {
  return {
    id: "A-000001", typeId: "faro", condition: "B", spedibile: true, price: 95, titolo: "Faro anteriore", descrizione: "Ottimo",
    testoModificato: false, caratteristiche: { Marca: "Fiat" }, gpsr: { tipo: "esente" }, createdAt: "2026-01-01T10:00:00.000Z", ...over,
  };
}
const ctx = (over: Partial<ContestoRichiesta> = {}): ContestoRichiesta => ({
  quantita: 1, foto: ["/uno.jpg"], compatibilita: [], categoriaQuery: "faro anteriore", typeShippable: true, ...over,
});
const richiesta = (a: Annuncio, c: ContestoRichiesta = ctx()) => richiestaPer(a, c, (b) => onlinePrice(b) as number);

test("prezzo online con l'8%", () => {
  const r = richiesta(annuncio({ price: 95 }));
  assert.equal(r.prezzo, 102.6);
  assert.equal(r.sku, "A-000001");
  assert.equal(r.quantita, 1);
  assert.deepEqual(r.foto, ["/uno.jpg"]);
});

test("a zero pezzi la richiesta resta attiva con quantità 0", () => {
  const r = richiesta(annuncio(), ctx({ quantita: 0, foto: ["/ultimo.jpg"] }));
  assert.equal(r.quantita, 0);
  assert.equal(r.attivo, true);
  assert.deepEqual(r.foto, ["/ultimo.jpg"]);
});

test("annuncio ritirato su eBay → attivo false", () => {
  assert.equal(richiesta(annuncio({ ebay: { stato: "ritirato", daRiallineare: true } })).attivo, false);
});

test("categoria già scelta e condizione passano nella richiesta", () => {
  const r = richiesta(annuncio({ ebay: { stato: "online", daRiallineare: false, categoria: { id: "33710", nome: "Fari" } } }));
  assert.equal(r.categoriaId, "33710");
  assert.equal(r.condizione, "B");
});

test("compatibilità e categoriaQuery del contesto passano invariate", () => {
  const compatibilita = [{ marca: "Fiat", modello: "Panda", anno: 2015 }];
  const r = richiesta(annuncio(), ctx({ compatibilita, categoriaQuery: "faro fanale anteriore" }));
  assert.deepEqual(r.compatibilita, compatibilita);
  assert.equal(r.categoriaQuery, "faro fanale anteriore");
});

test("spedizione", () => {
  assert.equal(richiesta(annuncio({ spedibile: true }), ctx({ typeShippable: false })).spedizione, "voluminoso");
  assert.equal(richiesta(annuncio({ spedibile: false }), ctx({ typeShippable: false })).spedizione, "ritiro");
  assert.equal(richiesta(annuncio({ typeId: "alternatore" }), ctx({ typeShippable: true })).spedizione, "corriere");
});
