// Codici e campi del registro come li vogliono RENTRI e MUD (verificati il 25/11/2026). Si eseguono con: npm test
process.env.TZ = "Europe/Rome";

import { test } from "node:test";
import assert from "node:assert/strict";
import { mudVeicoliRicevuti, moveIssues, normalizzaMovimenti, rigaRentri } from "./periodo.ts";
import { BONIFICA, datiCompleti, datiRifiuto, EER, eerBatteriaTrazione, eerByCode, eerValido, movesForBonifica, movesForIntake, pericoloso, typicalBonifica } from "./ambiente.ts";
import type { Vehicle, WasteMove } from "./types.ts";

let seq = 0;
const mv = (p: Partial<WasteMove>): WasteMove => ({
  id: `M-${++seq}`,
  at: "2026-10-10T10:00:00+02:00",
  kind: "carico",
  eer: "16 01 04*",
  kg: 1000,
  origin: "V-1",
  rentri: "da trasmettere",
  ...p,
});

const veicolo = (p: Partial<Vehicle>) => ({ id: "V-1", plate: "AA000AA", year: 2010, fuel: "Benzina", weightKg: 1000, dossier: { number: "CR-1" } as Vehicle["dossier"], ...p }) as Vehicle;

test("la causale «ricevuto da terzi» è T*, come nelle API RENTRI; i dati vecchi con *T si convertono", () => {
  const [carico] = movesForIntake(veicolo({}), "2026-11-25T10:00:00+01:00");
  assert.equal(carico.causale, "T*");
  const vecchi = [{ id: "a", causale: "*T" }, { id: "b", causale: "NP" }];
  assert.deepEqual(normalizzaMovimenti(vecchi).map((m) => m.causale), ["T*", "NP"]);
  const nuovi = [{ id: "c", causale: "T*" }];
  assert.equal(normalizzaMovimenti(nuovi), nuovi, "senza dati vecchi non si copia niente");
});

test("ogni movimento generato ha provenienza S e le classi di pericolo del codice", () => {
  const v = veicolo({});
  const { moves } = movesForBonifica(v, typicalBonifica(v), "2026-11-25T10:00:00+01:00");
  for (const m of [...movesForIntake(v, "2026-11-25T10:00:00+01:00"), ...moves]) {
    assert.equal(m.provenienza, "S", m.eer);
    assert.deepEqual(m.hp, eerByCode(m.eer)?.hp, m.eer);
  }
});

test("i codici non pericolosi non hanno classi di pericolo; le classi sono nel formato HP01–HP15", () => {
  for (const e of EER) {
    if (!pericoloso(e.code)) assert.deepEqual(e.hp, [], e.code);
    for (const h of e.hp) assert.match(h, /^HP(0[1-9]|1[0-5])$/, e.code);
  }
  assert.equal(new Set(EER.map((e) => e.code)).size, EER.length, "codici doppi");
});

test("codice pericoloso senza classi di pericolo: avviso finché non è trasmesso o rettificato", () => {
  const m = mv({ numero: 1, registeredAt: "2026-10-10T10:00:00+02:00", eer: "13 02 08*", causale: "NP", hp: [] });
  assert.deepEqual(moveIssues(m).map((i) => [i.code, i.blocking]), [["hp-mancanti", false]]);
  assert.deepEqual(moveIssues(m, undefined, true), []);
  assert.deepEqual(moveIssues({ ...m, rentri: "trasmesso" }), []);
  assert.deepEqual(moveIssues({ ...m, eer: "16 01 06" }), []);
  assert.deepEqual(datiCompleti(m).hp, datiRifiuto("13 02 08*").hp, "la rettifica le completa dal codice");
});

test("batterie: dal 9/12/2026 la batteria di trazione è 16 06 07*, prima 16 06 05", () => {
  assert.equal(eerBatteriaTrazione("2026-12-08T23:00:00+01:00"), "16 06 05");
  assert.equal(eerBatteriaTrazione("2026-12-09T08:00:00+01:00"), "16 06 07*");
  assert.equal(eerValido(eerByCode("16 06 05")!, "2026-12-09"), false);
  assert.equal(eerValido(eerByCode("16 06 07*")!, "2026-12-09"), true);
});

