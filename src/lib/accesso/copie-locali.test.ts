import { test } from "node:test";
import assert from "node:assert/strict";
import { chiaviDaTogliere } from "./copie-locali.ts";

const S = "gestionale-demolizione-demo-v12";

test("ingresso nell'azienda b: via le copie delle altre aziende e degli schemi vecchi, restano le code in sospeso", () => {
  const chiavi = [
    `${S}:b`,
    `${S}:b:in-sospeso`,
    `${S}:a`,
    `${S}:a:in-sospeso`,
    "gestionale-demolizione-demo-v11:a",
    "gestionale-demolizione-demo-v11:a:in-sospeso",
    "gestionale-ultimo-tocco",
    "ebay-vendite-ultimo-controllo:a",
    S, // vecchia chiave senza azienda: la toglie già Hydrator
  ];
  assert.deepEqual(chiaviDaTogliere(chiavi, S, "b"), [`${S}:a`, "gestionale-demolizione-demo-v11:a", "gestionale-demolizione-demo-v11:a:in-sospeso"]);
});

test("nessuna altra azienda: non si toglie nulla", () => {
  assert.deepEqual(chiaviDaTogliere([`${S}:b`, `${S}:b:in-sospeso`, "altro"], S, "b"), []);
});
