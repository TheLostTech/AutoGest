// Regole del registro rifiuti e del periodo RENTRI. Si eseguono con: npm test
process.env.TZ = "Europe/Rome";

import { test } from "node:test";
import assert from "node:assert/strict";
import {
  canTransmit,
  currentKg,
  deadlineOf,
  firNumberLooksValid,
  firNumberTaken,
  isDraft,
  missingFields,
  monthKey,
  monthLabel,
  monthStock,
  moveIssues,
  nextRegisterNumber,
  parseKg,
  periodsOf,
  workingDaysAfter,
} from "./periodo.ts";
import type { Fir, WasteMove } from "./types.ts";

let seq = 0;
const mv = (p: Partial<WasteMove>): WasteMove => ({
  id: `M-${++seq}`,
  at: "2026-10-10T10:00:00+02:00",
  kind: "carico",
  eer: "16 01 04*",
  hp: ["HP14"], // i codici pericolosi hanno le classi di pericolo (senza, c'è un avviso: vedi codici-rifiuti.test.ts)
  kg: 1000,
  origin: "V-1",
  rentri: "da trasmettere",
  ...p,
});
const fir = (p: Partial<Fir>): Fir => ({
  id: "F-1",
  at: "2026-10-12T10:00:00+02:00",
  numero: "JNMPC 00262 JC",
  emessoAt: "2026-10-12T09:00:00+02:00",
  eer: "16 01 06",
  kg: 5000,
  destinatarioId: "S-2",
  trasportatoreId: "S-2",
  rinfusa: true,
  status: "firmato",
  history: [],
  ...p,
});

test("monthKey: le 23:30 del 31 ottobre in Italia sono ottobre", () => {
  assert.equal(monthKey("2026-10-31T22:30:00Z"), "2026-10");
  assert.equal(monthKey("2026-11-01T00:30:00+01:00"), "2026-11");
});

test("monthLabel in italiano", () => {
  assert.equal(monthLabel("2026-10"), "ottobre 2026");
});

test("deadlineOf: fine del mese successivo, anche a cavallo d'anno", () => {
  const ott = new Date(deadlineOf("2026-10"));
  assert.deepEqual([ott.getFullYear(), ott.getMonth(), ott.getDate(), ott.getHours()], [2026, 10, 30, 23]);
  const dic = new Date(deadlineOf("2026-12"));
  assert.deepEqual([dic.getFullYear(), dic.getMonth(), dic.getDate()], [2027, 0, 31]);
});

test("parseKg: solo numeri maggiori di zero, virgola italiana", () => {
  for (const bad of ["0", "-5", "abc", "", "  "]) assert.equal(parseKg(bad), null, bad);
  assert.equal(parseKg("1.234,5"), 1234.5);
  assert.equal(parseKg("38,5"), 38.5);
  assert.equal(parseKg("5000"), 5000);
});

test("missingFields: carico di un veicolo fuori uso", () => {
  const ok = mv({ causale: "T*", vfu: true, produttore: { nome: "Mario Rossi", cf: "RSSMRA80A01L219X" }, certificato: { numero: "CR-1", data: "2026-10-10" }, pesoPesa: true });
  assert.deepEqual(missingFields(ok), []);
  assert.ok(missingFields({ ...ok, produttore: { nome: "Mario Rossi" } }).includes("cf-produttore"));
  assert.ok(missingFields({ ...ok, certificato: undefined }).includes("certificato"));
  assert.ok(missingFields({ ...ok, pesoPesa: false }).includes("peso"));
  assert.deepEqual(missingFields(mv({ causale: "NP", kg: 12 })), []);
  assert.ok(missingFields(mv({ causale: "NP", kg: 0 })).includes("peso"));
});

test("isDraft: una registrazione senza numero è una bozza", () => {
  assert.equal(isDraft(mv({})), true);
  assert.equal(isDraft(mv({ numero: 3 })), false);
});

