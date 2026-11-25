import { test } from "node:test";
import assert from "node:assert/strict";
import { ABBONAMENTO_NUOVO, type Abbonamento } from "../abbonamento.ts";
import { abbonamentoAzzerato, azioneCliente, aziendaDaEvento, chiaveCheckout, daSincronizzare, eventoDiUnAltroAmbiente, origineRitorno, pagamentoInCorso, sessioniDaScadere, type SessioneCheckout, ESPANSIONI, espansioneValida, etichettaStripe, modalitaDaChiave, sincronizzazioneLimitata, stessoAmbiente } from "./chiavi.ts";

test("modalitaDaChiave: senza chiave è spenta", () => {
  assert.equal(modalitaDaChiave(undefined, undefined), "spenta");
  assert.equal(modalitaDaChiave("", "1"), "spenta");
});

test("modalitaDaChiave: le chiavi di prova danno prova", () => {
  assert.equal(modalitaDaChiave("sk_test_x", undefined), "prova");
  assert.equal(modalitaDaChiave("rk_test_x", undefined), "prova");
  assert.equal(modalitaDaChiave("sk_test_x", "1"), "prova");
});

test("modalitaDaChiave: una chiave vera serve il flag STRIPE_LIVE=1", () => {
  assert.equal(modalitaDaChiave("sk_live_x", undefined), "spenta");
  assert.equal(modalitaDaChiave("sk_live_x", "true"), "spenta");
  assert.equal(modalitaDaChiave("sk_live_x", "1"), "live");
  assert.equal(modalitaDaChiave("rk_live_x", "1"), "live");
});

test("modalitaDaChiave: qualunque altra stringa è spenta", () => {
  assert.equal(modalitaDaChiave("pk_test_x", undefined), "spenta");
  assert.equal(modalitaDaChiave("ciao", "1"), "spenta");
  assert.equal(modalitaDaChiave(" sk_test_x", undefined), "spenta");
});

test("etichettaStripe: la riga della Piattaforma", () => {
  assert.equal(etichettaStripe("prova"), "Stripe: prova (AutoLost demo)");
  assert.equal(etichettaStripe("live"), "Stripe: live");
  assert.equal(etichettaStripe("spenta"), "Stripe: spento");
});

test("aziendaDaEvento: l'orologio pronto si cerca per orologio", () => {
  assert.deepEqual(aziendaDaEvento({ type: "test_helpers.test_clock.ready", data: { object: { id: "clock_1", object: "test_helpers.test_clock" } } }), { orologio: "clock_1" });
});

test("aziendaDaEvento: metadata.azienda dell'oggetto vince", () => {
  assert.deepEqual(aziendaDaEvento({ type: "customer.subscription.updated", data: { object: { id: "sub_1", metadata: { azienda: "az1" }, customer: "cus_1" } } }), { azienda: "az1" });
});

test("aziendaDaEvento: Checkout porta l'azienda in client_reference_id", () => {
  assert.deepEqual(aziendaDaEvento({ type: "checkout.session.completed", data: { object: { id: "cs_1", metadata: {}, client_reference_id: "az2", customer: "cus_2" } } }), { azienda: "az2" });
});

test("aziendaDaEvento: senza azienda si passa dal cliente (stringa o oggetto)", () => {
  assert.deepEqual(aziendaDaEvento({ type: "invoice.paid", data: { object: { id: "in_1", customer: "cus_3" } } }), { cliente: "cus_3" });
  assert.deepEqual(aziendaDaEvento({ type: "invoice.payment_failed", data: { object: { id: "in_2", customer: { id: "cus_4" } } } }), { cliente: "cus_4" });
});

test("aziendaDaEvento: niente da cui partire dà null", () => {
  assert.equal(aziendaDaEvento({ type: "invoice.paid", data: { object: { id: "in_3" } } }), null);
  assert.equal(aziendaDaEvento({ type: "invoice.paid", data: { object: { id: "in_4", metadata: { azienda: "" }, customer: null } } }), null);
});

test("aziendaDaEvento: gli eventi non ascoltati si ignorano", () => {
  assert.equal(aziendaDaEvento({ type: "charge.succeeded", data: { object: { id: "ch_1", metadata: { azienda: "az1" } } } }), null);
});

test("daSincronizzare: a richiesta sempre, altrimenti solo il titolare dopo un'ora", () => {
  const ora = 10_000_000;
  assert.equal(daSincronizzare({ richiesta: true, titolare: false, aggiornato: ora, ora }), true);
  assert.equal(daSincronizzare({ richiesta: false, titolare: true, aggiornato: ora - 3_600_001, ora }), true);
  assert.equal(daSincronizzare({ richiesta: false, titolare: true, aggiornato: ora - 3_600_000, ora }), false);
  assert.equal(daSincronizzare({ richiesta: false, titolare: false, aggiornato: 0, ora }), false);
});