test("bonifica: serbatoio del gas solo per GPL e metano, batteria di trazione solo per elettriche e ibride", () => {
  const keys = (fuel: string) => typicalBonifica(veicolo({ fuel })).map((i) => i.key);
  assert.ok(keys("GPL").includes("serbatoio-gas"));
  assert.ok(keys("Metano").includes("serbatoio-gas"));
  assert.ok(!keys("Benzina").includes("serbatoio-gas"));
  assert.ok(keys("Elettrica").includes("trazione"));
  assert.ok(!keys("Diesel").includes("trazione"));
  for (const b of BONIFICA) assert.ok(eerByCode(b.eer(veicolo({}), "2026-11-25")), `codice della voce ${b.key} non in tabella`);
  for (const b of BONIFICA) assert.ok(eerByCode(b.eer(veicolo({}), "2026-12-10")), `codice della voce ${b.key} non in tabella`);
});

test("MUD: 16 01 04 ricevuto diviso per immatricolazione prima e dal 1980, con rettifiche e annullamenti", () => {
  const reg = { causale: "T*" as const, vfu: true, registeredAt: "2026-03-01T10:00:00+01:00" };
  const a = mv({ ...reg, id: "A", numero: 1, origin: "V-A", kg: 900, at: "2026-03-01T10:00:00+01:00" });
  const b = mv({ ...reg, id: "B", numero: 2, origin: "V-B", kg: 1100, at: "2026-04-01T10:00:00+02:00" });
  const c = mv({ ...reg, id: "C", numero: 3, origin: "V-C", kg: 1000, at: "2026-05-01T10:00:00+02:00" });
  const d = mv({ ...reg, id: "D", numero: 4, origin: "V-D", kg: 800, at: "2026-05-02T10:00:00+02:00" });
  const bozza = mv({ causale: "T*", vfu: true, id: "E", origin: "V-E", kg: 700 });
  const vecchio = mv({ ...reg, id: "F", numero: 9, origin: "V-A", kg: 500, at: "2025-12-01T10:00:00+01:00" });
  const rett = mv({ id: "R", numero: 5, causale: "RETT", rettificaDi: "B", kg: 1050, registeredAt: "2026-06-01T10:00:00+02:00" });
  const ann = mv({ id: "N", numero: 6, causale: "ANN", annullaDi: "C", kg: 0, registeredAt: "2026-06-02T10:00:00+02:00" });
  const anni: Record<string, number> = { "V-A": 1978, "V-B": 2005, "V-C": 1990 };
  const r = mudVeicoliRicevuti([a, b, c, d, bozza, vecchio, rett, ann], (id) => anni[id], 2026);
  assert.deepEqual(r, { anno: 2026, veicoli: 3, totaleKg: 2750, prima1980Kg: 900, dal1980Kg: 1050, senzaAnno: 1 });
});

test("riga RENTRI: rettifica e annullamento richiamano il numero, la differenza di pesata in più è NP", () => {
  const orig = mv({ id: "O", numero: 7, causale: "T*", registeredAt: "2026-10-10T10:00:00+02:00" });
  const rett = mv({ id: "R", numero: 8, causale: "RETT", rettificaDi: "O", registeredAt: "2026-10-12T10:00:00+02:00" });
  const ann = mv({ id: "N", numero: 9, causale: "ANN", annullaDi: "O", registeredAt: "2026-10-13T10:00:00+02:00" });
  const piu = mv({ id: "P", numero: 10, causale: "DIFF", kind: "carico" });
  const meno = mv({ id: "Q", numero: 11, causale: "DIFF", kind: "scarico" });
  const all = [orig, rett, ann, piu, meno];
  assert.deepEqual(rigaRentri(orig, all), { causale: "T*", provenienza: "S" });
  assert.deepEqual(rigaRentri(rett, all), { causale: "T*", rettificaDi: "7/2026", provenienza: "S" });
  assert.deepEqual(rigaRentri(ann, all), { causale: "", annullaDi: "7/2026", provenienza: "S" });
  assert.equal(rigaRentri(piu, all).causale, "NP");
  assert.equal(rigaRentri(meno, all).causale, "");
  assert.ok(rigaRentri(meno, all).nota);
});
