// Scadenza delle riserve e limiti degli ordini del negozio pubblico. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { archivioNegozioValido, decidiOrdine, ordiniScaduti, SCADENZA_RISERVA_MS } from "./negozio-regole.ts";

const T0 = Date.parse("2026-03-01T10:00:00.000Z");
const ordine = (id: string, over: Record<string, unknown> = {}) => ({ id, channel: "negozio", status: "in attesa di pagamento", createdAt: new Date(T0).toISOString(), ...over }) as never;

test("scade dopo 30 minuti e 1 ms, non a 29 minuti né a 30 esatti", () => {
  const o = [ordine("O-1")];
  assert.deepEqual(ordiniScaduti(o, T0 + 29 * 60_000), []);
  assert.deepEqual(ordiniScaduti(o, T0 + SCADENZA_RISERVA_MS), []);
  assert.deepEqual(ordiniScaduti(o, T0 + SCADENZA_RISERVA_MS + 1), ["O-1"]);
});

test("scadono solo gli ordini del negozio in attesa", () => {
  const o = [ordine("O-1", { status: "pagato" }), ordine("O-2", { channel: "banco" }), ordine("O-3", { channel: "marketplace" }), ordine("O-4")];
  assert.deepEqual(ordiniScaduti(o, T0 + 3_600_000), ["O-4"]);
});

const annunci = [{ id: "A-1", negozio: { stato: "online" } }, { id: "A-2", negozio: { stato: "esaurito" } }, { id: "A-3" }] as never;

test("il 21° ordine aperto è rifiutato (429), il 20° passa; gli ordini di altri canali non contano", () => {
  const venti = Array.from({ length: 19 }, (_, i) => ordine(`O-${i}`));
  assert.deepEqual(decidiOrdine({ orders: venti, annunci }, ["A-1"]), { ok: true });
  const piene = [...venti, ordine("O-19"), ordine("O-b", { channel: "banco" })];
  const r = decidiOrdine({ orders: piene, annunci }, ["A-1"]);
  assert.equal(r.ok, false);
  if (!r.ok) assert.equal(r.stato, 429);
});

test("annuncio inesistente, esaurito, non sul negozio o carrello vuoto: 400 (nessuna scrittura)", () => {
  for (const ids of [["A-9"], ["A-2"], ["A-3"], ["A-1", "A-9"], []]) {
    const r = decidiOrdine({ orders: [], annunci }, ids);
    assert.equal(r.ok, false, JSON.stringify(ids));
    if (!r.ok) assert.equal(r.stato, 400);
  }
});

test("archivio: servono le liste e i contatori ordine ed evento", () => {
  const ok = { vehicles: [], parts: [], annunci: [], orders: [], audit: [], counters: { order: 1, event: 2 } };
  assert.equal(archivioNegozioValido(ok), true);
  assert.equal(archivioNegozioValido({ ...ok, counters: { order: 1 } }), false);
  assert.equal(archivioNegozioValido({ ...ok, orders: undefined }), false);
  assert.equal(archivioNegozioValido(null), false);
});
