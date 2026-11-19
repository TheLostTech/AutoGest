// Moduli a pagamento: a quale modulo appartiene ogni pagina e quali sono attivi. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync } from "node:fs";
import path from "node:path";
import { linkAttivazione, moduliAttivi, moduliDaArchivio, moduloDi, ORDINE_MODULI } from "./moduli.ts";

test("moduloDi: ogni percorso al suo modulo", () => {
  assert.equal(moduloDi("/ambiente/periodo?mese=2026-10"), "ambiente");
  assert.equal(moduloDi("/veicoli/V-000118/bonifica"), "ambiente");
  assert.equal(moduloDi("/veicoli/V-000118"), "magazzino");
  assert.equal(moduloDi("/veicoli/V-000118#pratica"), "magazzino");
  assert.equal(moduloDi("/vendite/documenti"), "vendite");
  assert.equal(moduloDi("/listini"), "vendite");
  assert.equal(moduloDi("/certificato/V-1"), "accettazione");
  assert.equal(moduloDi("/ordini"), "magazzino");
  assert.equal(moduloDi("/moduli/ambiente"), "magazzino");
  assert.equal(moduloDi("/"), "magazzino");
});

test("moduloDi: il prefisso vale per segmenti interi", () => {
  assert.equal(moduloDi("/venditex"), "magazzino");
  assert.equal(moduloDi("/ambientale"), "magazzino");
});

test("moduliAttivi: senza stato salvato sono tutti attivi", () => {
  assert.equal(moduliAttivi(undefined).size, 4);
  assert.equal(moduliAttivi([]).size, 4);
});

test("moduliAttivi: il Magazzino resta attivo anche se spento", () => {
  const m = moduliAttivi([
    { id: "vendite", attivo: false },
    { id: "magazzino", attivo: false },
  ]);
  assert.deepEqual([...m].sort(), ["accettazione", "ambiente", "magazzino"]);
});

test("linkAttivazione: messaggio WhatsApp già scritto", () => {
  assert.equal(
    linkAttivazione("Demo Srl", "accettazione"),
    "https://wa.me/390000000000?text=" + encodeURIComponent("Ciao, sono Demo Srl su AutoLost: vorrei attivare il modulo Accettazione."),
  );
});

test("moduliDaArchivio: archivio assente o non valido = tutti attivi", () => {
  assert.equal(moduliDaArchivio(null).size, 4);
  assert.equal(moduliDaArchivio({ state: { moduli: "x" } }).size, 4);
  assert.equal(moduliDaArchivio({ state: { moduli: [{ id: "accettazione", attivo: "no" }] } }).size, 4);
  const m = moduliDaArchivio({ state: { moduli: [{ id: "accettazione", attivo: false }] } });
  assert.equal(m.has("accettazione"), false);
  assert.equal(m.size, 3);
});

// Ogni pagina dell'app ha un modulo: una pagina nuova sotto un prefisso sbagliato non passa inosservata
const APP = path.join(import.meta.dirname, "..", "app");
const percorsoDi = (file: string) =>
  "/" +
  path
    .dirname(file)
    .split(path.sep)
    .filter((s) => s !== "." && !/^\(.*\)$/.test(s))
    .map((s) => (/^\[.*\]$/.test(s) ? "X" : s))
    .join("/");

test("ogni pagina ha un modulo", () => {
  const pagine = (readdirSync(APP, { recursive: true }) as string[]).filter((f) => path.basename(f) === "page.tsx").map(percorsoDi);
  assert.ok(pagine.length > 20, "pagine trovate");
  for (const p of pagine) assert.ok(ORDINE_MODULI.includes(moduloDi(p)), p);
  assert.ok(pagine.includes("/certificato/X"));
  assert.equal(moduloDi("/certificato/X"), "accettazione");
  assert.ok(pagine.includes("/veicoli/X/bonifica"));
  assert.equal(moduloDi("/veicoli/X/bonifica"), "ambiente");
});
