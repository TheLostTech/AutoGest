// Prova dell'archivio dell'abbonamento su una cartella dati temporanea (DATI_DIR sempre nuova, mai i dati veri).
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

process.env.DATI_DIR = mkdtempSync(path.join(tmpdir(), "prova-abbonamento-"));

test("leggiAbbonamento di un'azienda senza file dà null", async () => {
  const { leggiAbbonamento } = await import("./abbonamento-server.ts");
  assert.equal(await leggiAbbonamento("azienda-vuota"), null);
});

test("aggiornaAbbonamento mette in fila le scritture della stessa azienda", async () => {
  const { aggiornaAbbonamento, leggiAbbonamento } = await import("./abbonamento-server.ts");
  const { ABBONAMENTO_NUOVO } = await import("./abbonamento.ts");
  await Promise.all(Array.from({ length: 20 }, (_, i) =>
    aggiornaAbbonamento("azienda-fila", (p) => ({ ...(p ?? ABBONAMENTO_NUOVO(true, 0)), aggiornato: (p?.aggiornato ?? 0) + (i + 1) }))));
  const atteso = (20 * 21) / 2;
  assert.equal((await leggiAbbonamento("azienda-fila"))?.aggiornato, atteso);
  const { cartellaAzienda } = await import("./server-data.ts");
  const raw = await readFile(path.join(cartellaAzienda("azienda-fila"), "abbonamento.json"), "utf8");
  assert.equal(JSON.parse(raw).aggiornato, atteso);
});
