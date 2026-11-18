// Testo automatico degli annunci. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  EBAY_CATEGORY_QUERY,
  buildDescription,
  buildTitle,
  compatVehicles,
  gpsrFor,
  generateText,
} from "./annuncio-testo.ts";
import type { Part, Vehicle } from "./types.ts";

const base = {
  tipo: "Faro anteriore",
  lato: "dx",
  marca: "Alfa Romeo",
  modello: "Giulietta",
  versione: "1.4 T-Jet 120 CV",
  anni: "2014",
  oem: "50510123",
};

test("il titolo completo sta in 80 caratteri", () => {
  const t = buildTitle(base);
  assert.equal(t, "Faro anteriore dx Alfa Romeo Giulietta 1.4 T-Jet 120 CV 2014 OE 50510123 usato");
  assert.ok(t.length <= 80);
});

test("se è troppo lungo toglie prima la versione, poi gli anni, e tiene il codice", () => {
  const t = buildTitle({ ...base, versione: "2.0 JTDm Distinctive Business Plus 170 CV" });
  assert.ok(!t.includes("JTDm"));
  assert.ok(t.includes("OE 50510123"));
  assert.ok(t.length <= 80);
  const l = buildTitle({
    ...base,
    versione: "2.0 JTDm Distinctive Business Plus 170 CV",
    modello: "Giulietta Quadrifoglio Verde Super Sportiva Edizione Limitata Speciale",
  });
  assert.ok(l.length <= 80);
  assert.ok(l.endsWith("usato"));
  assert.ok(l.includes("OE 50510123"));
});

test("nomi accentati entro 80 caratteri", () => {
  const t = buildTitle({
    ...base,
    tipo: "Fanale posteriore",
    marca: "Citroën",
    modello: "C4 Grand Picasso",
    versione: "1.6 e-HDi 115 CV Exclusive",
  });
  assert.ok(t.length <= 80);
  assert.ok(t.includes("Citroën"));
});

const desc = { condizione: "Buono", spiegazione: "Funzionante", spedibile: true, quanti: 1 };

test("con più pezzi la descrizione non dà km e difetti del singolo", () => {
  const d = buildDescription({ ...desc, quanti: 3, km: 120000, difetti: "graffio" });
  assert.ok(!d.includes("km"));
  assert.ok(!d.includes("graffio"));
  assert.ok(d.includes("Disponibili 3 pezzi uguali"));
  const s = buildDescription({ ...desc, km: 120000 });
  assert.ok(s.includes("120.000 km"));
});

test("solo ritiro scritto nella descrizione", () => {
  assert.ok(buildDescription({ ...desc, spedibile: false }).includes("Solo ritiro in sede"));
  assert.ok(!buildDescription(desc).includes("Solo ritiro in sede"));
});

test("compatibilità senza doppioni", () => {
  const v = {
    id: "V1",
    make: "Alfa Romeo",
    model: "Giulietta",
    version: "1.4",
    year: 2014,
    platform: "alfa-giulietta-940",
  } as Vehicle;
  const p = (id: string, verified: boolean) =>
    ({ id, vehicleId: "V1", compat: { platforms: ["alfa-giulietta-940"], source: "x", verified } }) as Part;
  const plats = [{ id: "alfa-giulietta-940", make: "Alfa Romeo", model: "Giulietta", years: "2010–2020" }];
  const r = compatVehicles([p("R1", true), p("R2", true)], [v], plats);
  assert.equal(r.length, 2);
  assert.equal(r.filter((x) => x.anni).length, 1);
  assert.equal(r.filter((x) => x.anno === 2014).length, 1);
  assert.equal(compatVehicles([p("R3", false)], [v], plats).length, 1);
});

test("gpsr", () => {
  assert.equal(gpsrFor(2014, "Fiat").tipo, "esente");
  assert.equal(gpsrFor(2024, "Fiat").tipo, "da confermare");
  assert.equal(gpsrFor(undefined, "Fiat").tipo, "da confermare");
  assert.equal(gpsrFor(2025, "MarcaSconosciuta").tipo, "da confermare");
});

test("ogni tipo di pezzo ha le parole per la categoria", () => {
  const ids = [
    "motore", "cambio", "alternatore", "motorino", "centralina", "batteria", "faro", "fanale",
    "specchietto", "porta", "cofano", "paraurti", "cerchio", "disco", "ammortizzatore",
    "radiatore", "compressore", "quadro",
  ];
  for (const id of ids) assert.ok(EBAY_CATEGORY_QUERY[id], id);
});

test("generateText unisce titolo e descrizione", () => {
  const r = generateText({ ...desc, tipo: "Faro anteriore", marca: "Fiat", oem: "123", anno: 2014 });
  assert.ok(r.titolo.endsWith("usato"));
  assert.ok(r.descrizione.includes("Pezzo controllato e catalogato con codice univoco"));
});