test("espansioneValida: al massimo quattro proprietà per stringa (limite di Stripe)", () => {
  assert.equal(espansioneValida("items.data.price.product"), true);
  assert.equal(espansioneValida("customer"), true);
  assert.equal(espansioneValida("data.items.data.price.product"), false);
  assert.equal(espansioneValida(""), false);
});

test("ESPANSIONI: ogni espansione usata dal codice sta nel limite", () => {
  const tutte = Object.values(ESPANSIONI).flat();
  assert.ok(tutte.length > 0);
  for (const e of tutte) assert.equal(espansioneValida(e), true, e);
});

const ab = (x: Partial<Abbonamento>): Abbonamento => ({ ...ABBONAMENTO_NUOVO(true, 0), ...x });

test("stessoAmbiente: prova con prova, vero con live, mai con spenta", () => {
  assert.equal(stessoAmbiente(ab({ prova: true }), "prova"), true);
  assert.equal(stessoAmbiente(ab({ prova: false }), "live"), true);
  assert.equal(stessoAmbiente(ab({ prova: true }), "live"), false);
  assert.equal(stessoAmbiente(ab({ prova: false }), "prova"), false);
  assert.equal(stessoAmbiente(ab({ prova: true }), "spenta"), false);
});

test("azioneCliente: stesso ambiente, si riusa il cliente o se ne crea uno", () => {
  assert.equal(azioneCliente(null, "prova"), "crea");
  assert.equal(azioneCliente(ab({ prova: true }), "prova"), "crea");
  assert.equal(azioneCliente(ab({ prova: true, customerId: "cus_1" }), "prova"), "riusa");
  assert.equal(azioneCliente(ab({ prova: false, customerId: "cus_2" }), "live"), "riusa");
});

test("azioneCliente: altro ambiente mai pagato si azzera, pagato si rifiuta", () => {
  assert.equal(azioneCliente(ab({ prova: true }), "live"), "azzera-e-crea");
  assert.equal(azioneCliente(ab({ prova: true, customerId: "cus_t", orologioId: "clock_1" }), "live"), "azzera-e-crea");
  assert.equal(azioneCliente(ab({ prova: false, customerId: "cus_l" }), "prova"), "azzera-e-crea");
  assert.equal(azioneCliente(ab({ prova: true, customerId: "cus_t", pagatoAlmenoUnaVolta: true, stato: "scaduto" }), "live"), "rifiuta");
});

test("abbonamentoAzzerato: cambiando ambiente Stripe la prova resta, lo spostamento solo con le chiavi di prova", () => {
  const prima = ab({ prova: true, customerId: "cus_t", orologioId: "clock_1", oraOrologio: 5, fineProva: 1_000_000, spostamentoProva: 86_400_000 });
  const live = abbonamentoAzzerato(prima, "live", 42);
  assert.equal(live.prova, false);
  assert.equal(live.customerId, null);
  assert.equal(live.orologioId, null);
  assert.equal(live.fineProva, 1_000_000);
  assert.equal(live.spostamentoProva, 0);
  assert.equal(live.aggiornato, 42);
  const test = abbonamentoAzzerato({ ...prima, prova: false }, "prova", 42);
  assert.equal(test.prova, true);
  assert.equal(test.fineProva, 1_000_000);
  assert.equal(test.spostamentoProva, 86_400_000);
  assert.deepEqual(abbonamentoAzzerato(null, "live", 7), ABBONAMENTO_NUOVO(false, 7));
});

test("azioneCliente: con Stripe spento si rifiuta", () => {
  assert.equal(azioneCliente(null, "spenta"), "rifiuta");
  assert.equal(azioneCliente(ab({ customerId: "cus_1" }), "spenta"), "rifiuta");
});

test("sincronizzazioneLimitata: niente Stripe se l'ultimo tentativo è di meno di 15 secondi fa", () => {
  assert.equal(sincronizzazioneLimitata(null, 100_000), false);
  assert.equal(sincronizzazioneLimitata(100_000, 100_000), true);
  assert.equal(sincronizzazioneLimitata(100_000, 114_999), true);
  assert.equal(sincronizzazioneLimitata(100_000, 115_000), false);
});

const sess = (o: Partial<SessioneCheckout> = {}): SessioneCheckout => ({
  id: "cs_1", customer: "cus_1", status: "open", payment_status: "unpaid", subscription: null, metadata: {}, ...o,
});

test("pagamentoInCorso: un abbonamento incomplete del cliente blocca un nuovo Checkout", () => {
  assert.equal(pagamentoInCorso("cus_1", [{ customer: "cus_1", status: "incomplete" }], []), true);
  assert.equal(pagamentoInCorso("cus_1", [{ customer: "cus_2", status: "incomplete" }], []), false);
  assert.equal(pagamentoInCorso("cus_1", [{ customer: "cus_1", status: "incomplete_expired" }], []), false);
  assert.equal(pagamentoInCorso("cus_1", [], []), false);
});

