import { test } from "node:test";
import assert from "node:assert/strict";
import { INVITO_MS, formatoCodice, invitoValido } from "./inviti-regole.ts";

test("formatoCodice normalizza maiuscole, spazi e trattini", () => {
  assert.equal(formatoCodice("al7k-2m9q-x4tp"), "AL7K-2M9Q-X4TP");
  assert.equal(formatoCodice("al7k 2m9q x4tp"), "AL7K-2M9Q-X4TP");
  assert.equal(formatoCodice("  AL7K2M9QX4TP "), "AL7K-2M9Q-X4TP");
});

test("formatoCodice rifiuta lunghezza o caratteri sbagliati", () => {
  assert.equal(formatoCodice("AL7K-2M9Q-X4T"), null);
  assert.equal(formatoCodice("AL7K-2M9Q-X4TPP"), null);
  assert.equal(formatoCodice("AL7K-2M9Q-X4T0"), null); // 0 fuori alfabeto
  assert.equal(formatoCodice("AL7K-2M9Q-X4TI"), null); // I fuori alfabeto
  assert.equal(formatoCodice(""), null);
});

test("invitoValido", () => {
  const ora = 1_000_000;
  assert.equal(invitoValido({ scade: ora + 86_400_000 }, ora), true);
  assert.equal(invitoValido({ scade: ora + 1, usato: null }, ora), true);
  assert.equal(invitoValido({ scade: ora - 1 }, ora), false);
  assert.equal(invitoValido({ scade: ora }, ora), false);
  assert.equal(invitoValido({ scade: ora + 1000, usato: ora - 5 }, ora), false);
  assert.equal(invitoValido(null, ora), false);
  assert.equal(INVITO_MS, 30 * 86_400_000);
});
