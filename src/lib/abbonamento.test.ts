import { test } from "node:test";
import assert from "node:assert/strict";
import {
  ABBONAMENTO_NUOVO, lookupKey, nomeStripe, moduliDaAbbonamento, bloccato, GIORNI_PROVA, avviaProva, oraProva, inProva, normalizzaAbbonamento,
  abbonamentoDaStripe, contoAllaRovescia, righeCambio, scritturaAzienda, statoPerBrowser, sceltaValida,
  fasciaDaMostrare, negozioAperto, riprendeDopoPagamento, senzaCliente, richiestaModuli, rifiutoCambio, nuovaOraOrologio, avanzamentoPermesso, passoValido,
  passoProvaValido, spostamentoPermesso, spostaProva,
  type Abbonamento, type SubStripe,
} from "./abbonamento.ts";

const T = (y: number, m: number, d: number) => Date.UTC(y, m - 1, d, 12); // mezzogiorno UTC: stessa data a Roma
const ORA = T(2026, 11, 22);
const RINNOVO = T(2026, 12, 22);

const ab = (o: Partial<Abbonamento> = {}): Abbonamento => ({ ...ABBONAMENTO_NUOVO(false, ORA), ...o });
const GIORNO = 86_400_000;
const FINE = ORA + 15 * GIORNO;
// In prova: registrata e confermata adesso (con le chiavi di prova di Stripe), 15 giorni da ORA
const prova = (o: Partial<Abbonamento> = {}): Abbonamento => ab({ prova: true, fineProva: FINE, ...o });

const sub = (o: { id?: string; status?: string; cancel?: boolean; cancelAt?: number | null; created?: number; modulo?: string; interval?: "month" | "year"; fine?: number } = {}): SubStripe => ({
  id: o.id ?? "sub_1", status: o.status ?? "active", cancel_at_period_end: o.cancel ?? false, cancel_at: o.cancelAt ?? null, created: o.created ?? 1000,
  items: [{ price: { recurring: { interval: o.interval ?? "month" }, product: { metadata: { modulo: o.modulo ?? "accettazione" } } }, current_period_end: o.fine ?? RINNOVO / 1000 }],
});

test("nomi e lookup key Stripe", () => {
  assert.equal(nomeStripe("accettazione"), "pratiche");
  assert.equal(nomeStripe("vendite"), "banco");
  assert.equal(lookupKey("accettazione", "mese"), "pratiche_mese");
  assert.equal(lookupKey("vendite", "anno"), "banco_anno");
});

test("moduliDaAbbonamento", () => {
  assert.deepEqual(moduliDaAbbonamento(ab({ stato: "nuovo" }), ORA), ["magazzino"]);
  assert.deepEqual(moduliDaAbbonamento(ab({ stato: "attivo", moduli: ["magazzino", "ambiente"] }), ORA), ["magazzino", "ambiente"]);
  assert.deepEqual(moduliDaAbbonamento(ab({ stato: "scaduto", moduli: ["magazzino", "ambiente"] }), ORA), ["magazzino"]);
  assert.deepEqual(moduliDaAbbonamento(ab({ stato: "attivo", moduli: ["ambiente"] }), ORA), ["magazzino", "ambiente"]);
});

test("moduliDaAbbonamento: in prova tutti e quattro, finita la prova solo il magazzino", () => {
  assert.deepEqual(moduliDaAbbonamento(prova(), ORA), ["magazzino", "accettazione", "ambiente", "vendite"]);
  assert.deepEqual(moduliDaAbbonamento(prova(), FINE - 1), ["magazzino", "accettazione", "ambiente", "vendite"]);
  assert.deepEqual(moduliDaAbbonamento(prova(), FINE), ["magazzino"]);
  assert.deepEqual(moduliDaAbbonamento(prova({ spostamentoProva: 15 * GIORNO }), ORA), ["magazzino"]);
});