test("pagamentoInCorso: una sessione completa ma non pagata del cliente blocca", () => {
  assert.equal(pagamentoInCorso("cus_1", [], [sess({ status: "complete", payment_status: "unpaid" })]), true);
  assert.equal(pagamentoInCorso("cus_1", [], [sess({ status: "complete", payment_status: "unpaid", subscription: { status: "incomplete" } })]), true);
  assert.equal(pagamentoInCorso("cus_1", [], [sess({ status: "complete", payment_status: "paid" })]), false);
  assert.equal(pagamentoInCorso("cus_1", [], [sess({ status: "open", payment_status: "unpaid" })]), false);
  assert.equal(pagamentoInCorso("cus_1", [], [sess({ customer: "cus_2", status: "complete", payment_status: "unpaid" })]), false);
});

test("pagamentoInCorso: un pagamento lento fallito (abbonamento finito) non blocca per sempre", () => {
  for (const status of ["incomplete_expired", "canceled", "unpaid"]) {
    assert.equal(pagamentoInCorso("cus_1", [], [sess({ status: "complete", payment_status: "unpaid", subscription: { status } })]), false);
  }
});

test("sessioniDaScadere: solo le aperte del cliente, non quella con la stessa chiave", () => {
  const s = [
    sess({ id: "cs_a" }),
    sess({ id: "cs_b", customer: "cus_2" }),
    sess({ id: "cs_c", status: "complete" }),
    sess({ id: "cs_d", metadata: { chiave: "k1" } }),
    sess({ id: "cs_e", metadata: { chiave: "k0" } }),
  ];
  assert.deepEqual(sessioniDaScadere("cus_1", s, "k1"), ["cs_a", "cs_e"]);
});

test("chiaveCheckout: azienda, periodo, moduli in ordine e minuto", () => {
  const m = Date.UTC(2026, 10, 22, 15, 30, 10);
  assert.equal(chiaveCheckout("az1", "anno", ["vendite", "magazzino", "ambiente"], m), chiaveCheckout("az1", "anno", ["ambiente", "vendite", "magazzino"], m + 40_000));
  assert.notEqual(chiaveCheckout("az1", "anno", ["magazzino"], m), chiaveCheckout("az1", "anno", ["magazzino"], m + 60_000));
  assert.notEqual(chiaveCheckout("az1", "anno", ["magazzino"], m), chiaveCheckout("az1", "mese", ["magazzino"], m));
  assert.notEqual(chiaveCheckout("az1", "anno", ["magazzino"], m), chiaveCheckout("az2", "anno", ["magazzino"], m));
});

test("origineRitorno: prima l'Origin della richiesta, poi INDIRIZZO_GESTIONALE, poi l'indirizzo della richiesta", () => {
  // Il titolare usa il gestionale dal tunnel: Stripe lo riporta lì, dove ha il cookie
  assert.equal(origineRitorno("https://demo.esempio.it", "http://localhost:3210", "http://localhost:3210/api/abbonamento/checkout"), "https://demo.esempio.it");
  assert.equal(origineRitorno("http://192.168.1.100:3210", undefined, "http://192.168.1.100:3210/api/x"), "http://192.168.1.100:3210");
  // Senza Origin: l'indirizzo fisso, senza barre in fondo
  assert.equal(origineRitorno(null, "https://gestionale.esempio.it//", "http://localhost:3210/api/x"), "https://gestionale.esempio.it");
  assert.equal(origineRitorno(null, "  ", "http://localhost:3210/api/x"), "http://localhost:3210");
  assert.equal(origineRitorno(null, undefined, "http://localhost:3210/api/x?a=1"), "http://localhost:3210");
  // Origin non valido ("null", altro schema, testo): non si usa
  assert.equal(origineRitorno("null", "https://g.esempio.it", "http://localhost:3210/api/x"), "https://g.esempio.it");
  assert.equal(origineRitorno("javascript:alert(1)", undefined, "http://localhost:3210/api/x"), "http://localhost:3210");
  assert.equal(origineRitorno("", undefined, "http://localhost:3210/api/x"), "http://localhost:3210");
});

test("eventoDiUnAltroAmbiente: livemode deve andare con la modalità (live ⇔ livemode vero)", () => {
  assert.equal(eventoDiUnAltroAmbiente(false, "prova"), false);
  assert.equal(eventoDiUnAltroAmbiente(true, "live"), false);
  assert.equal(eventoDiUnAltroAmbiente(true, "prova"), true);
  assert.equal(eventoDiUnAltroAmbiente(false, "live"), true);
  // Spento: lo decide la route (503, Stripe ritenta quando la chiave c'è)
  assert.equal(eventoDiUnAltroAmbiente(true, "spenta"), false);
  assert.equal(eventoDiUnAltroAmbiente(false, "spenta"), false);
});
