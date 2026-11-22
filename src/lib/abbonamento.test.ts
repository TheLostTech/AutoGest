import { test } from "node:test";
import assert from "node:assert/strict";
import {
  ABBONAMENTO_NUOVO, lookupKey, nomeStripe, moduliDaAbbonamento, bloccato,
  abbonamentoDaStripe, contoAllaRovescia, righeCambio, scritturaAzienda, statoPerBrowser, contaVeicoli,
  type Abbonamento, type SubStripe,
} from "./abbonamento.ts";

const T = (y: number, m: number, d: number) => Date.UTC(y, m - 1, d, 12); // mezzogiorno UTC: stessa data a Roma
const ORA = T(2026, 11, 22);
const RINNOVO = T(2026, 12, 22);

const ab = (o: Partial<Abbonamento> = {}): Abbonamento => ({ ...ABBONAMENTO_NUOVO(false, ORA), ...o });

const sub = (o: { id?: string; status?: string; cancel?: boolean; created?: number; modulo?: string; interval?: "month" | "year"; fine?: number } = {}): SubStripe => ({
  id: o.id ?? "sub_1", status: o.status ?? "active", cancel_at_period_end: o.cancel ?? false, created: o.created ?? 1000,
  items: [{ price: { recurring: { interval: o.interval ?? "month" }, product: { metadata: { modulo: o.modulo ?? "accettazione" } } }, current_period_end: o.fine ?? RINNOVO / 1000 }],
});

test("nomi e lookup key Stripe", () => {
  assert.equal(nomeStripe("accettazione"), "pratiche");
  assert.equal(nomeStripe("vendite"), "banco");
  assert.equal(lookupKey("accettazione", "mese"), "pratiche_mese");
  assert.equal(lookupKey("vendite", "anno"), "banco_anno");
});

test("moduliDaAbbonamento", () => {
  assert.deepEqual(moduliDaAbbonamento(ab({ stato: "nuovo" })), ["magazzino"]);
  assert.deepEqual(moduliDaAbbonamento(ab({ stato: "attivo", moduli: ["magazzino", "ambiente"] })), ["magazzino", "ambiente"]);
  assert.deepEqual(moduliDaAbbonamento(ab({ stato: "scaduto", moduli: ["magazzino", "ambiente"] })), ["magazzino"]);
  assert.deepEqual(moduliDaAbbonamento(ab({ stato: "attivo", moduli: ["ambiente"] })), ["magazzino", "ambiente"]);
});

test("bloccato", () => {
  assert.equal(bloccato(ab({ stato: "nuovo" }), 0), false);
  assert.equal(bloccato(ab({ stato: "nuovo" }), 1), true);
  assert.equal(bloccato(ab({ stato: "scaduto" }), 0), true);
  assert.equal(bloccato(ab({ stato: "in-ritardo" }), 50), false);
  assert.equal(bloccato(ab({ stato: "disdetto" }), 50), false);
  assert.equal(bloccato(ab({ stato: "attivo" }), 50), false);
});

test("abbonamentoDaStripe: stati", () => {
  const d = (s: SubStripe[], prima = ab()) => abbonamentoDaStripe(s, prima, ORA, null);
  assert.equal(d([sub({ status: "active" })]).stato, "attivo");
  assert.equal(d([sub({ status: "active", cancel: true })]).stato, "disdetto");
  assert.equal(d([sub({ status: "past_due" })]).stato, "in-ritardo");
  for (const s of ["canceled", "unpaid", "incomplete_expired"]) assert.equal(d([sub({ status: s })]).stato, "scaduto");
  assert.equal(d([sub({ status: "incomplete" })], ab({ stato: "disdetto" })).stato, "disdetto");
  assert.equal(d([], ab({ pagatoAlmenoUnaVolta: false })).stato, "nuovo");
  assert.equal(d([], ab({ pagatoAlmenoUnaVolta: true, stato: "attivo" })).stato, "scaduto");
});

