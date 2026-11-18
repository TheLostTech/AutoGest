// Codici di errore del collegamento eBay nell'indirizzo → testi fissi. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { CODICI_COLLEGAMENTO, testoErroreCollegamento } from "./codici.ts";

test("ogni codice ha il suo testo fisso con «Cosa fare»", () => {
  for (const c of CODICI_COLLEGAMENTO) {
    const t = testoErroreCollegamento(c);
    assert.ok(t.includes("Cosa fare"), c);
    if (c !== "imprevisto") assert.notEqual(t, testoErroreCollegamento("imprevisto"), c);
  }
});

test("codice sconosciuto o testo libero → testo generico, mai il testo dell'indirizzo", () => {
  const generico = testoErroreCollegamento("imprevisto");
  assert.equal(testoErroreCollegamento("Chiama il 333 per assistenza"), generico);
  assert.equal(testoErroreCollegamento(null), generico);
  assert.equal(testoErroreCollegamento("__proto__"), generico);
  assert.equal(testoErroreCollegamento("toString"), generico);
});