test("bloccato: scaduto sempre, gli abbonamenti in corso mai", () => {
  assert.equal(bloccato(ab({ stato: "scaduto" }), ORA), true);
  assert.equal(bloccato(ab({ stato: "scaduto", fineProva: FINE }), ORA), true);
  assert.equal(bloccato(ab({ stato: "in-ritardo" }), ORA), false);
  assert.equal(bloccato(ab({ stato: "disdetto" }), ORA), false);
  assert.equal(bloccato(ab({ stato: "attivo" }), ORA), false);
  // Pagato durante la prova e poi la prova sarebbe finita: conta l'abbonamento
  assert.equal(bloccato(ab({ stato: "attivo", fineProva: FINE }), FINE + GIORNO), false);
});

test("bloccato: nuovo senza prova partita è bloccato", () => {
  assert.equal(bloccato(ab({ stato: "nuovo" }), ORA), true);
  assert.equal(bloccato(ab({ stato: "nuovo", fineProva: null }), 0), true);
});

test("bloccato: in prova fino a fineProva esclusa, anche con lo spostamento della prova", () => {
  assert.equal(bloccato(prova(), ORA), false);
  assert.equal(bloccato(prova(), FINE - 1), false);
  assert.equal(bloccato(prova(), FINE), true);
  assert.equal(bloccato(prova(), FINE + 30 * GIORNO), true);
  // +1 settimana dagli strumenti di prova: 7 giorni prima della fine vera è già finita
  const spostata = prova({ spostamentoProva: 7 * GIORNO });
  assert.equal(bloccato(spostata, FINE - 7 * GIORNO - 1), false);
  assert.equal(bloccato(spostata, FINE - 7 * GIORNO), true);
  assert.equal(bloccato(spostata, FINE - 1), true);
});

test("avviaProva: 15 giorni da adesso, una volta sola e solo per un'azienda nuova", () => {
  assert.equal(GIORNI_PROVA, 15);
  const a = avviaProva(ab(), ORA);
  assert.equal(a.fineProva, ORA + 15 * 86_400_000);
  assert.equal(a.stato, "nuovo");
  const ancora = avviaProva(a, ORA + 3 * GIORNO);
  assert.equal(ancora, a);
  assert.equal(ancora.fineProva, ORA + 15 * 86_400_000);
  const attivo = ab({ stato: "attivo" });
  assert.equal(avviaProva(attivo, ORA), attivo);
  const scaduto = ab({ stato: "scaduto" });
  assert.equal(avviaProva(scaduto, ORA), scaduto);
});

test("oraProva e inProva", () => {
  assert.equal(oraProva(prova(), ORA), ORA);
  assert.equal(oraProva(prova({ spostamentoProva: 2 * GIORNO }), ORA), ORA + 2 * GIORNO);
  assert.equal(inProva(prova(), ORA), true);
  assert.equal(inProva(prova(), FINE - 1), true);
  assert.equal(inProva(prova(), FINE), false);
  assert.equal(inProva(ab(), ORA), false);
  assert.equal(inProva(prova({ stato: "attivo" }), ORA), false);
  assert.equal(inProva(prova({ spostamentoProva: 15 * GIORNO }), ORA), false);
});

test("oraProva: lo spostamento conta solo con le chiavi di prova (a.prova), mai per un'azienda con le chiavi vere", () => {
  const vera = prova({ prova: false, spostamentoProva: 20 * GIORNO });
  assert.equal(oraProva(vera, ORA), ORA);
  assert.equal(inProva(vera, ORA), true);
  assert.equal(bloccato(vera, ORA), false);
  assert.equal(bloccato(vera, FINE), true);
  assert.equal(contoAllaRovescia(vera, ORA)?.giorni, 15);
  assert.equal(bloccato(prova({ spostamentoProva: 20 * GIORNO }), ORA), true);
});

