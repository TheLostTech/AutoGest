import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readdir, readFile, stat, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { CollegamentiIlleggibili, leggiCollegamentiDaFile, scriviCollegamentiSuFile } from "./collegamenti-file.ts";

test("collegamenti: file assente = nessun collegamento", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "collegamenti-"));
  assert.deepEqual(await leggiCollegamentiDaFile(path.join(dir, "collegamenti.json")), {});
});

test("collegamenti: file corrotto o non oggetto = errore, mai vuoto", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "collegamenti-"));
  const f = path.join(dir, "collegamenti.json");
  for (const t of ['{"openapi":{"valori"', "null", "[]", "42"]) {
    await writeFile(f, t);
    await assert.rejects(leggiCollegamentiDaFile(f), CollegamentiIlleggibili, t);
  }
});

test("collegamenti: la scrittura passa da un file temporaneo, resta solo il file finale (0600)", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "collegamenti-"));
  const f = path.join(dir, "sotto", "collegamenti.json");
  await scriviCollegamentiSuFile(f, { a: { valori: { x: "1" }, segreti: {}, file: {} } });
  await scriviCollegamentiSuFile(f, { b: { valori: {}, segreti: {}, file: {} } });
  assert.deepEqual(JSON.parse(await readFile(f, "utf8")), { b: { valori: {}, segreti: {}, file: {} } });
  assert.deepEqual(await readdir(path.dirname(f)), ["collegamenti.json"]);
  assert.equal((await stat(f)).mode & 0o777, 0o600);
});