test("workingDaysAfter: si saltano sabato e domenica", () => {
  const fromFri = new Date(workingDaysAfter("2026-11-13T18:00:00+01:00", 2));
  assert.deepEqual([fromFri.getMonth(), fromFri.getDate()], [10, 17]);
  const fromMon = new Date(workingDaysAfter("2026-11-16T09:00:00+01:00", 2));
  assert.deepEqual([fromMon.getMonth(), fromMon.getDate()], [10, 18]);
  const tenWd = new Date(workingDaysAfter("2026-11-16T09:00:00+01:00", 10));
  assert.deepEqual([tenWd.getMonth(), tenWd.getDate()], [10, 30]);
});

test("moveIssues: bozze bloccanti, formulari come avvisi", () => {
  assert.deepEqual(moveIssues(mv({ causale: "T*" })).map((i) => [i.code, i.blocking]), [["bozza", true]]);
  const out = mv({ numero: 1, kind: "scarico", causale: "aT", eer: "16 01 06", kg: 5000, fir: "F-1" });
  assert.deepEqual(moveIssues(out, fir({})).map((i) => i.code), ["esito-mancante"]);
  assert.deepEqual(moveIssues(out, fir({ esito: "respinto", kgAccettati: 0 })).map((i) => i.code), ["respinto"]);
  assert.deepEqual(moveIssues(out, fir({ esito: "parziale", kgAccettati: 4850 })).map((i) => [i.code, i.blocking]), [["kg-diversi", false]]);
  assert.ok(moveIssues(out, fir({ numero: "F-000012", esito: "accettato", kgAccettati: 5000 })).some((i) => i.code === "fir-formato"));
  assert.deepEqual(moveIssues(out, fir({ esito: "accettato", kgAccettati: 5000 })), []);
  assert.deepEqual(moveIssues(mv({ numero: 2, kind: "scarico", causale: "I" })), []);
});

test("firNumberLooksValid: formato della vidimazione RENTRI", () => {
  assert.equal(firNumberLooksValid("JNMPC 00262 JC"), true);
  assert.equal(firNumberLooksValid("JNMPC00262JC"), true);
  assert.equal(firNumberLooksValid("F-000012"), false);
});

test("periodsOf: trasmesso, da trasmettere, aperto", () => {
  const now = new Date("2026-11-17T12:00:00+01:00");
  const moves = [
    mv({ numero: 1, at: "2026-09-05T10:00:00+02:00", registeredAt: "2026-09-05T10:00:00+02:00", rentri: "trasmesso", rentriRicevuta: "R-9" }),
    mv({ numero: 2, at: "2026-10-05T10:00:00+02:00", registeredAt: "2026-10-05T10:00:00+02:00" }),
    mv({ numero: 3, at: "2026-11-05T10:00:00+01:00", registeredAt: "2026-11-05T10:00:00+01:00" }),
  ];
  const ps = periodsOf(moves, [], now);
  assert.deepEqual(ps.map((p) => [p.key, p.status]), [["2026-09", "trasmesso"], ["2026-10", "da trasmettere"], ["2026-11", "aperto"]]);
  assert.equal(ps[0].ricevuta, "R-9");
});

test("periodsOf: una bozza conta nel mese dell'operazione", () => {
  const now = new Date("2026-11-17T12:00:00+01:00");
  const ps = periodsOf([mv({ numero: 2, registeredAt: "2026-10-05T10:00:00+02:00" }), mv({ at: "2026-10-30T10:00:00+01:00" })], [], now);
  assert.equal(ps[0].drafts, 1);
});

test("canTransmit: solo mesi chiusi, con registrazioni e senza bozze", () => {
  const now = new Date("2026-11-17T12:00:00+01:00");
  const reg = mv({ numero: 2, registeredAt: "2026-10-05T10:00:00+02:00" });
  assert.equal(canTransmit(periodsOf([reg], [], now)[0]), true);
  assert.equal(canTransmit(periodsOf([reg, mv({ at: "2026-10-20T10:00:00+02:00" })], [], now)[0]), false);
  const nov = mv({ numero: 3, at: "2026-11-05T10:00:00+01:00", registeredAt: "2026-11-05T10:00:00+01:00" });
  assert.equal(canTransmit(periodsOf([nov], [], now)[0]), false);
  assert.equal(canTransmit({ key: "2026-10", label: "", deadline: "", status: "da trasmettere", moves: [], drafts: 0, warnings: 0 }), false);
});

