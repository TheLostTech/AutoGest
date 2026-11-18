// Fusione dei salvataggi dei dispositivi. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { esitoPush, unisciPush, type Stored } from "./archivio-unione.ts";

const S = "schema-x";
const base = (state: Record<string, unknown>): Stored => ({ schema: S, version: 3, state });

test("nuovi record per parts in cima", () => {
  const r = unisciPush(base({ parts: [{ id: "A" }, { id: "B" }] }), { schema: S, changes: { parts: [{ id: "N" }] } });
  assert.deepEqual((r.state!.parts as { id: string }[]).map((x) => x.id), ["N", "A", "B"]);
  assert.equal(r.version, 4);
});
test("record esistente sostituito per id", () => {
  const r = unisciPush(base({ parts: [{ id: "A", n: 1 }] }), { schema: S, changes: { parts: [{ id: "A", n: 2 }] } });
  assert.deepEqual(r.state!.parts, [{ id: "A", n: 2 }]);
});
test("audit in fondo, chiave id+ora", () => {
  const cur = [{ id: "E-1", at: "t1" }];
  const r = unisciPush(base({ audit: cur }), { schema: S, changes: { audit: [{ id: "E-1", at: "t2" }, { id: "E-1", at: "t1" }] } });
  assert.deepEqual(r.state!.audit, [{ id: "E-1", at: "t1" }, { id: "E-1", at: "t2" }]);
});
test("whole sostituito", () => {
  const r = unisciPush(base({ rules: [1] }), { schema: S, whole: { rules: [2, 3] } });
  assert.deepEqual(r.state!.rules, [2, 3]);
});
test("contatori al massimo", () => {
  const r = unisciPush(base({ counters: { order: 5, docs: { P: 1, FT: 9 } } }), { schema: S, counters: { order: 3, docs: { P: 4, FT: 2 } } });
  assert.deepEqual(r.state!.counters, { order: 5, docs: { P: 4, FT: 9 } });
});
test("replace sostituisce tutto", () => {
  const r = unisciPush(base({ parts: [{ id: "A" }] }), { schema: S, replace: true, state: { parts: [] } });
  assert.deepEqual(r.state, { parts: [] });
  assert.equal(r.version, 4);
});
test("schema diverso sostituisce tutto", () => {
  const r = unisciPush(base({ parts: [{ id: "A" }] }), { schema: "nuovo", state: { x: 1 } });
  assert.equal(r.schema, "nuovo");
  assert.deepEqual(r.state, { x: 1 });
});
test("nessuno stato salvato: prende quello inviato", () => {
  const r = unisciPush({ schema: "", version: 0, state: null }, { schema: S, state: { y: 1 } });
  assert.deepEqual(r, { schema: S, version: 1, state: { y: 1 } });
});
test("due unisciPush in serie: entrambi presenti", () => {
  let s = base({ orders: [], parts: [{ id: "P1", prezzo: 1 }] });
  s = unisciPush(s, { schema: S, changes: { orders: [{ id: "O-1" }] } });
  s = unisciPush(s, { schema: S, changes: { parts: [{ id: "P1", prezzo: 2 }] } });
  assert.deepEqual(s.state!.orders, [{ id: "O-1" }]);
  assert.deepEqual(s.state!.parts, [{ id: "P1", prezzo: 2 }]);
  assert.equal(s.version, 5);
});

const nonDemo = { demo: false, responsabile: true };
test("esitoPush: non demo, mai sostituzione implicita (409)", () => {
  assert.equal(esitoPush(base({}), { schema: "x", state: {} }, { demo: false, responsabile: false }), 409);
  assert.equal(esitoPush(base({}), { schema: S, replace: true, state: {} }, nonDemo), 409);
  assert.equal(esitoPush({ schema: "", version: 0, state: null }, { schema: S, state: {} }, nonDemo), 409);
});
test("esitoPush: demo senza responsabile (403)", () => {
  assert.equal(esitoPush(base({}), { schema: "x", state: {} }, { demo: true, responsabile: false }), 403);
  assert.equal(esitoPush(base({}), { schema: S, replace: true }, { demo: true, responsabile: false }), 403);
});
test("esitoPush: demo responsabile sostituisce", () => {
  assert.equal(esitoPush(base({}), { schema: S, replace: true, state: {} }, { demo: true, responsabile: true }), "sostituisci");
  assert.equal(esitoPush({ schema: "", version: 0, state: null }, { schema: S, state: {} }, { demo: true, responsabile: true }), "sostituisci");
});
test("esitoPush: modifiche normali si uniscono", () => {
  for (const ctx of [nonDemo, { demo: true, responsabile: false }]) assert.equal(esitoPush(base({}), { schema: S, changes: {} }, ctx), "unisci");
});
