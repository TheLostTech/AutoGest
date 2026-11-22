// Listino dei moduli: importi e formato dei prezzi sulla pagina di presentazione. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { LISTINO, euro, risparmioAnnuale, totale } from "./listino.ts";
import { ORDINE_MODULI } from "./moduli.ts";

test("ogni modulo ha un prezzo mensile e annuale", () => {
  for (const m of ORDINE_MODULI) {
    assert.ok(LISTINO[m].mese > 0 && LISTINO[m].anno > 0, m);
  }
});

test("i prezzi finiscono in 9, mai cifre tonde", () => {
  for (const m of ORDINE_MODULI) {
    assert.equal(Math.floor(LISTINO[m].mese / 10) % 10, 9, `${m} mensile`);
    assert.equal((LISTINO[m].anno / 100) % 10, 9, `${m} annuale`);
  }
});

test("l'annuale costa meno di dodici mensili", () => {
  for (const m of ORDINE_MODULI) assert.ok(risparmioAnnuale(m) > 0, m);
  assert.equal(risparmioAnnuale("magazzino"), 39980);
});

test("totali e formato in euro", () => {
  assert.equal(euro(totale(["magazzino"], "mese")), "299,90\u00a0€");
  assert.equal(euro(totale(["magazzino"], "anno")), "3.199\u00a0€");
  assert.equal(euro(totale(ORDINE_MODULI, "mese")), "419,60\u00a0€");
  assert.equal(euro(totale(ORDINE_MODULI, "anno")), "4.496\u00a0€");
});