test("monthStock: rettifiche e annullamenti si applicano", () => {
  const a = mv({ numero: 1, registeredAt: "2026-10-05T10:00:00+02:00", kg: 1000 });
  const b = mv({ numero: 2, registeredAt: "2026-10-06T10:00:00+02:00", kg: 800 });
  const rett = mv({ numero: 3, registeredAt: "2026-10-07T10:00:00+02:00", causale: "RETT", rettificaDi: a.id, kg: 950 });
  const ann = mv({ numero: 4, registeredAt: "2026-10-08T10:00:00+02:00", causale: "ANN", annullaDi: b.id, kg: 0 });
  const bozza = mv({ kg: 500 });
  const row = monthStock([a, b, rett, ann, bozza], "2026-10", [{ code: "16 01 04*", limitKg: 900 }]).find((r) => r.code === "16 01 04*")!;
  assert.equal(row.giacenza, 950);
  assert.equal(row.carichi, 950);
  assert.equal(row.over, true);
});

test("nextRegisterNumber: progressivo per anno", () => {
  const moves = [
    mv({ numero: 9, registeredAt: "2025-12-30T10:00:00+01:00" }),
    mv({ numero: 1, registeredAt: "2026-01-02T10:00:00+01:00" }),
    mv({ numero: 3, registeredAt: "2026-03-02T10:00:00+01:00" }),
    mv({ numero: 2, registeredAt: "2026-02-02T10:00:00+01:00" }),
  ];
  assert.equal(nextRegisterNumber(moves, "2026-11-17T10:00:00+01:00"), 4);
  assert.equal(nextRegisterNumber(moves, "2027-01-03T10:00:00+01:00"), 1);
});

test("parseKg: il punto come decimale (tastiera del telefono) non moltiplica per 10", () => {
  assert.equal(parseKg("38.5"), 38.5);
  assert.equal(parseKg("1234.5"), 1234.5);
  assert.equal(parseKg("4.3"), 4.3);
  assert.equal(parseKg("1.234"), 1234);
  assert.equal(parseKg("12.345.678"), 12345678);
  assert.equal(parseKg("0x10"), null);
  assert.equal(parseKg("1e3"), null);
});

test("missingFields: lo scarico interno resta bozza finché il carico d'ingresso è bozza", () => {
  const carico = mv({ id: "C-1", causale: "T*", vfu: true, produttore: { nome: "A" }, pesoPesa: true, certificato: { numero: "CR", data: "2026-10-01" } });
  const scarico = mv({ kind: "scarico", causale: "I", caricoRif: "C-1" });
  assert.ok(missingFields(scarico, [carico, scarico]).includes("carico"));
  assert.deepEqual(missingFields(scarico, [{ ...carico, numero: 4 }, scarico]), []);
});

test("missingFields: senza nome di chi conferisce non si numera", () => {
  const m = mv({ causale: "T*", vfu: true, produttore: { nome: "", cf: "X" }, pesoPesa: true, certificato: { numero: "CR", data: "2026-10-01" } });
  assert.ok(missingFields(m).includes("produttore"));
  assert.ok(missingFields({ ...m, produttore: undefined }).includes("produttore"));
});

test("monthStock: la giacenza negativa non si nasconde", () => {
  const c = mv({ numero: 1, registeredAt: "2026-10-05T10:00:00+02:00", kg: 100 });
  const s = mv({ numero: 2, registeredAt: "2026-10-06T10:00:00+02:00", kind: "scarico", kg: 300 });
  const row = monthStock([c, s], "2026-10", [{ code: "16 01 04*", limitKg: 1000 }])[0];
  assert.equal(row.giacenza, -200);
  assert.equal(row.negative, true);
});

