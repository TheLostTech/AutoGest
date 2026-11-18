// Ruoli dell'azienda. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { RUOLI, ruoliAStringa, ruoliDaStringa } from "./ruoli.ts";

test("ruoliDaStringa pulisce e ordina", () => {
  assert.deepEqual(ruoliDaStringa(" accettazione,smontatore ,smontatore"), ["accettazione", "smontatore"]);
  assert.deepEqual(ruoliDaStringa("smontatore,owner,boh"), ["smontatore"]);
  assert.deepEqual(ruoliDaStringa(null), []);
  assert.deepEqual(ruoliDaStringa("vendite,accettazione"), ["accettazione", "vendite"]);
});
test("ruoliAStringa è l'inverso", () => assert.equal(ruoliAStringa(["smontatore", "accettazione"]), "accettazione,smontatore"));
test("RUOLI ha i sei ruoli", () => assert.equal(RUOLI.length, 6));