test("passoProvaValido: solo giorno o settimana", () => {
  assert.equal(passoProvaValido({ passo: "giorno" }), "giorno");
  assert.equal(passoProvaValido({ passo: "settimana" }), "settimana");
  for (const c of [{ passo: "mese" }, { passo: "anno" }, {}, null, "giorno", ["giorno"], { passo: 1 }]) assert.equal(passoProvaValido(c), null, JSON.stringify(c));
});

test("spostamentoPermesso: solo nuovo, prova partita e chiavi di prova", () => {
  assert.equal(spostamentoPermesso(prova()), true);
  assert.equal(spostamentoPermesso(prova({ spostamentoProva: 30 * GIORNO })), true); // finita: si può ancora spostare
  assert.equal(spostamentoPermesso(ab({ prova: true })), false); // prova non partita
  assert.equal(spostamentoPermesso(prova({ prova: false })), false);
  for (const stato of ["attivo", "in-ritardo", "disdetto", "scaduto"] as const) assert.equal(spostamentoPermesso(prova({ stato })), false, stato);
  assert.equal(spostamentoPermesso(null), false);
});

test("spostaProva: +1 o +7 giorni allo spostamento, il resto non cambia", () => {
  const a = prova({ spostamentoProva: GIORNO });
  const g = spostaProva(a, "giorno");
  assert.equal(g.spostamentoProva, 2 * GIORNO);
  assert.deepEqual({ ...g, spostamentoProva: a.spostamentoProva }, a);
  assert.equal(spostaProva(a, "settimana").spostamentoProva, 8 * GIORNO);
  // Tre settimane dalla conferma: 21 giorni, oltre i 15 della prova
  const tre = spostaProva(spostaProva(spostaProva(prova(), "settimana"), "settimana"), "settimana");
  assert.equal(tre.spostamentoProva, 21 * GIORNO);
  assert.equal(bloccato(tre, ORA), true);
});

test("ABBONAMENTO_NUOVO: prova non partita, nessuno spostamento", () => {
  const a = ABBONAMENTO_NUOVO(true, ORA);
  assert.equal(a.fineProva, null);
  assert.equal(a.spostamentoProva, 0);
});

