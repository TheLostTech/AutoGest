// Registrazione del titolare: controllo dei campi e limite per indirizzo. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { registrazioneConsentita, validaRegistrazione } from "./registrazione.ts";

const buono = { azienda: "Rossi Autodemolizioni", nome: "Mario Rossi", email: "mario@rossi.it", password: "unapassword", invito: "ABCD-EFGH-JKLM", condizioni: true };

const errore = (corpo: unknown) => {
  const r = validaRegistrazione(corpo);
  assert.ok("errore" in r, JSON.stringify(corpo));
  return r.errore;
};

test("validaRegistrazione accetta un corpo buono", () => {
  const r = validaRegistrazione(buono);
  assert.ok("ok" in r);
  assert.deepEqual(r.ok, buono);
});

test("validaRegistrazione: nome dell'azienda da 2 a 80 caratteri", () => {
  assert.match(errore({ ...buono, azienda: "R" }), /azienda/);
  assert.match(errore({ ...buono, azienda: "x".repeat(81) }), /azienda/);
  assert.match(errore({ ...buono, azienda: 5 }), /azienda/);
  const r = validaRegistrazione({ ...buono, azienda: "  Ro  " });
  assert.ok("ok" in r && r.ok.azienda === "Ro");
});

test("validaRegistrazione: nome e cognome obbligatori", () => {
  assert.match(errore({ ...buono, nome: "" }), /nome/i);
  assert.match(errore({ ...buono, nome: "   " }), /nome/i);
});

test("validaRegistrazione: email con @, in minuscolo e senza spazi ai lati", () => {
  assert.match(errore({ ...buono, email: "mario.rossi.it" }), /email/i);
  assert.match(errore({ ...buono, email: "" }), /email/i);
  const r = validaRegistrazione({ ...buono, email: "  Mario@Rossi.IT " });
  assert.ok("ok" in r && r.ok.email === "mario@rossi.it");
});

test("validaRegistrazione: password di almeno 10 caratteri", () => {
  assert.equal(errore({ ...buono, password: "123456789" }), "La password deve avere almeno 10 caratteri.");
  const r = validaRegistrazione({ ...buono, password: "1234567890" });
  assert.ok("ok" in r);
});

test("validaRegistrazione: condizioni da accettare", () => {
  assert.match(errore({ ...buono, condizioni: false }), /condizioni/);
  assert.match(errore({ ...buono, condizioni: "true" }), /condizioni/);
  const { condizioni: _, ...senza } = buono;
  void _;
  assert.match(errore(senza), /condizioni/);
});

test("validaRegistrazione: codice invito di formato sbagliato", () => {
  for (const invito of ["", "ABCD", "ABCD-EFGH-JKL0", 12]) assert.equal(errore({ ...buono, invito }), "Codice invito non valido", String(invito));
  const r = validaRegistrazione({ ...buono, invito: " abcd efgh jklm " });
  assert.ok("ok" in r && r.ok.invito === "ABCD-EFGH-JKLM");
});

test("validaRegistrazione: corpo mancante o non oggetto", () => {
  for (const c of [null, undefined, "x", 3, []]) assert.ok("errore" in validaRegistrazione(c));
});

test("registrazioneConsentita: tre all'ora per indirizzo", () => {
  const t = 1_000_000_000;
  assert.equal(registrazioneConsentita("198.51.100.1", t), true);
  assert.equal(registrazioneConsentita("198.51.100.1", t + 1000), true);
  assert.equal(registrazioneConsentita("198.51.100.1", t + 2000), true);
  assert.equal(registrazioneConsentita("198.51.100.1", t + 3000), false);
  // Un altro indirizzo ha il suo contatore
  assert.equal(registrazioneConsentita("198.51.100.2", t + 3000), true);
  // Dopo 61 minuti la finestra è passata
  assert.equal(registrazioneConsentita("198.51.100.1", t + 61 * 60_000), true);
});

test("registrazioneConsentita: senza indirizzo un contatore comune", () => {
  const t = 2_000_000_000;
  assert.equal(registrazioneConsentita(null, t), true);
  assert.equal(registrazioneConsentita(null, t + 1), true);
  assert.equal(registrazioneConsentita(null, t + 2), true);
  assert.equal(registrazioneConsentita(null, t + 3), false);
  assert.equal(registrazioneConsentita("198.51.100.9", t + 3), true);
});
