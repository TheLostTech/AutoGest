// Prove del deposito su disco, su una cartella dati temporanea (DATI_DIR sempre nuova, mai i dati veri).
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync } from "node:fs";
import { mkdir, readFile, rm, stat, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { provaContratto } from "./contratto.ts";

const cartella = mkdtempSync(path.join(tmpdir(), "prova-deposito-"));
process.env.DATI_DIR = cartella;

provaContratto(
  "disco",
  async () => (await import("./disco.ts")).depositoDisco(),
  () => rm(cartella, { recursive: true, force: true }),
);

test("disco: un JSON illeggibile non si sovrascrive mai", async () => {
  const { depositoDisco } = await import("./disco.ts");
  const { DocumentoIlleggibile } = await import("./tipi.ts");
  const { cartellaAzienda } = await import("../server-data.ts");
  const dir = cartellaAzienda("az-rovinata");
  await mkdir(dir, { recursive: true });
  const file = path.join(dir, "state.json");
  await writeFile(file, "{non json");
  const d = depositoDisco();
  await assert.rejects(d.leggiDocumento("az-rovinata", "archivio"), DocumentoIlleggibile);
  await assert.rejects(d.aggiornaDocumento("az-rovinata", "archivio", () => ({ dati: { n: 1 }, risultato: 0 })), DocumentoIlleggibile);
  assert.equal(await readFile(file, "utf8"), "{non json");
});

test("disco: collegamenti ed ebay hanno permessi 0o600", async () => {
  const { depositoDisco } = await import("./disco.ts");
  const { cartellaAzienda } = await import("../server-data.ts");
  const d = depositoDisco();
  await d.aggiornaDocumento("az-permessi", "collegamenti", () => ({ dati: { a: 1 }, risultato: 0 }));
  await d.creaDocumento("az-permessi", "ebay", { a: 1 });
  for (const f of ["collegamenti.json", "ebay.json"]) {
    assert.equal((await stat(path.join(cartellaAzienda("az-permessi"), f))).mode & 0o777, 0o600);
  }
});

test("archivio illeggibile → ArchivioIlleggibile, e il file resta com'era", async () => {
  const { leggiStato, aggiornaStato } = await import("../archivio-azienda.ts");
  const { ArchivioIlleggibile } = await import("../archivio-file.ts");
  const { DocumentoIlleggibile } = await import("./tipi.ts");
  const { cartellaAzienda } = await import("../server-data.ts");
  const dir = cartellaAzienda("az-archivio-rovinato");
  await mkdir(dir, { recursive: true });
  const file = path.join(dir, "state.json");
  await writeFile(file, "{non json");
  const e = await leggiStato("az-archivio-rovinato").catch((x) => x);
  assert.ok(e instanceof ArchivioIlleggibile);
  assert.ok(e instanceof DocumentoIlleggibile);
  await assert.rejects(aggiornaStato("az-archivio-rovinato", (s) => ({ stored: s, risultato: 0 })), ArchivioIlleggibile);
  assert.equal(await readFile(file, "utf8"), "{non json");
});
