// Id dell'azienda usato come nome di cartella. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { idAziendaValido } from "./id-azienda.ts";

test("id validi", () => {
  assert.equal(idAziendaValido("az_1-B"), true);
  assert.equal(idAziendaValido("a".repeat(64)), true);
});
test("id non validi", () => {
  for (const x of ["", "../x", "a/b", "a.b", "a".repeat(65), "a b", "a\\b"]) assert.equal(idAziendaValido(x), false, JSON.stringify(x));
});