test("abbonamentoDaStripe: moduli, rinnovo, periodo", () => {
  const r = abbonamentoDaStripe([sub({ modulo: "ambiente", interval: "year" })], ab(), ORA, null);
  assert.deepEqual(r.moduli, ["ambiente"]);
  assert.equal(r.rinnovo, RINNOVO);
  assert.equal(r.periodo, "anno");
  assert.equal(r.subscriptionId, "sub_1");
  assert.equal(r.pagatoAlmenoUnaVolta, true);
  assert.equal(abbonamentoDaStripe([sub()], ab(), ORA, null).periodo, "mese");
  assert.deepEqual(abbonamentoDaStripe([sub({ modulo: "boh" })], ab(), ORA, null).moduli, []);
});

test("abbonamentoDaStripe sceglie l'abbonamento attivo tra più abbonamenti", () => {
  const r1 = abbonamentoDaStripe([sub({ id: "c", status: "canceled", created: 2000 }), sub({ id: "a", status: "active", created: 1000 })], ab(), ORA, null);
  assert.equal(r1.subscriptionId, "a");
  assert.equal(r1.stato, "attivo");
  const r2 = abbonamentoDaStripe([sub({ id: "vecchio", created: 1000 }), sub({ id: "nuovo", created: 2000 })], ab(), ORA, null);
  assert.equal(r2.subscriptionId, "nuovo");
});

test("contoAllaRovescia", () => {
  const a = ab({ stato: "attivo", rinnovo: RINNOVO });
  assert.deepEqual(contoAllaRovescia(a, ORA), { tono: "ok", testo: "Si rinnova il 22/12/2026 · tra 30 giorni", giorni: 30 });
  assert.equal(contoAllaRovescia(a, RINNOVO)?.testo, "Si rinnova oggi");
  const d = contoAllaRovescia(ab({ stato: "disdetto", rinnovo: RINNOVO }), ORA);
  assert.equal(d?.testo, "Finisce il 22/12/2026 · tra 30 giorni. Poi il gestionale si blocca, i dati restano.");
  assert.equal(d?.tono, "avviso");
  const r = contoAllaRovescia(ab({ stato: "in-ritardo", rinnovo: RINNOVO }), ORA);
  assert.deepStrictEqual(r, { tono: "errore", testo: "Pagamento non riuscito: aggiorna la carta. Stripe riprova da solo.", giorni: null });
  assert.equal(contoAllaRovescia(ab({ stato: "scaduto" }), ORA), null);
  assert.equal(contoAllaRovescia(ab({ stato: "nuovo" }), ORA), null);
});

test("contoAllaRovescia usa oraOrologio quando c'è", () => {
  const c = contoAllaRovescia(ab({ stato: "attivo", rinnovo: RINNOVO, oraOrologio: T(2026, 12, 20) }), ORA);
  assert.match(c!.testo, /tra 2 giorni/);
  assert.equal(c!.giorni, 2);
});

test("righeCambio", () => {
  const att = ab({ stato: "attivo", moduli: ["magazzino"] });
  assert.deepEqual(righeCambio(ab({ stato: "nuovo" }), att), ["Abbonamento attivato"]);
  assert.deepEqual(righeCambio(att, { ...att, moduli: ["magazzino", "ambiente"] }), ["Modulo aggiunto: Ambiente"]);
  assert.deepEqual(righeCambio({ ...att, moduli: ["magazzino", "ambiente"] }, att), ["Modulo tolto: Ambiente"]);
  assert.deepEqual(righeCambio(att, { ...att, stato: "in-ritardo" }), ["Pagamento non riuscito"]);
  assert.deepEqual(righeCambio(att, { ...att, stato: "disdetto" }), ["Abbonamento disdetto"]);
  assert.deepEqual(righeCambio({ ...att, stato: "disdetto" }, att), ["Abbonamento riattivato"]);
  assert.deepEqual(righeCambio(att, { ...att, stato: "scaduto" }), ["Abbonamento scaduto"]);
  assert.deepEqual(righeCambio(att, att), []);
  assert.deepEqual(
    righeCambio(ab({ stato: "nuovo" }), { ...att, moduli: ["magazzino", "vendite"] }),
    ["Abbonamento attivato", "Modulo aggiunto: Vendite"],
  );
});

