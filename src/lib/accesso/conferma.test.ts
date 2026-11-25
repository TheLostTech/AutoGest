import { test } from "node:test";
import assert from "node:assert/strict";
import { avvisoConferma, EMAIL_CONFERMATA, esitoRimando, RITORNO_CONFERMA } from "./conferma.ts";

test("ritorno dal link: sulla pagina di accesso con confermata=1", () => {
  assert.equal(RITORNO_CONFERMA, "/accesso?confermata=1");
});

test("avviso di conferma: riuscita, scaduta, non valida, assente", () => {
  assert.deepEqual(avvisoConferma("1", undefined), { tono: "ok", testo: EMAIL_CONFERMATA });
  assert.equal(EMAIL_CONFERMATA, "Email confermata: la prova di 15 giorni è iniziata.");
  const scaduto = avvisoConferma("1", "TOKEN_EXPIRED");
  assert.equal(scaduto?.tono, "danger");
  assert.ok(scaduto?.testo.includes("scaduto"));
  for (const e of ["INVALID_TOKEN", "USER_NOT_FOUND", "qualsiasi"]) {
    const a = avvisoConferma("1", e);
    assert.equal(a?.tono, "danger");
    assert.ok(a?.testo.includes("non è valido"), e);
  }
  assert.equal(avvisoConferma(undefined, undefined), null);
  assert.equal(avvisoConferma("0", "INVALID_TOKEN"), null);
});

test("esito del rimando", () => {
  assert.equal(esitoRimando(200).tono, "ok");
  assert.ok(esitoRimando(429).testo.includes("troppe"));
  assert.ok(esitoRimando(0).testo.includes("rete"));
  assert.equal(esitoRimando(500).tono, "danger");
});
