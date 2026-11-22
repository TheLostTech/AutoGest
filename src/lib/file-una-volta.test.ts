// File creati una volta sola: nessuno li legge mai vuoti, e se c'erano già restano quelli.
// Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readdirSync, readFileSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { creaUnaVolta, creaUnaVoltaSync } from "./file-una-volta.ts";

const cartella = () => mkdtempSync(path.join(tmpdir(), "una-volta-"));

test("il primo vince, il secondo trova il file del primo e non lo tocca", () => {
  const f = path.join(cartella(), ".segreto");
  assert.equal(creaUnaVoltaSync(f, "primo"), true);
  assert.equal(creaUnaVoltaSync(f, "secondo"), false);
  assert.equal(readFileSync(f, "utf8"), "primo");
  assert.equal(statSync(f).mode & 0o777, 0o600);
});

test("tante creazioni insieme: una sola riesce, il file è sempre completo e non restano temporanei", async () => {
  const dir = cartella();
  const f = path.join(dir, ".chiave");
  const contenuto = (i: number) => `chiave-${i}-${"x".repeat(5000)}`;
  const esiti = await Promise.all(Array.from({ length: 20 }, (_, i) => creaUnaVolta(f, contenuto(i))));
  assert.equal(esiti.filter(Boolean).length, 1);
  assert.equal(readFileSync(f, "utf8"), contenuto(esiti.indexOf(true)));
  assert.deepEqual(readdirSync(dir), [".chiave"]);
});
