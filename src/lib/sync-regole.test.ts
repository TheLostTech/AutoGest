// Quando un dispositivo può mandare il proprio stato locale intero al server. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { devePubblicareStatoLocale } from "./sync-regole.ts";

const S = "schema-v1";

test("demo con stato nullo: pubblica", () => {
  assert.equal(devePubblicareStatoLocale({ state: null, schema: "", demo: true }, S), true);
});
test("demo con schema diverso: pubblica", () => {
  assert.equal(devePubblicareStatoLocale({ state: { a: 1 }, schema: "vecchio", demo: true }, S), true);
});
test("azienda non demo con stato nullo: mai", () => {
  assert.equal(devePubblicareStatoLocale({ state: null, schema: "", demo: false }, S), false);
});
test("azienda non demo con schema diverso: mai", () => {
  assert.equal(devePubblicareStatoLocale({ state: { a: 1 }, schema: "vecchio", demo: false }, S), false);
});
test("demo con lo stesso schema: non serve", () => {
  assert.equal(devePubblicareStatoLocale({ state: { a: 1 }, schema: S, demo: true }, S), false);
});
