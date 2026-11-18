// Stato di un'azienda nuova. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { statoVuoto } from "./stato-iniziale.ts";

const base = { listini: [{ id: "L1" }], warehouses: [{ id: "M1" }] };

test("liste condivise vuote", () => {
  const s = statoVuoto(base);
  for (const k of ["parts", "vehicles", "annunci", "orders", "audit", "docs", "firs", "wasteMoves", "inventory", "rules", "soggetti"]) {
    assert.deepEqual(s[k], [], k);
  }
});
test("listini e magazzini passati", () => {
  const s = statoVuoto(base);
  assert.deepEqual(s.listini, base.listini);
  assert.deepEqual(s.warehouses, base.warehouses);
});
test("contatori a zero", () => {
  const c = statoVuoto(base).counters as Record<string, unknown>;
  assert.equal(c.order, 0);
  assert.equal(c.annuncio, 0);
  assert.equal(c.event, 0);
  assert.deepEqual(c.docs, { P: 0, DC: 0, FT: 0, NC: 0 });
});
