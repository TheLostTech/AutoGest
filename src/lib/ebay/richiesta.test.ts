// Richiesta per eBay costruita da un annuncio. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { richiestaPer } from "./richiesta.ts";
import { onlinePrice } from "../pricing.ts";
import type { Annuncio, Part } from "../types.ts";

let n = 0;
function part(over: Partial<Part> = {}): Part {
  n += 1;
  return {
    id: `R-${String(n).padStart(6, "0")}`, vehicleId: "V-1", typeId: "faro", description: "Faro", condition: "B",
    status: "disponibile", oem: "50510123A", oemVerified: true, photos: [`/f/${n}.jpg`], labelPrints: 0, price: 90,
    annuncioId: "A-000001", createdAt: `2026-01-0${(n % 9) + 1}T10:00:00.000Z`, createdBy: "t", ...over,
  };
}
function annuncio(over: Partial<Annuncio> = {}): Annuncio {
  return {
    id: "A-000001", typeId: "faro", condition: "B", spedibile: true, price: 95, titolo: "Faro anteriore", descrizione: "Ottimo",
    testoModificato: false, caratteristiche: { Marca: "Fiat" }, gpsr: { tipo: "esente" }, createdAt: "2026-01-01T10:00:00.000Z", ...over,
  };
}
const richiesta = (a: Annuncio, parts: Part[], shippable = true) =>
  richiestaPer(a, parts, shippable, (b) => onlinePrice(b) as number);

test("prezzo online con l'8%", () => {
  const p = part({ photos: ["/uno.jpg"] });
  const r = richiesta(annuncio({ price: 95 }), [p]);
  assert.equal(r.prezzo, 102.6);
  assert.equal(r.sku, "A-000001");
  assert.equal(r.quantita, 1);
  assert.deepEqual(r.foto, ["/uno.jpg"]);
});

test("a zero pezzi la richiesta resta attiva con quantità 0", () => {
  const nuovo = part({ status: "venduto", photos: ["/ultimo.jpg"], createdAt: "2026-03-01T10:00:00.000Z" });
  const vecchio = part({ status: "venduto", photos: ["/vecchio.jpg"], createdAt: "2026-02-01T10:00:00.000Z" });
  const r = richiesta(annuncio(), [vecchio, nuovo]);
  assert.equal(r.quantita, 0);
  assert.equal(r.attivo, true);
  assert.deepEqual(r.foto, ["/ultimo.jpg"]);
});

test("annuncio ritirato su eBay → attivo false", () => {
  const a = annuncio({ ebay: { stato: "ritirato", daRiallineare: true } });
  assert.equal(richiesta(a, [part()]).attivo, false);
});

test("categoria già scelta e condizione passano nella richiesta", () => {
  const a = annuncio({ ebay: { stato: "online", daRiallineare: false, categoria: { id: "33710", nome: "Fari" } } });
  const r = richiesta(a, [part()]);
  assert.equal(r.categoriaId, "33710");
  assert.equal(r.condizione, "B");
});

test("spedizione", () => {
  assert.equal(richiesta(annuncio({ spedibile: true }), [part()], false).spedizione, "voluminoso");
  assert.equal(richiesta(annuncio({ spedibile: false }), [part()], false).spedizione, "ritiro");
  assert.equal(richiesta(annuncio({ typeId: "alternatore" }), [part({ typeId: "alternatore" })], true).spedizione, "corriere");
});
