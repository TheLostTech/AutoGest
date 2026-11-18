import { test } from "node:test";
import assert from "node:assert/strict";
import { aggiungiInSospeso, corpoDaRiprendere, IN_SOSPESO_MAX_MS } from "./sync-in-sospeso.ts";

const ORA = 1_800_000_000_000;
const SCHEMA = "s-v12";
const LISTE = ["vehicles", "parts", "audit"] as const;

test("il corpo ripreso ha solo schema, changes per id e counters: mai whole, mai replace, mai state", () => {
  const coda = aggiungiInSospeso(null, SCHEMA, { parts: [{ id: "P-1", x: 1 }] }, { part: 3 }, ORA, LISTE);
  // Anche se qualcuno scrive nel salvataggio campi in più, non passano
  const manomessa = { ...coda, replace: true, whole: { rules: [] }, state: { parts: [] } };
  const c = corpoDaRiprendere(JSON.parse(JSON.stringify(manomessa)), SCHEMA, ORA + 1000, LISTE);
  assert.deepEqual(c, { schema: SCHEMA, changes: { parts: [{ id: "P-1", x: 1 }] }, counters: { part: 3 } });
  assert.deepEqual(Object.keys(c!).sort(), ["changes", "counters", "schema"]);
});

test("aggiungi non conserva whole né liste sconosciute; le righe senza id si scartano", () => {
  const coda = aggiungiInSospeso(
    null,
    SCHEMA,
    { parts: [{ id: "P-1" }, { senzaId: true }, "testo"] as unknown[], rules: [{ typeId: "T" }], segreto: [{ id: "X" }] } as Record<string, unknown[]>,
    undefined,
    ORA,
    LISTE,
  );
  const c = corpoDaRiprendere(coda, SCHEMA, ORA, LISTE);
  assert.deepEqual(c, { schema: SCHEMA, changes: { parts: [{ id: "P-1" }] } });
});

test("voci più vecchie di 24 ore si scartano; la copia più recente di un record vince", () => {
  let coda = aggiungiInSospeso(null, SCHEMA, { parts: [{ id: "P-1", v: 1 }], vehicles: [{ id: "V-1" }] }, { part: 1 }, ORA, LISTE);
  coda = aggiungiInSospeso(coda, SCHEMA, { parts: [{ id: "P-1", v: 2 }] }, undefined, ORA + IN_SOSPESO_MAX_MS - 10, LISTE);
  const c = corpoDaRiprendere(coda, SCHEMA, ORA + IN_SOSPESO_MAX_MS + 1, LISTE);
  // V-1 e i contatori (salvati a ORA) sono scaduti; P-1 è stato riscritto dopo
  assert.deepEqual(c, { schema: SCHEMA, changes: { parts: [{ id: "P-1", v: 2 }] } });
  assert.equal(corpoDaRiprendere(coda, SCHEMA, ORA + 2 * IN_SOSPESO_MAX_MS, LISTE), null);
});

test("schema diverso, dati non validi o vuoti: niente da riprendere", () => {
  const coda = aggiungiInSospeso(null, SCHEMA, { parts: [{ id: "P-1" }] }, undefined, ORA, LISTE);
  assert.equal(corpoDaRiprendere(coda, "altro", ORA, LISTE), null);
  assert.equal(corpoDaRiprendere(null, SCHEMA, ORA, LISTE), null);
  assert.equal(corpoDaRiprendere("x", SCHEMA, ORA, LISTE), null);
  assert.equal(corpoDaRiprendere({ v: 1, schema: SCHEMA, voci: "x" }, SCHEMA, ORA, LISTE), null);
  assert.equal(corpoDaRiprendere(aggiungiInSospeso(null, SCHEMA, {}, undefined, ORA, LISTE), SCHEMA, ORA, LISTE), null);
});

test("contatori: solo numeri", () => {
  const coda = aggiungiInSospeso(null, SCHEMA, {}, { part: 4, cattivo: "x", annidato: { a: 1 } }, ORA, LISTE);
  assert.deepEqual(corpoDaRiprendere(coda, SCHEMA, ORA, LISTE), { schema: SCHEMA, changes: {}, counters: { part: 4 } });
});

test("una coda salvata con un altro schema viene sostituita, non unita", () => {
  const vecchia = aggiungiInSospeso(null, "vecchio", { parts: [{ id: "P-9" }] }, undefined, ORA, LISTE);
  const coda = aggiungiInSospeso(vecchia, SCHEMA, { parts: [{ id: "P-1" }] }, undefined, ORA, LISTE);
  assert.deepEqual(corpoDaRiprendere(coda, SCHEMA, ORA, LISTE), { schema: SCHEMA, changes: { parts: [{ id: "P-1" }] } });
});