test("periodsOf: due registrazioni con lo stesso numero nello stesso anno bloccano la trasmissione", () => {
  const now = new Date("2026-11-17T12:00:00+01:00");
  const a = mv({ numero: 7, registeredAt: "2026-10-05T10:00:00+02:00" });
  const b = mv({ numero: 7, registeredAt: "2026-10-06T10:00:00+02:00" });
  const p = periodsOf([a, b], [], now)[0];
  assert.equal(p.duplicates, 2);
  assert.equal(canTransmit(p), false);
});

test("moveIssues: rettifica o annullamento tolgono gli avvisi del formulario", () => {
  const out = mv({ numero: 1, kind: "scarico", causale: "aT", eer: "16 01 06", kg: 5000, fir: "F-1" });
  assert.deepEqual(moveIssues(out, fir({ esito: "parziale", kgAccettati: 4850 }), true), []);
  assert.deepEqual(moveIssues(out, fir({ esito: "respinto", kgAccettati: 0 }), true), []);
  assert.match(moveIssues(out, fir({ esito: "respinto", kgAccettati: 0 }))[0].text, /annulla/i);
});

test("firNumberTaken: lo stesso formulario non si registra due volte", () => {
  const firs = [fir({ numero: "JNMPC 00262 JC" })];
  assert.equal(firNumberTaken(firs, "jnmpc00262jc"), true);
  assert.equal(firNumberTaken(firs, "JNMPC 00263 JC"), false);
});

test("moveIssues: pesa molto diversa dal libretto è un avviso", () => {
  const m = mv({ numero: 9, causale: "T*", vfu: true, kg: 700, kgLibretto: 975, pesoPesa: true, produttore: { nome: "A", cf: "X" }, certificato: { numero: "CR", data: "2026-10-01" } });
  assert.deepEqual(moveIssues(m).map((i) => [i.code, i.blocking]), [["peso-diverso", false]]);
  assert.deepEqual(moveIssues({ ...m, kg: 990 }), []);
});

test("differenza di pesata: si segnala da verificare e conta in giacenza", () => {
  const c = mv({ numero: 1, registeredAt: "2026-10-05T10:00:00+02:00", eer: "16 06 01*", kg: 420 });
  const d = mv({ numero: 2, registeredAt: "2026-10-20T10:00:00+02:00", eer: "16 06 01*", kind: "scarico", causale: "DIFF", kg: 22 });
  assert.deepEqual(moveIssues(d).map((i) => [i.code, i.blocking]), [["diff-pesata", false]]);
  assert.deepEqual(moveIssues(d, undefined, true), []);
  const row = monthStock([c, d], "2026-10", [{ code: "16 06 01*", limitKg: 3000 }])[0];
  assert.equal(row.giacenza, 398);
});

test("una differenza di pesata confermata dalla consulente non è più un avviso", () => {
  const d = mv({ numero: 2, registeredAt: "2026-10-20T10:00:00+02:00", kind: "scarico", causale: "DIFF", kg: 22, verificato: { at: "2026-10-21T10:00:00+02:00", by: "Laura" } });
  assert.deepEqual(moveIssues(d), []);
});

test("currentKg: i kg di una registrazione tengono conto dell'ultima rettifica", () => {
  const c = mv({ numero: 10, registeredAt: "2026-10-10T10:00:00+02:00", kg: 1040 });
  assert.equal(currentKg([c], c.id), 1040);
  const r1 = mv({ numero: 11, registeredAt: "2026-10-11T10:00:00+02:00", causale: "RETT", rettificaDi: c.id, kg: 1010 });
  const r2 = mv({ numero: 12, registeredAt: "2026-10-12T10:00:00+02:00", causale: "RETT", rettificaDi: c.id, kg: 995 });
  assert.equal(currentKg([c, r1, r2], c.id), 995);
  assert.equal(currentKg([r2, r1, c], c.id), 995); // non dipende dall'ordine della lista
  assert.equal(currentKg([c], "inesistente"), undefined);
});
