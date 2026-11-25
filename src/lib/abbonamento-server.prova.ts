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

test("un abbonamento salvato prima della prova di 15 giorni si legge con fineProva null e spostamentoProva 0", async () => {
  const { aggiornaAbbonamento, leggiAbbonamento } = await import("./abbonamento-server.ts");
  const { ABBONAMENTO_NUOVO } = await import("./abbonamento.ts");
  const { cartellaAzienda } = await import("./server-data.ts");
  const { mkdir, writeFile } = await import("node:fs/promises");
  const vecchio: Record<string, unknown> = { ...ABBONAMENTO_NUOVO(true, 0), stato: "attivo", moduli: ["magazzino"] };
  delete vecchio.fineProva;
  delete vecchio.spostamentoProva;
  await mkdir(cartellaAzienda("azienda-vecchia"), { recursive: true });
  await writeFile(path.join(cartellaAzienda("azienda-vecchia"), "abbonamento.json"), JSON.stringify(vecchio));
  const letto = await leggiAbbonamento("azienda-vecchia");
  assert.equal(letto?.stato, "attivo");
  assert.equal(letto?.fineProva, null);
  assert.equal(letto?.spostamentoProva, 0);
  // Anche chi aggiorna riceve il documento con i campi della prova
  let visto: unknown;
  await aggiornaAbbonamento("azienda-vecchia", (p) => {
    visto = { fineProva: p?.fineProva, spostamentoProva: p?.spostamentoProva };
    return p!;
  });
  assert.deepEqual(visto, { fineProva: null, spostamentoProva: 0 });
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
