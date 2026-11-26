import { test } from "node:test";
import assert from "node:assert/strict";
import { ABBONAMENTO_NUOVO, normalizzaAbbonamento, type Abbonamento } from "./abbonamento.ts";
import { avvisoDaMandare, segretoValido } from "./avvisi-prova.ts";

const GIORNO = 86_400_000;
const ORA = Date.UTC(2026, 10, 26, 8);
const prova = (giorni: number, o: Partial<Abbonamento> = {}): Abbonamento =>
  ({ ...ABBONAMENTO_NUOVO(true, ORA), fineProva: ORA + giorni * GIORNO, ...o });

test("avvisoDaMandare: a 4 giorni dalla fine niente", () => {
  assert.equal(avvisoDaMandare(prova(4), ORA), null);
});

test("avvisoDaMandare: a 3 giorni, e anche a meno, scadenza", () => {
  assert.equal(avvisoDaMandare(prova(3), ORA), "scadenza");
  assert.equal(avvisoDaMandare(prova(1), ORA), "scadenza");
  assert.equal(avvisoDaMandare(prova(0.2), ORA), "scadenza");
});

test("avvisoDaMandare: scadenza già mandata, niente", () => {
  assert.equal(avvisoDaMandare(prova(2, { avvisi: { scadenza: "2026-11-25T08:00:00.000Z" } }), ORA), null);
});

test("avvisoDaMandare: prova finita dà finita, una volta sola", () => {
  assert.equal(avvisoDaMandare(prova(-1), ORA), "finita");
  assert.equal(avvisoDaMandare(prova(0), ORA), "finita");
  assert.equal(avvisoDaMandare(prova(-1, { avvisi: { scadenza: "x", finita: "y" } }), ORA), null);
  assert.equal(avvisoDaMandare(prova(-1, { avvisi: { scadenza: "x" } }), ORA), "finita");
});

test("avvisoDaMandare: pagato, prova non partita o scaduto: niente", () => {
  assert.equal(avvisoDaMandare(prova(2, { stato: "attivo" }), ORA), null);
  assert.equal(avvisoDaMandare(prova(-1, { stato: "attivo" }), ORA), null);
  assert.equal(avvisoDaMandare(prova(-1, { stato: "scaduto" }), ORA), null);
  assert.equal(avvisoDaMandare(prova(2, { fineProva: null }), ORA), null);
});

test("avvisoDaMandare: conta lo spostamento della prova con le chiavi di prova", () => {
  assert.equal(avvisoDaMandare(prova(10, { spostamentoProva: 8 * GIORNO }), ORA), "scadenza");
  assert.equal(avvisoDaMandare(prova(10, { prova: false, spostamentoProva: 8 * GIORNO }), ORA), null);
});

test("normalizzaAbbonamento: avvisi assente o non valido diventa {}", () => {
  const vecchio = { ...ABBONAMENTO_NUOVO(true, 0) } as Record<string, unknown>;
  delete vecchio.avvisi;
  assert.deepEqual(normalizzaAbbonamento(vecchio as Abbonamento).avvisi, {});
  assert.deepEqual(normalizzaAbbonamento({ ...ABBONAMENTO_NUOVO(true, 0), avvisi: "boh" } as unknown as Abbonamento).avvisi, {});
  assert.deepEqual(normalizzaAbbonamento({ ...ABBONAMENTO_NUOVO(true, 0), avvisi: { scadenza: "a", finita: 3 } } as unknown as Abbonamento).avvisi, { scadenza: "a" });
});

test("segretoValido: serve il segreto giusto, mai senza", () => {
  assert.equal(segretoValido("Bearer abcdefghijklmnop", "abcdefghijklmnop"), true);
  assert.equal(segretoValido("Bearer sbagliatosbagliato", "abcdefghijklmnop"), false);
  assert.equal(segretoValido("abcdefghijklmnop", "abcdefghijklmnop"), false);
  assert.equal(segretoValido(null, "abcdefghijklmnop"), false);
  assert.equal(segretoValido("Bearer ", ""), false);
  assert.equal(segretoValido("Bearer x", undefined), false);
  assert.equal(segretoValido("Bearer corto", "corto"), false); // segreto troppo corto: non configurato bene
});
