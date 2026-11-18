// Spedizione sì o no, pezzo per pezzo. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { asksShipping, isShippable } from "./spedizione.ts";

test("i tipi spedibili restano sempre spedibili", () => {
  assert.equal(isShippable({}, true), true);
  assert.equal(isShippable({ spedibile: false }, true), true);
  assert.equal(asksShipping(true), false);
});

test("i tipi ingombranti sono solo ritiro finché non si sceglie di spedirli", () => {
  assert.equal(isShippable({}, false), false);
  assert.equal(isShippable({ spedibile: true }, false), true);
  assert.equal(asksShipping(false), true);
});
