// Ricerca tollerante di ricambi e tipologie. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { cercaTipologie, corrisponde } from "./cerca.ts";

test("trova la tipologia anche con doppie, maiuscole e parole in un altro ordine", () => {
  for (const q of ["bobina accensione", "bobbina accensione", "BOBINA", "accensione bobina", "bobine"]) {
    assert.equal(cercaTipologie(q)[0]?.id, "bobina", q);
  }
});

test("la categoria porta tutti i suoi pezzi, e il plurale trova il singolare", () => {
  const freni = cercaTipologie("freni").map((t) => t.id);
  assert.ok(freni.includes("pastiglie") && freni.includes("disco") && freni.includes("tamburo"));
  assert.ok(cercaTipologie("disco freno").every((t) => /disco/i.test(t.name)));
});

test("le tipologie che cominciano con la parola cercata vengono prima", () => {
  assert.equal(cercaTipologie("faro")[0]?.name.toLowerCase().startsWith("faro"), true);
});

test("i codici si trovano con o senza spazi e trattini", () => {
  assert.ok(corrisponde("EK482", ["EK 482 ZZ"]));
  assert.ok(corrisponde("1K0 510", ["1K0510601"]));
  assert.ok(corrisponde("r-002306", ["R-002306"]));
  assert.ok(!corrisponde("R-0023", ["R-02306"]), "le cifre doppie non si fondono");
});

test("tutte le parole devono esserci, in campi diversi va bene", () => {
  assert.ok(corrisponde("bobina panda", ["Bobina accensione", "Fiat Panda"]));
  assert.ok(!corrisponde("bobina punto", ["Bobina accensione", "Fiat Panda"]));
  assert.ok(corrisponde("", ["qualsiasi"]));
});

test("gli accenti non contano", () => {
  assert.ok(corrisponde("velocita", ["Sensore velocità"]));
});
