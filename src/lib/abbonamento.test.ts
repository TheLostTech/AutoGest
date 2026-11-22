import { test } from "node:test";
import assert from "node:assert/strict";
import {
  ABBONAMENTO_NUOVO, lookupKey, nomeStripe, moduliDaAbbonamento, bloccato,
  abbonamentoDaStripe, contoAllaRovescia, righeCambio, scritturaAzienda, statoPerBrowser, contaVeicoli, sceltaValida,
  fasciaDaMostrare, richiestaModuli, rifiutoCambio, nuovaOraOrologio, avanzamentoPermesso, passoValido,
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

test("sceltaValida: periodo e moduli dal corpo di Checkout", () => {
  assert.deepEqual(sceltaValida({ periodo: "anno", moduli: ["ambiente"] }), { periodo: "anno", moduli: ["magazzino", "ambiente"] });
  assert.equal(sceltaValida({ periodo: "settimana", moduli: ["ambiente"] }), null);
  assert.deepEqual(sceltaValida({ periodo: "mese", moduli: ["boh", "vendite"] }), { periodo: "mese", moduli: ["magazzino", "vendite"] });
  assert.equal(sceltaValida(null), null);
});

test("sceltaValida: doppioni e magazzino una volta sola, nell'ordine dei moduli", () => {
  assert.deepEqual(sceltaValida({ periodo: "mese", moduli: ["vendite", "magazzino", "vendite", "accettazione"] }), { periodo: "mese", moduli: ["magazzino", "accettazione", "vendite"] });
  assert.deepEqual(sceltaValida({ periodo: "mese" }), { periodo: "mese", moduli: ["magazzino"] });
  assert.equal(sceltaValida({ periodo: "mese", moduli: "ambiente" }), null);
  assert.equal(sceltaValida("anno"), null);
});

const GIORNO = 86_400_000;

test("fasciaDaMostrare: in ritardo sempre, disdetto negli ultimi 7 giorni, mai per gli altri stati", () => {
  assert.equal(fasciaDaMostrare(ab({ stato: "in-ritardo", rinnovo: ORA + 20 * GIORNO }), ORA), true);
  assert.equal(fasciaDaMostrare(ab({ stato: "disdetto", rinnovo: ORA + 8 * GIORNO }), ORA), false);
  assert.equal(fasciaDaMostrare(ab({ stato: "disdetto", rinnovo: ORA + 7 * GIORNO }), ORA), true);
  assert.equal(fasciaDaMostrare(ab({ stato: "disdetto", rinnovo: ORA - GIORNO }), ORA), true);
  assert.equal(fasciaDaMostrare(ab({ stato: "attivo", rinnovo: ORA + GIORNO }), ORA), false);
  assert.equal(fasciaDaMostrare(ab({ stato: "nuovo" }), ORA), false);
  assert.equal(fasciaDaMostrare(ab({ stato: "scaduto" }), ORA), false);
  assert.equal(fasciaDaMostrare(ab({ stato: "disdetto", rinnovo: null }), ORA), false);
});

test("fasciaDaMostrare: con l'orologio di prova conta oraOrologio, non l'ora del Mac", () => {
  // Il Mac dice 20 giorni alla fine, l'orologio di prova è già a 3 giorni
  const a = ab({ stato: "disdetto", rinnovo: ORA + 20 * GIORNO, oraOrologio: ORA + 17 * GIORNO });
  assert.equal(fasciaDaMostrare(a, ORA), true);
  assert.equal(fasciaDaMostrare({ ...a, oraOrologio: ORA }, ORA + 17 * GIORNO), false);
});

test("richiestaModuli: un'azione sola con un modulo conosciuto, oppure riattiva", () => {
  assert.deepEqual(richiestaModuli({ aggiungi: "accettazione" }), { azione: "aggiungi", modulo: "accettazione" });
  assert.deepEqual(richiestaModuli({ togli: "ambiente" }), { azione: "togli", modulo: "ambiente" });
  assert.deepEqual(richiestaModuli({ anteprima: "vendite" }), { azione: "anteprima", modulo: "vendite" });
  assert.deepEqual(richiestaModuli({ riattiva: true }), { azione: "riattiva" });
  assert.equal(richiestaModuli({ riattiva: "si" }), null);
  assert.equal(richiestaModuli({ aggiungi: "pratiche" }), null); // nome Stripe, non id dell'app
  assert.equal(richiestaModuli({ aggiungi: "accettazione", togli: "ambiente" }), null);
  assert.equal(richiestaModuli({}), null);
  assert.equal(richiestaModuli(null), null);
  assert.equal(richiestaModuli("aggiungi"), null);
  assert.equal(richiestaModuli({ aggiungi: ["ambiente"] }), null);
});

test("rifiutoCambio: stati ammessi, magazzino, doppioni e riattiva", () => {
  const attivo = ab({ stato: "attivo", periodo: "mese", moduli: ["magazzino", "ambiente"] });
  assert.equal(rifiutoCambio(attivo, { azione: "aggiungi", modulo: "accettazione" }), null);
  assert.equal(rifiutoCambio(attivo, { azione: "anteprima", modulo: "accettazione" }), null);
  assert.equal(rifiutoCambio(attivo, { azione: "togli", modulo: "ambiente" }), null);
  assert.equal(rifiutoCambio({ ...attivo, stato: "disdetto" }, { azione: "aggiungi", modulo: "vendite" }), null);
  assert.deepEqual(rifiutoCambio(attivo, { azione: "togli", modulo: "magazzino" }), { stato: 400, messaggio: "Il Magazzino non si toglie" });
  assert.deepEqual(rifiutoCambio(attivo, { azione: "aggiungi", modulo: "ambiente" }), { stato: 409, messaggio: "Modulo già attivo" });
  assert.deepEqual(rifiutoCambio(attivo, { azione: "anteprima", modulo: "magazzino" }), { stato: 409, messaggio: "Modulo già attivo" });
  assert.deepEqual(rifiutoCambio(attivo, { azione: "togli", modulo: "vendite" }), { stato: 409, messaggio: "Modulo non attivo" });
  for (const stato of ["nuovo", "in-ritardo", "scaduto"] as const) {
    assert.deepEqual(rifiutoCambio({ ...attivo, stato }, { azione: "aggiungi", modulo: "accettazione" }), { stato: 409, messaggio: "Abbonamento non attivo" });
  }
  assert.deepEqual(rifiutoCambio({ ...attivo, periodo: null }, { azione: "aggiungi", modulo: "accettazione" }), { stato: 409, messaggio: "Abbonamento non attivo" });
  assert.equal(rifiutoCambio({ ...attivo, stato: "disdetto" }, { azione: "riattiva" }), null);
  assert.deepEqual(rifiutoCambio(attivo, { azione: "riattiva" }), { stato: 409, messaggio: "L'abbonamento non è disdetto" });
});

test("nuovaOraOrologio: giorno e settimana aggiungono 24 ore e 7 × 24 ore", () => {
  assert.equal(nuovaOraOrologio(ORA, "giorno"), ORA + 86_400_000);
  assert.equal(nuovaOraOrologio(ORA, "settimana"), ORA + 7 * 86_400_000);
});

test("nuovaOraOrologio: mese e anno di calendario a Roma, stessa ora", () => {
  assert.equal(nuovaOraOrologio(ORA, "mese"), T(2026, 12, 22));
  assert.equal(nuovaOraOrologio(T(2027, 1, 31), "mese"), T(2027, 2, 28));
  assert.equal(nuovaOraOrologio(ORA, "anno"), T(2027, 11, 22));
  // 29 febbraio + 1 anno: ultimo giorno di febbraio
  assert.equal(nuovaOraOrologio(T(2028, 2, 29), "anno"), T(2029, 2, 28));
  // Dicembre → gennaio dell'anno dopo
  assert.equal(nuovaOraOrologio(T(2026, 12, 31), "mese"), T(2027, 1, 31));
});

test("nuovaOraOrologio: con il cambio dell'ora legale resta la stessa ora di Roma", () => {
  // 22/03/2027 13:00 a Roma (ora solare, 12:00 UTC) → 22/04/2027 13:00 a Roma (ora legale, 11:00 UTC)
  assert.equal(nuovaOraOrologio(Date.UTC(2027, 2, 22, 12), "mese"), Date.UTC(2027, 3, 22, 11));
  // Il contrario a ottobre: 22/10/2027 13:00 (legale, 11:00 UTC) → 22/11/2027 13:00 (solare, 12:00 UTC)
  assert.equal(nuovaOraOrologio(Date.UTC(2027, 9, 22, 11), "mese"), Date.UTC(2027, 10, 22, 12));
});

test("avanzamentoPermesso: +1 anno solo con l'annuale, gli altri sempre", () => {
  assert.equal(avanzamentoPermesso(ab({ stato: "attivo", periodo: "mese" }), "anno"), false);
  assert.equal(avanzamentoPermesso(ab({ stato: "attivo", periodo: "anno" }), "anno"), true);
  assert.equal(avanzamentoPermesso(ab({ stato: "nuovo", periodo: null }), "anno"), false);
  for (const periodo of ["mese", "anno", null] as const) {
    assert.equal(avanzamentoPermesso(ab({ periodo }), "mese"), true);
    assert.equal(avanzamentoPermesso(ab({ periodo }), "settimana"), true);
    assert.equal(avanzamentoPermesso(ab({ periodo }), "giorno"), true);
  }
});

test("passoValido: solo i quattro passi", () => {
  assert.equal(passoValido({ passo: "mese" }), "mese");
  assert.equal(passoValido({ passo: "giorno" }), "giorno");
  assert.equal(passoValido({ passo: "ora" }), null);
  assert.equal(passoValido({}), null);
  assert.equal(passoValido(null), null);
  assert.equal(passoValido("mese"), null);
});
