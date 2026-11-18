// Riallineamento eBay: scelta e applicazione dell'esito. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { applyEsito, nextToSync } from "./sync-puro.ts";
import type { Annuncio, AnnuncioEbay } from "../types.ts";

const ann = (id: string, ebay?: Partial<AnnuncioEbay>): Annuncio =>
  ({ id, typeId: "faro", condition: "B", spedibile: true, price: 100, titolo: "t", descrizione: "d", testoModificato: false, caratteristiche: {}, gpsr: { tipo: "esente" }, createdAt: "2026-01-01", ebay: ebay ? { stato: "online", daRiallineare: false, ...ebay } : undefined }) as Annuncio;

test("sceglie prima gli annunci senza errore", () => {
  const a = ann("A-1", { daRiallineare: true, stato: "errore", errore: "no" });
  const b = ann("A-2", { daRiallineare: true });
  assert.equal(nextToSync([a, b])?.id, "A-2");
  assert.equal(nextToSync([a])?.id, "A-1");
});

test("ignora annunci senza eBay, già allineati o mai pensati per eBay; il ritirato si manda una volta", () => {
  assert.equal(nextToSync([ann("A-1"), ann("A-2", { daRiallineare: false }), ann("A-3", { daRiallineare: true, stato: "non pubblicato" })]), undefined);
  assert.equal(nextToSync([ann("A-4", { daRiallineare: true, stato: "ritirato" })])?.id, "A-4");
});

test("dopo un errore l'annuncio resta da riallineare", () => {
  const e = applyEsito(ann("A-1", { daRiallineare: true, stato: "in pubblicazione" }), { stato: "errore", avvisi: [], errore: "prezzo rifiutato" }, { quantita: 1, prezzo: 98.13 }, "T");
  assert.equal(e.stato, "errore");
  assert.equal(e.daRiallineare, true);
  assert.equal(e.errore, "prezzo rifiutato");
});

test("un ritiro fallito resta un ritiro", () => {
  const e = applyEsito(ann("A-1", { daRiallineare: true, stato: "ritirato" }), { stato: "errore", avvisi: [], errore: "x" }, { quantita: 1, prezzo: 1 }, "T");
  assert.equal(e.stato, "ritirato");
  assert.equal(e.daRiallineare, true);
});

test("esito buono azzera errore e segno, e salva quantità e prezzo inviati", () => {
  const e = applyEsito(
    ann("A-1", { daRiallineare: true, stato: "errore", errore: "vecchio", listingId: "L0" }),
    { stato: "online", listingId: "SIM-A-1", url: "/ebay-simulato/A-1", categoria: { id: "1", nome: "Fari" }, avvisi: [] },
    { quantita: 2, prezzo: 102.6 },
    "2026-02-01T00:00:00Z",
  );
  assert.equal(e.stato, "online");
  assert.equal(e.daRiallineare, false);
  assert.equal(e.errore, undefined);
  assert.equal(e.quantitaInviata, 2);
  assert.equal(e.prezzoInviato, 102.6);
  assert.equal(e.listingId, "SIM-A-1");
  assert.equal(e.aggiornatoAt, "2026-02-01T00:00:00Z");
});

const esitoOnline = { stato: "online" as const, listingId: "L1", url: "/u", avvisi: [] };

test("una risposta vecchia non cancella un ritiro fatto nel frattempo", () => {
  const e = applyEsito(ann("A-1", { daRiallineare: true, stato: "ritirato", listingId: "L1" }), esitoOnline, { quantita: 1, prezzo: 1, attivo: true }, "T");
  assert.equal(e.stato, "ritirato");
  assert.equal(e.daRiallineare, true);
  assert.equal(e.listingId, "L1");
});

test("una risposta di ritiro non cancella una ripubblicazione fatta nel frattempo", () => {
  const e = applyEsito(ann("A-1", { daRiallineare: true, stato: "in pubblicazione", listingId: "L1" }), { stato: "ritirato", avvisi: [] }, { quantita: 1, prezzo: 1, attivo: false }, "T");
  assert.equal(e.stato, "in pubblicazione");
  assert.equal(e.daRiallineare, true);
});

test("ritiro confermato senza cambi: ritirato e allineato", () => {
  const e = applyEsito(ann("A-1", { daRiallineare: true, stato: "ritirato", listingId: "L1" }), { stato: "ritirato", avvisi: [] }, { quantita: 1, prezzo: 1, attivo: false }, "T");
  assert.equal(e.stato, "ritirato");
  assert.equal(e.daRiallineare, false);
});

test("un errore su un annuncio già online ne tiene lo stato e salva l'errore", () => {
  const e = applyEsito(ann("A-1", { daRiallineare: true, stato: "online", listingId: "L1" }), { stato: "errore", avvisi: [], errore: "eBay non risponde" }, { quantita: 1, prezzo: 1, attivo: true }, "T");
  assert.equal(e.stato, "online");
  assert.equal(e.errore, "eBay non risponde");
  assert.equal(e.daRiallineare, true);
});

test("se l'annuncio è cambiato durante la richiesta resta da riallineare", () => {
  const e = applyEsito(ann("A-1", { daRiallineare: true, stato: "online", listingId: "L1" }), esitoOnline, { quantita: 1, prezzo: 1, attivo: true }, "T", true);
  assert.equal(e.daRiallineare, true);
  assert.equal(e.stato, "online");
});
