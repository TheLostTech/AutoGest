import { test } from "node:test";
import assert from "node:assert/strict";
import { moduliUsati } from "./moduli-usati.ts";

// Veicolo come lo salva l'ingresso (Magazzino): la pratica c'è sempre ma è vuota
const veicolo = (o: Record<string, unknown> = {}) => ({
  id: "V-000001", plate: "AB123CD", dossier: { number: "", kind: "Certificato di Rottamazione Digitale", status: "da registrare" }, ...o,
});
// Carico d'ingresso creato da solo all'ingresso del veicolo (anche senza il modulo Ambiente)
const caricoIngresso = { id: "M-000001", kind: "carico", causale: "*T", origin: "V-000001", eer: "16 01 04*", kg: 900 };

test("moduliUsati: archivio assente, vuoto o di solo magazzino dà solo il magazzino", () => {
  assert.deepEqual(moduliUsati(null), ["magazzino"]);
  assert.deepEqual(moduliUsati({}), ["magazzino"]);
  assert.deepEqual(
    moduliUsati({ vehicles: [veicolo({ bonifica: { semplice: true, items: [] } })], wasteMoves: [caricoIngresso], orders: [{ id: "O-1", channel: "negozio" }, { id: "O-2", channel: "marketplace" }], docs: [{ id: "DC-1", type: "documento commerciale", orderId: "O-1" }], firs: [] }),
    ["magazzino"],
  );
});

test("moduliUsati: accettazione con almeno una pratica avviata", () => {
  assert.deepEqual(moduliUsati({ vehicles: [veicolo({ documenti: ["libretto"] })] }), ["magazzino", "accettazione"]);
  assert.deepEqual(moduliUsati({ vehicles: [veicolo(), veicolo({ visura: { at: "x", fermo: false, intestatario: "R" } })] }), ["magazzino", "accettazione"]);
  assert.deepEqual(moduliUsati({ vehicles: [veicolo({ visuraRichiesta: { id: "1", at: "x", stato: "in corso", modo: "x" } })] }), ["magazzino", "accettazione"]);
  assert.deepEqual(moduliUsati({ vehicles: [veicolo({ radiazione: { stato: "da richiedere" } })] }), ["magazzino", "accettazione"]);
  assert.deepEqual(moduliUsati({ vehicles: [veicolo({ dossier: { number: "", kind: "CRD", status: "in corso" } })] }), ["magazzino", "accettazione"]);
  assert.deepEqual(moduliUsati({ vehicles: [veicolo({ conferente: { tipo: "privato", nome: "R", documento: "CA123" } })] }), ["magazzino", "accettazione"]);
  // Documenti vuoti: non è una pratica
  assert.deepEqual(moduliUsati({ vehicles: [veicolo({ documenti: [] })] }), ["magazzino"]);
});

test("moduliUsati: ambiente con almeno un formulario o una registrazione del registro rifiuti", () => {
  assert.deepEqual(moduliUsati({ firs: [{ id: "F-1" }] }), ["magazzino", "ambiente"]);
  assert.deepEqual(moduliUsati({ wasteMoves: [caricoIngresso, { id: "M-2", kind: "scarico", causale: "I", caricoRif: "M-000001" }] }), ["magazzino", "ambiente"]);
  assert.deepEqual(moduliUsati({ wasteMoves: [{ id: "M-3", kind: "carico", causale: "NP" }] }), ["magazzino", "ambiente"]);
  // Bonifica con i materiali (non quella "semplice" del solo Magazzino)
  assert.deepEqual(moduliUsati({ vehicles: [veicolo({ bonifica: { items: [{ key: "olio", qty: 4, done: true }] } })] }), ["magazzino", "ambiente"]);
});

test("moduliUsati: vendite con almeno una vendita al banco o un preventivo", () => {
  assert.deepEqual(moduliUsati({ orders: [{ id: "O-1", channel: "banco" }] }), ["magazzino", "vendite"]);
  assert.deepEqual(moduliUsati({ docs: [{ id: "PR-1", type: "preventivo" }] }), ["magazzino", "vendite"]);
});

test("moduliUsati: tutti insieme, nell'ordine dei moduli", () => {
  assert.deepEqual(
    moduliUsati({ docs: [{ type: "preventivo" }], firs: [{ id: "F-1" }], vehicles: [veicolo({ documenti: ["libretto"] })] }),
    ["magazzino", "accettazione", "ambiente", "vendite"],
  );
});

test("moduliUsati: campi mancanti o non validi non fanno errori e non contano", () => {
  assert.deepEqual(moduliUsati({ vehicles: "x", wasteMoves: 3, firs: null, orders: {}, docs: [null, 1, "preventivo"] }), ["magazzino"]);
  assert.deepEqual(moduliUsati({ vehicles: [null, 7, { dossier: null }, { documenti: "libretto" }], wasteMoves: [null, "M"], orders: [null, { channel: 1 }] }), ["magazzino"]);
});
