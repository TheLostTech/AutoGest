// Passi della pratica dopo la presa in carico: radiazione con fascicolo e ricevuta, poi distruzione di targhe e documenti.
// Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { distruzioneDal, fascicoloAuto, fascicoloFor, praticaSteps } from "./pratica.ts";
import type { Vehicle } from "./types.ts";

const presa = "2026-11-18T10:00:00.000Z";
const veicolo = (extra: Partial<Vehicle> = {}) =>
  ({
    id: "V-000200",
    plate: "GA771ZK",
    vin: "ZFA31200000123456",
    verification: "verificato",
    intakeAt: presa,
    dossier: { number: "CR-2026-004900", kind: "Certificato di Rottamazione Digitale", status: "in corso" },
    conferente: { tipo: "privato", nome: "Mario Demo", cf: "DMOMRA80A01L219X" },
    documenti: ["targa-ant", "targa-post", "libretto", "proprieta", "identita"],
    visura: { at: presa, fermo: false, intestatario: "Mario Demo" },
    presaInCarico: { at: presa, by: "Giulia (accettazione)" },
    radiazione: { stato: "da richiedere" },
    ...extra,
  }) as unknown as Vehicle;

test("il provvedimento della PA serve solo con il codice C05333", () => {
  assert.ok(!fascicoloFor("C05332").some((d) => d.key === "provvedimento"));
  assert.ok(fascicoloFor("C05333").some((d) => d.key === "provvedimento"));
});

test("documenti del passo 1 e CRD del passo 3 entrano nel fascicolo da soli, l'istanza no", () => {
  const auto = fascicoloAuto(veicolo());
  assert.deepEqual([...auto].sort(), ["crd", "libretto", "proprieta"]);
  assert.ok(!auto.has("istanza"));
  assert.ok(!fascicoloAuto(veicolo({ presaInCarico: undefined })).has("crd"));
});

test("targhe e documenti si distruggono non prima di 120 giorni dal CRD", () => {
  assert.equal(distruzioneDal(veicolo())?.slice(0, 10), "2027-03-18");
  assert.equal(distruzioneDal(veicolo({ presaInCarico: undefined })), undefined);
});

test("la distruzione si apre solo dopo la ricevuta di radiazione", () => {
  assert.equal(praticaSteps(veicolo()).radiazione, "attuale");
  assert.equal(praticaSteps(veicolo()).distruzione, "dopo");
  assert.equal(praticaSteps(veicolo({ radiazione: { stato: "da integrare" } })).radiazione, "attuale");
  const radiato = veicolo({ radiazione: { stato: "completata", completataAt: presa, estremi: "123" } });
  assert.equal(praticaSteps(radiato).radiazione, "fatto");
  assert.equal(praticaSteps(radiato).distruzione, "attuale");
  const chiuso = veicolo({ ...radiato, distruzione: { at: presa, by: "Giulia", cosa: ["targa-ant"] } });
  assert.equal(praticaSteps(chiuso).distruzione, "fatto");
});
