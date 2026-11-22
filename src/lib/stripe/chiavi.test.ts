import { test } from "node:test";
import assert from "node:assert/strict";
import { aziendaDaEvento, daSincronizzare, etichettaStripe, modalitaDaChiave } from "./chiavi.ts";

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