test("normalizzaAbbonamento: un documento salvato prima della prova si legge con fineProva null e spostamento 0", () => {
  const vecchio = { ...ab({ stato: "attivo", moduli: ["magazzino", "ambiente"] }) } as Partial<Abbonamento>;
  delete vecchio.fineProva;
  delete vecchio.spostamentoProva;
  const letto = normalizzaAbbonamento(vecchio as Abbonamento);
  assert.equal(letto.fineProva, null);
  assert.equal(letto.spostamentoProva, 0);
  assert.equal(letto.stato, "attivo");
  assert.deepEqual(letto.moduli, ["magazzino", "ambiente"]);
  // Valori non validi: come assenti
  const strano = normalizzaAbbonamento({ ...ab(), fineProva: "domani", spostamentoProva: Number.NaN } as unknown as Abbonamento);
  assert.equal(strano.fineProva, null);
  assert.equal(strano.spostamentoProva, 0);
  // Quelli buoni restano
  const buono = normalizzaAbbonamento(prova({ spostamentoProva: GIORNO }));
  assert.equal(buono.fineProva, FINE);
  assert.equal(buono.spostamentoProva, GIORNO);
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

test("abbonamentoDaStripe: disdetto anche con cancel_at (disdetta a una data), che vale come fine se viene prima", () => {
  const d = (s: SubStripe) => abbonamentoDaStripe([s], ab(), ORA, null);
  const prima = RINNOVO / 1000 - 5 * 86_400;
  const r = d(sub({ status: "active", cancelAt: prima }));
  assert.equal(r.stato, "disdetto");
  assert.equal(r.rinnovo, prima * 1000);
  assert.equal(d(sub({ status: "trialing", cancelAt: prima })).stato, "disdetto");
  // cancel_at dopo la fine del periodo: la fine resta quella del periodo
  const dopo = d(sub({ status: "active", cancelAt: RINNOVO / 1000 + 86_400 }));
  assert.equal(dopo.stato, "disdetto");
  assert.equal(dopo.rinnovo, RINNOVO);
  // Tutte e due: disdetto, fine del periodo
  const tutte = d(sub({ status: "active", cancel: true, cancelAt: RINNOVO / 1000 }));
  assert.equal(tutte.stato, "disdetto");
  assert.equal(tutte.rinnovo, RINNOVO);
  // Senza disdetta: attivo
  assert.equal(d(sub({ status: "active", cancelAt: null })).stato, "attivo");
  // past_due con cancel_at resta in ritardo
  assert.equal(d(sub({ status: "past_due", cancelAt: prima })).stato, "in-ritardo");
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

test("contoAllaRovescia in prova: giorni alla fine, più evidente negli ultimi 3", () => {
  assert.deepEqual(contoAllaRovescia(prova(), ORA), { tono: "ok", testo: "Prova gratuita: tra 15 giorni il gestionale si blocca", giorni: 15 });
  assert.deepEqual(contoAllaRovescia(prova(), FINE - 4 * GIORNO), { tono: "ok", testo: "Prova gratuita: tra 4 giorni il gestionale si blocca", giorni: 4 });
  assert.deepEqual(contoAllaRovescia(prova(), FINE - 3 * GIORNO), { tono: "avviso", testo: "Prova gratuita: tra 3 giorni il gestionale si blocca", giorni: 3 });
  assert.deepEqual(contoAllaRovescia(prova(), FINE - GIORNO), { tono: "avviso", testo: "Prova gratuita: tra 1 giorno il gestionale si blocca", giorni: 1 });
  // Meno di un giorno: si arrotonda in su
  assert.equal(contoAllaRovescia(prova(), FINE - 1)?.giorni, 1);
  // Lo spostamento della prova conta, l'orologio di Stripe no
  assert.equal(contoAllaRovescia(prova({ spostamentoProva: 11 * GIORNO }), ORA)?.testo, "Prova gratuita: tra 4 giorni il gestionale si blocca");
  assert.equal(contoAllaRovescia(prova({ spostamentoProva: 12 * GIORNO }), ORA)?.tono, "avviso");
  assert.equal(contoAllaRovescia(prova({ oraOrologio: FINE - GIORNO }), ORA)?.giorni, 15);
  // Finita la prova: niente conto (il riquadro di pagamento dice il resto)
  assert.equal(contoAllaRovescia(prova(), FINE), null);
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
  const r = scritturaAzienda(true, prova(), ORA, corpo);
  assert.equal(r.esito, "ok");
  if (r.esito === "ok") assert.deepEqual(r.corpo, { schema: "s", whole: { rules: [1] }, counters: { a: 1 } });
  const n = scritturaAzienda(false, null, ORA, corpo);
  assert.deepEqual(n, { esito: "ok", corpo });
});

test("scritturaAzienda: blocco per stato", () => {
  const c = { schema: "s", changes: { vehicles: [{ id: "V1" }] } };
  assert.equal(scritturaAzienda(true, ab({ stato: "attivo" }), ORA, c).esito, "ok");
  assert.equal(scritturaAzienda(true, ab({ stato: "in-ritardo" }), ORA, c).esito, "ok");
  assert.equal(scritturaAzienda(true, ab({ stato: "disdetto" }), ORA, c).esito, "ok");
  assert.equal(scritturaAzienda(true, ab({ stato: "scaduto" }), ORA, c).esito, "bloccato");
  assert.equal(scritturaAzienda(false, ab({ stato: "scaduto" }), ORA, c).esito, "ok");
  // Registrata senza prova partita (o senza file): bloccata
  assert.equal(scritturaAzienda(true, ab(), ORA, c).esito, "bloccato");
  assert.equal(scritturaAzienda(true, null, ORA, c).esito, "bloccato");
});

test("scritturaAzienda in prova: quanti veicoli si vuole, fino alla fine della prova", () => {
  const molti = { schema: "s", changes: { vehicles: [{ id: "V1" }, { id: "V2" }, { id: "V3" }] } };
  assert.equal(scritturaAzienda(true, prova(), ORA, molti).esito, "ok");
  assert.equal(scritturaAzienda(true, prova(), FINE - 1, molti).esito, "ok");
  const pezzo = { schema: "s", changes: { parts: [{ id: "P1" }] } };
  assert.equal(scritturaAzienda(true, prova(), FINE, pezzo).esito, "bloccato");
  assert.equal(scritturaAzienda(true, prova({ spostamentoProva: 15 * GIORNO }), ORA, pezzo).esito, "bloccato");
  // Pagato: si scrive anche dopo la fine della prova
  assert.equal(scritturaAzienda(true, prova({ stato: "attivo" }), FINE + GIORNO, pezzo).esito, "ok");
});

test("statoPerBrowser mette i moduli dell'abbonamento", () => {
  const r = statoPerBrowser(true, ab({ stato: "attivo", moduli: ["magazzino", "vendite"] }), ORA, { x: 1, moduli: [] }) as { x: number; moduli: { id: string; attivo: boolean }[] };
  assert.equal(r.x, 1);
  assert.deepEqual(r.moduli.map((m) => [m.id, m.attivo]), [["magazzino", true], ["accettazione", false], ["ambiente", false], ["vendite", true]]);
  const st = { moduli: [1] };
  assert.equal(statoPerBrowser(false, null, ORA, st), st);
  assert.equal(statoPerBrowser(true, null, ORA, null), null);
});

test("statoPerBrowser in prova: tutti i moduli accesi, finita la prova solo il magazzino", () => {
  const moduli = (ora: number) => (statoPerBrowser(true, prova(), ora, { moduli: [] }) as { moduli: { id: string; attivo: boolean }[] }).moduli.filter((m) => m.attivo).map((m) => m.id);
  assert.deepEqual(moduli(ORA), ["magazzino", "accettazione", "ambiente", "vendite"]);
  assert.deepEqual(moduli(FINE), ["magazzino"]);
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

test("fasciaDaMostrare: per tutta la prova, non dopo", () => {
  assert.equal(fasciaDaMostrare(prova(), ORA), true);
  assert.equal(fasciaDaMostrare(prova(), FINE - 10 * GIORNO), true);
  assert.equal(fasciaDaMostrare(prova(), FINE - 1), true);
  assert.equal(fasciaDaMostrare(prova(), FINE), false);
  assert.equal(fasciaDaMostrare(prova({ spostamentoProva: 15 * GIORNO }), ORA), false);
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

test("negozioAperto: non registrata sempre aperto; registrata chiude solo quando è bloccata", () => {
  const ab = (stato: Abbonamento["stato"]): Abbonamento => ({ ...ABBONAMENTO_NUOVO(false, ORA), stato });
  assert.equal(negozioAperto(false, ab("scaduto"), ORA), true);
  assert.equal(negozioAperto(false, null, ORA), true);
  assert.equal(negozioAperto(true, ab("scaduto"), ORA), false);
  assert.equal(negozioAperto(true, ab("in-ritardo"), ORA), true);
  assert.equal(negozioAperto(true, ab("attivo"), ORA), true);
  assert.equal(negozioAperto(true, prova(), ORA), true); // in prova
  assert.equal(negozioAperto(true, prova(), FINE), false); // prova finita: bloccata
  assert.equal(negozioAperto(true, null, ORA), false); // file assente: prova non partita, bloccata
});

test("senzaCliente: cliente sparito da Stripe, si riparte senza abbonamenti (scaduto se pagato, altrimenti nuovo)", () => {
  const pagato = ab({ stato: "attivo", periodo: "mese", moduli: ["magazzino", "ambiente"], rinnovo: RINNOVO, customerId: "cus_1", subscriptionId: "sub_1", orologioId: "clock_1", oraOrologio: ORA, pagatoAlmenoUnaVolta: true });
  const via = senzaCliente(pagato);
  assert.equal(via.customerId, null);
  assert.equal(via.subscriptionId, null);
  assert.equal(via.orologioId, null);
  assert.equal(via.oraOrologio, null);
  assert.equal(via.pagatoAlmenoUnaVolta, true);
  const r = abbonamentoDaStripe([], via, ORA, null);
  assert.equal(r.stato, "scaduto");
  assert.deepEqual(r.moduli, []);
  assert.equal(r.customerId, null); // il prossimo Checkout crea un cliente nuovo
  assert.equal(r.oraOrologio, null);
  const mai = abbonamentoDaStripe([], senzaCliente(ab({ stato: "nuovo", customerId: "cus_2" })), ORA, null);
  assert.equal(mai.stato, "nuovo");
  assert.equal(mai.customerId, null);
});

test("senzaCliente e abbonamentoDaStripe tengono la prova", () => {
  const p = prova({ customerId: "cus_3", spostamentoProva: GIORNO });
  const via = senzaCliente(p);
  assert.equal(via.fineProva, FINE);
  assert.equal(via.spostamentoProva, GIORNO);
  // Cliente creato al Checkout ma niente pagato: la prova continua
  const r = abbonamentoDaStripe([], p, ORA, null);
  assert.equal(r.stato, "nuovo");
  assert.equal(r.fineProva, FINE);
  assert.equal(r.spostamentoProva, GIORNO);
  assert.equal(inProva(r, ORA), true);
  // Pagamento non ancora concluso (incomplete): niente cambia, la prova continua
  assert.equal(inProva(abbonamentoDaStripe([sub({ status: "incomplete" })], p, ORA, null), ORA), true);
});

test("abbonamentoDaStripe: pagando durante la prova la prova finisce subito", () => {
  const r = abbonamentoDaStripe([sub({ modulo: "ambiente" })], prova(), ORA, null);
  assert.equal(r.stato, "attivo");
  assert.equal(inProva(r, ORA), false);
  assert.deepEqual(moduliDaAbbonamento(r, ORA), ["magazzino", "ambiente"]);
  assert.equal(bloccato(r, FINE + GIORNO), false);
  assert.equal(fasciaDaMostrare(r, ORA), false);
  assert.equal(contoAllaRovescia(r, ORA)?.testo, "Si rinnova il 22/12/2026 · tra 30 giorni");
});

test("riprendeDopoPagamento: le modifiche in attesa ripartono quando l'azienda non è più bloccata", () => {
  assert.equal(riprendeDopoPagamento(null, ORA), true); // azienda non registrata
  assert.equal(riprendeDopoPagamento(undefined, ORA), true);
  assert.equal(riprendeDopoPagamento(ab({ stato: "attivo" }), ORA), true);
  assert.equal(riprendeDopoPagamento(ab({ stato: "in-ritardo" }), ORA), true);
  assert.equal(riprendeDopoPagamento(ab({ stato: "disdetto" }), ORA), true);
  // Prova non partita, prova finita o scaduto: il server rifiuterebbe di nuovo, niente giro di 402
  assert.equal(riprendeDopoPagamento(ab({ stato: "nuovo" }), ORA), false);
  assert.equal(riprendeDopoPagamento(prova(), FINE), false);
  assert.equal(riprendeDopoPagamento(ab({ stato: "scaduto" }), ORA), false);
  // In prova le scritture passano: quelle in attesa ripartono
  assert.equal(riprendeDopoPagamento(prova(), ORA), true);
});
