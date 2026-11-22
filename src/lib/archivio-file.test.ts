import { test } from "node:test";
import assert from "node:assert/strict";
import { chmod, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { ArchivioIlleggibile, leggiStatoDaFile } from "./archivio-file.ts";

test("file assente: archivio vuoto, non un errore", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "archivio-"));
  const s = await leggiStatoDaFile(path.join(dir, "state.json"));
  assert.equal(s.state, null);
  assert.equal(s.version, 0);
});

test("file valido: si legge", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "archivio-"));
  const f = path.join(dir, "state.json");
  await writeFile(f, JSON.stringify({ schema: "x", version: 3, state: { a: 1 } }));
  assert.equal((await leggiStatoDaFile(f)).version, 3);
});

test("file corrotto o non leggibile: errore (mai archivio vuoto da sovrascrivere)", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "archivio-"));
  const f = path.join(dir, "state.json");
  await writeFile(f, '{"schema":"x","version":3,"sta');
  await assert.rejects(leggiStatoDaFile(f), ArchivioIlleggibile);
  await writeFile(f, "null");
  await assert.rejects(leggiStatoDaFile(f), ArchivioIlleggibile);
  await writeFile(f, "{}");
  await chmod(f, 0o000);
  try {
    if (process.getuid?.() !== 0) await assert.rejects(leggiStatoDaFile(f), ArchivioIlleggibile);
  } finally {
    await chmod(f, 0o600);
  }
});
