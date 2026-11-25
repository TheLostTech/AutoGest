import { test } from "node:test";
import assert from "node:assert/strict";
import { EMAIL_CONFERMATA, esitoRimando, linkConferma, richiestaConferma } from "./conferma.ts";

test("testo della conferma riuscita", () => {
  assert.equal(EMAIL_CONFERMATA, "Email confermata: la prova di 15 giorni è iniziata.");
});

test("link dell'email: alla nostra pagina /conferma con il gettone", () => {
  assert.equal(linkConferma("a.b-c_d", null, { BETTER_AUTH_URL: "https://app.piazzale.it/" }), "https://app.piazzale.it/conferma?token=a.b-c_d");
  assert.equal(linkConferma("x y", null, { VERCEL: "1", VERCEL_URL: "d.vercel.app" }), "https://d.vercel.app/conferma?token=x%20y");
  // In locale (non produzione) l'indirizzo si prende dalla richiesta
  assert.equal(linkConferma("t", "http://localhost:3000", { NODE_ENV: "development" }), "http://localhost:3000/conferma?token=t");
  assert.throws(() => linkConferma("t", null, {}), /Indirizzo/);
});

test("link dell'email: in produzione fuori da Vercel serve BETTER_AUTH_URL, mai l'host della richiesta", () => {
  assert.throws(() => linkConferma("t", "https://host-scelto-dal-cliente.it", { NODE_ENV: "production" }), {
    message: "Indirizzo pubblico non configurato: imposta BETTER_AUTH_URL",
  });
  assert.equal(linkConferma("t", "https://altro.it", { NODE_ENV: "production", BETTER_AUTH_URL: "https://app.piazzale.it" }), "https://app.piazzale.it/conferma?token=t");
});

test("richiesta di conferma: gettone e password", () => {
  assert.deepEqual(richiestaConferma({ token: " abc ", password: "segreta-123" }), { token: "abc", password: "segreta-123" });
  for (const corpo of [null, {}, { token: "abc" }, { password: "x" }, { token: "", password: "x" }, { token: 1, password: "x" }, { token: "a", password: "" }, { token: "a".repeat(5000), password: "x" }, { token: "a", password: "p".repeat(129) }]) {
    assert.equal(richiestaConferma(corpo), null, JSON.stringify(corpo)?.slice(0, 60));
  }
});

test("esito del rimando", () => {
  assert.equal(esitoRimando(200).tono, "ok");
  assert.ok(esitoRimando(429).testo.includes("troppe"));
  assert.ok(esitoRimando(0).testo.includes("rete"));
  assert.equal(esitoRimando(500).tono, "danger");
});
