// Prezzo online con la commissione di gestione. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { ONLINE_FEE_PCT, onlinePrice } from "./pricing.ts";

test("la commissione online è dell'8%", () => {
  assert.equal(ONLINE_FEE_PCT, 8);
});

test("online il prezzo sale dell'8%, arrotondato al centesimo", () => {
  assert.equal(onlinePrice(100), 108);
  assert.equal(onlinePrice(35), 37.8);
  assert.equal(onlinePrice(15), 16.2);
  assert.equal(onlinePrice(149), 160.92);
});

test("senza prezzo non c'è prezzo online", () => {
  assert.equal(onlinePrice(undefined), undefined);
});
