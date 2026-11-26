// Scheda della registrazione con i consensi: versioni dei testi, ora e indirizzo. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { schedaRegistrazione, VERSIONE_CONDIZIONI, VERSIONE_PRIVACY } from "./consensi.ts";
import type { DatiRegistrazione } from "./accesso/registrazione.ts";

const dati: DatiRegistrazione = {
  azienda: "Rossi Autodemolizioni",
  nome: "Mario Rossi",
  email: "mario@rossi.it",
  password: "unapassword",
  telefono: "+39 333 1234567",
  condizioni: true,
  clausole: true,
  commerciale: false,
};
const ora = Date.UTC(2026, 10, 26, 9, 30);
const iso = "2026-11-26T09:30:00.000Z";

test("versioni dei testi come date", () => {
  assert.equal(VERSIONE_CONDIZIONI, "2026-11-27");
  assert.equal(VERSIONE_PRIVACY, "2026-11-26");
});

test("schedaRegistrazione: senza consenso commerciale → commerciale null; versioni, ora e IP riportati", () => {
  assert.deepEqual(schedaRegistrazione(dati, "198.51.100.7", ora), {
    titolare: "Mario Rossi",
    email: "mario@rossi.it",
    telefono: "+39 333 1234567",
    azienda: "Rossi Autodemolizioni",
    registrata: iso,
    confermata: null,
    condizioni: { versione: VERSIONE_CONDIZIONI, ora: iso, ip: "198.51.100.7" },
    clausole: { versione: VERSIONE_CONDIZIONI, ora: iso, ip: "198.51.100.7" },
    privacy: { versione: VERSIONE_PRIVACY, ora: iso, ip: "198.51.100.7" },
    commerciale: null,
  });
});

test("schedaRegistrazione: con consenso commerciale, senza telefono e senza IP", () => {
  const s = schedaRegistrazione({ ...dati, telefono: null, commerciale: true }, null, ora);
  assert.equal(s.telefono, null);
  assert.deepEqual(s.commerciale, { versione: VERSIONE_PRIVACY, ora: iso, ip: null });
  assert.deepEqual(s.condizioni, { versione: VERSIONE_CONDIZIONI, ora: iso, ip: null });
});

test("schedaRegistrazione: la password non finisce nella scheda", () => {
  assert.equal(JSON.stringify(schedaRegistrazione(dati, null, ora)).includes("unapassword"), false);
});
