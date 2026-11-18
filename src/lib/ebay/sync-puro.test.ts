// Riallineamento eBay: scelta e applicazione dell'esito. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { applyEsito, daPerVendite, esitoDaStato, nextToSync } from "./sync-puro.ts";
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

test("quantità o prezzo diversi da quelli mandati: da riallineare anche senza il segno", () => {
  const attuale = () => ({ quantita: 2, prezzo: 108 });
  const allineato = ann("A-1", { quantitaInviata: 2, prezzoInviato: 108 });
  const qDiversa = ann("A-2", { quantitaInviata: 3, prezzoInviato: 108 });
  const pDiverso = ann("A-3", { quantitaInviata: 2, prezzoInviato: 100 });
  assert.equal(nextToSync([allineato], attuale), undefined);
  assert.equal(nextToSync([allineato, qDiversa], attuale)?.id, "A-2");
  assert.equal(nextToSync([allineato, pDiverso], attuale)?.id, "A-3");
  // Senza il confronto vale solo il segno, come prima
  assert.equal(nextToSync([qDiversa]), undefined);
});

test("la differenza non conta per annunci ritirati o mai pensati per eBay; mai mandato = da mandare", () => {
  const attuale = () => ({ quantita: 1, prezzo: 108 });
  assert.equal(nextToSync([ann("A-1", { stato: "ritirato", quantitaInviata: 5, prezzoInviato: 1 })], attuale), undefined);
  assert.equal(nextToSync([ann("A-2", { stato: "non pubblicato" })], attuale), undefined);
  assert.equal(nextToSync([ann("A-3", { stato: "in pubblicazione" })], attuale)?.id, "A-3");
});

test("risposta del ponte: 4xx errore salvato, 5xx salta l'annuncio, niente rete ferma il giro", () => {
  const e413 = esitoDaStato(413);
  assert.ok(typeof e413 === "object" && e413.stato === "errore" && /troppo grande/.test(e413.errore ?? ""));
  const e400 = esitoDaStato(400);
  assert.ok(typeof e400 === "object" && e400.stato === "errore");
  const e403 = esitoDaStato(403);
  assert.ok(typeof e403 === "object" && e403.stato === "errore" && /403/.test(e403.errore ?? ""));
  assert.equal(esitoDaStato(500), "salta");
  assert.equal(esitoDaStato(502), "salta");
  assert.equal(esitoDaStato(0), "fermati");
});

test("controllo vendite: dall'ultimo controllo meno un'ora; al primo, 7 giorni", () => {
  const ora = Date.parse("2026-11-18T12:00:00.000Z");
  assert.equal(daPerVendite("2026-11-18T11:55:00.000Z", ora), "2026-11-18T10:55:00.000Z");
  assert.equal(daPerVendite(null, ora), "2026-11-11T12:00:00.000Z");
  assert.equal(daPerVendite("rovinato", ora), "2026-11-11T12:00:00.000Z");
});

test("categoria rifiutata: si dimentica quella di eBay, resta quella dell'operatore", () => {
  const rifiuto = { stato: "errore" as const, avvisi: [], errore: "eBay non accetta la categoria.", categoriaRifiutata: true };
  const daEbay = applyEsito(ann("A-1", { daRiallineare: true, categoria: { id: "1", nome: "Fari" } }), rifiuto, { quantita: 1, prezzo: 1 }, "T");
  assert.equal(daEbay.categoria, undefined);
  const manuale = applyEsito(ann("A-1", { daRiallineare: true, categoria: { id: "2", manuale: true } }), rifiuto, { quantita: 1, prezzo: 1 }, "T");
  assert.deepEqual(manuale.categoria, { id: "2", manuale: true });
  // Un altro errore non tocca la categoria
  const altro = applyEsito(ann("A-1", { daRiallineare: true, categoria: { id: "1", nome: "Fari" } }), { stato: "errore", avvisi: [], errore: "x" }, { quantita: 1, prezzo: 1 }, "T");
  assert.equal(altro.categoria?.id, "1");
});

test("esito buono: la categoria dell'operatore resta sua e prende il nome da eBay", () => {
  const e = applyEsito(ann("A-1", { daRiallineare: true, categoria: { id: "2", manuale: true } }), { ...esitoOnline, categoria: { id: "2", nome: "Fanali" } }, { quantita: 1, prezzo: 1 }, "T");
  assert.deepEqual(e.categoria, { id: "2", nome: "Fanali", manuale: true });
  const senza = applyEsito(ann("A-1", { daRiallineare: true }), { ...esitoOnline, categoria: { id: "3", nome: "Fari" } }, { quantita: 1, prezzo: 1 }, "T");
  assert.deepEqual(senza.categoria, { id: "3", nome: "Fari" });
});

test("se l'annuncio è cambiato durante la richiesta resta da riallineare", () => {
  const e = applyEsito(ann("A-1", { daRiallineare: true, stato: "online", listingId: "L1" }), esitoOnline, { quantita: 1, prezzo: 1, attivo: true }, "T", true);
  assert.equal(e.daRiallineare, true);
  assert.equal(e.stato, "online");
});