test("scritturaAzienda toglie i moduli mandati dal browser", () => {
  const corpo = { schema: "s", whole: { moduli: [{ id: "vendite", attivo: true }], rules: [1] }, counters: { a: 1 } };
  const r = scritturaAzienda(true, ab(), { prima: 0, dopo: 0 }, corpo);
  assert.equal(r.esito, "ok");
  if (r.esito === "ok") assert.deepEqual(r.corpo, { schema: "s", whole: { rules: [1] }, counters: { a: 1 } });
  const n = scritturaAzienda(false, null, { prima: 5, dopo: 5 }, corpo);
  assert.deepEqual(n, { esito: "ok", corpo });
});

test("scritturaAzienda: blocco per stato e veicoli", () => {
  const c = { schema: "s", changes: { vehicles: [{ id: "V1" }] } };
  assert.equal(scritturaAzienda(true, ab(), { prima: 0, dopo: 1 }, c).esito, "ok");
  assert.equal(scritturaAzienda(true, null, { prima: 0, dopo: 1 }, c).esito, "ok");
  assert.equal(scritturaAzienda(true, ab(), { prima: 0, dopo: 2 }, c).esito, "bloccato");
  assert.equal(scritturaAzienda(true, ab(), { prima: 0, dopo: 1 }, c).esito, "ok");
  assert.equal(scritturaAzienda(true, ab({ stato: "attivo" }), { prima: 9, dopo: 9 }, c).esito, "ok");
  assert.equal(scritturaAzienda(false, ab({ stato: "scaduto" }), { prima: 9, dopo: 9 }, c).esito, "ok");
});

test("scritturaAzienda blocca un primo invio con più veicoli", () => {
  const c = { schema: "s", changes: { vehicles: [{ id: "V1" }, { id: "V2" }, { id: "V3" }] } };
  assert.equal(scritturaAzienda(true, ab(), { prima: 0, dopo: 3 }, c).esito, "bloccato");
  assert.equal(scritturaAzienda(true, ab({ stato: "in-ritardo" }), { prima: 1, dopo: 3 }, c).esito, "ok");
  assert.equal(scritturaAzienda(true, ab({ stato: "disdetto" }), { prima: 1, dopo: 3 }, c).esito, "ok");
  assert.equal(scritturaAzienda(true, ab({ stato: "scaduto" }), { prima: 0, dopo: 0 }, c).esito, "bloccato");
});

test("scritturaAzienda blocca le scritture dopo il primo veicolo", () => {
  const c = { schema: "s", changes: { parts: [{ id: "P1" }] } };
  assert.equal(scritturaAzienda(true, ab(), { prima: 1, dopo: 1 }, c).esito, "bloccato");
  assert.equal(scritturaAzienda(true, ab(), { prima: Infinity, dopo: 1 }, c).esito, "bloccato");
  assert.equal(scritturaAzienda(true, ab({ stato: "attivo" }), { prima: 1, dopo: 1 }, c).esito, "ok");
});

test("contaVeicoli: lista, assente, valore non valido (blocca)", () => {
  assert.equal(contaVeicoli(null), 0);
  assert.equal(contaVeicoli({}), 0);
  assert.equal(contaVeicoli({ vehicles: [1, 2] }), 2);
  assert.equal(scritturaAzienda(true, ab(), { prima: 0, dopo: contaVeicoli({ vehicles: "x" }) }, { schema: "s" }).esito, "bloccato");
});

test("statoPerBrowser mette i moduli dell'abbonamento", () => {
  const r = statoPerBrowser(true, ab({ stato: "attivo", moduli: ["magazzino", "vendite"] }), { x: 1, moduli: [] }) as { x: number; moduli: { id: string; attivo: boolean }[] };
  assert.equal(r.x, 1);
  assert.deepEqual(r.moduli.map((m) => [m.id, m.attivo]), [["magazzino", true], ["accettazione", false], ["ambiente", false], ["vendite", true]]);
  const st = { moduli: [1] };
  assert.equal(statoPerBrowser(false, null, st), st);
  assert.equal(statoPerBrowser(true, null, null), null);
});
