// Moduli a pagamento: a quale modulo appartiene ogni pagina e quali sono attivi. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync } from "node:fs";
import path from "node:path";
import { SERVIZI } from "./collegamenti.ts";
import { filtraAgenda, linkAttivazione, moduliAttivi, moduliDaArchivio, moduloDi, moduloDoc, ORDINE_MODULI, tabsAttive } from "./moduli.ts";

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

// Documenti di vendita: quelli degli ordini online sono del Magazzino, quelli del banco di Vendite
test("moduloDoc: documento al suo modulo", () => {
  const orders = [
    { id: "O-1", channel: "banco" as const },
    { id: "O-2", channel: "negozio" as const },
    { id: "O-3", channel: "marketplace" as const },
  ];
  assert.equal(moduloDoc({ type: "preventivo", orderId: "O-2" }, orders), "vendite");
  assert.equal(moduloDoc({ type: "fattura", orderId: "O-1" }, orders), "vendite");
  assert.equal(moduloDoc({ type: "fattura", orderId: "O-2" }, orders), "magazzino");
  assert.equal(moduloDoc({ type: "nota di credito", orderId: "O-3" }, orders), "magazzino");
  assert.equal(moduloDoc({ type: "documento commerciale" }, orders), "vendite");
  assert.equal(moduloDoc({ type: "fattura", orderId: "O-9" }, orders), "vendite");
});

// Coda "Oggi": niente voci dei moduli spenti, tranne la bonifica che senza Ambiente si segna dalla scheda
test("filtraAgenda: voci dei moduli spenti tolte, bonifica verso la scheda", () => {
  const voci = [
    { id: "a", kind: "pratica" as const, href: "/veicoli/V-1#pratica" },
    { id: "b", kind: "ambiente" as const, href: "/ambiente/periodo?mese=2026-10" },
    { id: "c", kind: "ambiente" as const, href: "/veicoli/V-1/bonifica" },
    { id: "d", kind: "ordine" as const, href: "/ordini" },
    { id: "e", kind: "ordine" as const, href: "/vendite" },
    { id: "f", kind: "veicolo" as const, href: "/campo/V-1" },
  ];
  const soloBase = filtraAgenda(voci, moduliAttivi([{ id: "accettazione", attivo: false }, { id: "ambiente", attivo: false }, { id: "vendite", attivo: false }]));
  assert.deepEqual(
    soloBase.map((v) => `${v.id} ${v.href}`),
    ["c /veicoli/V-1#bonifica", "d /ordini", "f /campo/V-1"],
  );
  assert.deepEqual(filtraAgenda(voci, moduliAttivi(undefined)), voci);
});

// Collegamenti: ogni servizio esterno appartiene a un modulo
test("ogni servizio ha un modulo", () => {
  for (const s of SERVIZI) assert.ok(ORDINE_MODULI.includes(s.modulo), s.id);
  const openapi = SERVIZI.find((s) => s.id === "openapi")!;
  assert.equal(openapi.modulo, "magazzino");
  const opzioni = openapi.campi.find((c) => c.key === "servizi")?.opzioni ?? [];
  assert.deepEqual(Object.keys(openapi.opzioniModulo ?? {}).filter((k) => !opzioni.includes(k)), []);
  assert.equal(openapi.opzioniModulo?.["Visura PRA"], "accettazione");
  assert.equal(SERVIZI.find((s) => s.id === "rvfu")?.modulo, "accettazione");
  assert.equal(SERVIZI.find((s) => s.id === "platerecognizer")?.modulo, "magazzino");
});

// Barra inferiore del telefono: mai schede bloccate, mai doppie
type T = { area?: string; href?: string };
const aperta = (chiuse: string[]) => (t: T) => !chiuse.includes(t.area ?? t.href ?? "");

test("tabsAttive: la scheda chiusa lascia il posto alla prima area aperta", () => {
  const tabs: T[] = [{ area: "oggi" }, { area: "veicoli" }, { area: "ambiente" }, { area: "ufficio" }];
  const ricambi: T[] = [{ area: "oggi" }, { area: "veicoli" }, { area: "ricambi" }, { area: "ufficio" }];
  assert.deepEqual(tabsAttive(tabs, ricambi, aperta(["ambiente"])), [{ area: "oggi" }, { area: "veicoli" }, { area: "ricambi" }, { area: "ufficio" }]);
});

test("tabsAttive: non duplica una scheda già presente", () => {
  const tabs: T[] = [{ area: "oggi" }, { area: "vendite" }, { area: "ricambi" }, { href: "/scansione" }];
  const ricambi: T[] = [{ area: "oggi" }, { area: "ricambi" }];
  assert.deepEqual(tabsAttive(tabs, ricambi, aperta(["vendite"])), [{ area: "oggi" }, { area: "ricambi" }, { href: "/scansione" }]);
});

test("tabsAttive: consulente senza ambiente", () => {
  const tabs: T[] = [{ area: "oggi" }, { href: "/ambiente/periodo" }, { href: "/ambiente" }, { href: "/ambiente/formulari" }];
  const r = tabsAttive(tabs, [{ area: "oggi" }], aperta(["/ambiente/periodo", "/ambiente", "/ambiente/formulari"]));
  assert.deepEqual(r, [{ area: "oggi" }]);
});
