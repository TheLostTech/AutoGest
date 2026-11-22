// Dati per il registro rifiuti senza il modulo Accettazione. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { bonificaRegistrabile, datiRegistroErrori, statoDatiRegistro } from "./dati-registro.ts";
import type { Vehicle, WasteMove } from "./types.ts";

const ok = { nome: "Mario Rossi", cf: "RSSMRA70A01H501U", numero: "CR-2026-000123", data: "2026-11-10" };
const oggi = new Date("2026-11-19T12:00:00");

test("datiRegistroErrori: dati completi = nessun errore", () => {
  assert.deepEqual(datiRegistroErrori(ok, oggi), []);
});

test("datiRegistroErrori: codice fiscale con spazi e minuscole, partita IVA con IT", () => {
  assert.deepEqual(datiRegistroErrori({ ...ok, cf: "rss mra 70a01 h501u" }, oggi), []);
  assert.deepEqual(datiRegistroErrori({ ...ok, cf: "IT01234567890" }, oggi), []);
  assert.deepEqual(datiRegistroErrori({ ...ok, cf: "01234567890" }, oggi), []);
});

test("bonificaRegistrabile: si registra se manca o se era segnata senza Ambiente", () => {
  assert.equal(bonificaRegistrabile(undefined), true);
  assert.equal(bonificaRegistrabile({ at: "", by: "", items: [], residualKg: 0, semplice: true }), true);
  assert.equal(bonificaRegistrabile({ at: "", by: "", items: [], residualKg: 900 }), false);
});

test("statoDatiRegistro: completo solo con il carico numerato", () => {
  const carico = (p: Partial<WasteMove>) => ({ id: "M-1", at: "", kind: "carico", eer: "16 01 04*", kg: 900, origin: "V-1", note: "", rentri: "da trasmettere", causale: "*T", ...p }) as WasteMove;
  const v = { id: "V-1", conferente: { tipo: "privato", nome: "A", cf: "X" }, dossier: { number: "CR-1" }, presaInCarico: { at: "", by: "" } } as unknown as Vehicle;
  assert.equal(statoDatiRegistro(v, [carico({ numero: 7 })]), "completo");
  assert.equal(statoDatiRegistro(v, [carico({ pesoPesa: false })]), "manca-pesata");
  assert.equal(statoDatiRegistro({ ...v, conferente: undefined }, [carico({})]), "da-compilare");
  assert.equal(statoDatiRegistro(v, []), "da-compilare");
});

test("datiRegistroErrori: ogni campo mancante o sbagliato ha il suo messaggio", () => {
  assert.deepEqual(datiRegistroErrori({ ...ok, nome: "  " }, oggi), ["Scrivi chi ha consegnato il veicolo"]);
  assert.deepEqual(datiRegistroErrori({ ...ok, cf: "ABC" }, oggi), ["Codice fiscale (16 caratteri) o partita IVA (11 cifre) non valido"]);
  assert.deepEqual(datiRegistroErrori({ ...ok, numero: "" }, oggi), ["Scrivi il numero del certificato di rottamazione"]);
  assert.deepEqual(datiRegistroErrori({ ...ok, data: "" }, oggi), ["Data del certificato non valida"]);
  assert.deepEqual(datiRegistroErrori({ ...ok, data: "2026-11-25" }, oggi), ["Data del certificato non valida"]);
});
