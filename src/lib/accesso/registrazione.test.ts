// Registrazione del titolare: controllo dei campi e limite per indirizzo. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { registrazioneConsentita, validaRegistrazione } from "./registrazione.ts";

const buono = { azienda: "Rossi Autodemolizioni", nome: "Mario Rossi", email: "mario@rossi.it", password: "unapassword", telefono: "+39 333 1234567", condizioni: true, clausole: true, commerciale: true };

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

test("validaRegistrazione: clausole da approvare specificamente", () => {
  assert.match(errore({ ...buono, clausole: false }), /clausole/);
  assert.match(errore({ ...buono, clausole: "true" }), /clausole/);
  const { clausole: _, ...senza } = buono;
  void _;
  assert.match(errore(senza), /clausole/);
});

test("validaRegistrazione: senza codice invito, e un invito mandato lo stesso non conta", () => {
  const r = validaRegistrazione({ ...buono, invito: "ABCD" });
  assert.ok("ok" in r);
  assert.deepEqual(r.ok, buono);
  assert.equal("invito" in r.ok, false);
});

test("validaRegistrazione: telefono facoltativo, vuoto o assente diventa null", () => {
  for (const telefono of ["", "   ", undefined, null]) {
    const r = validaRegistrazione({ ...buono, telefono });
    assert.ok("ok" in r && r.ok.telefono === null, String(telefono));
  }
  const r = validaRegistrazione({ ...buono, telefono: "  0471 123456 " });
  assert.ok("ok" in r && r.ok.telefono === "0471 123456");
});

test("validaRegistrazione: telefono solo cifre, spazi e +, da 6 a 20 caratteri, almeno 6 cifre", () => {
  const msg = "Scrivi un numero di telefono valido o lascia vuoto.";
  for (const telefono of ["abc", "333-1234567", "12345", "1".repeat(21), 333123456, "+39 (333) 12", "++++++", "+ 1 2 3", "12 34 5"]) assert.equal(errore({ ...buono, telefono }), msg, String(telefono));
  for (const telefono of ["123456", "1".repeat(20), "+393331234567", "+1 23 456"]) assert.ok("ok" in validaRegistrazione({ ...buono, telefono }), telefono);
});

test("validaRegistrazione: consenso commerciale facoltativo, solo true lo dà", () => {
  const { commerciale: _, ...senza } = buono;
  void _;
  const r = validaRegistrazione(senza);
  assert.ok("ok" in r && r.ok.commerciale === false);
  for (const commerciale of [false, "true", 1]) {
    const x = validaRegistrazione({ ...buono, commerciale });
    assert.ok("ok" in x && x.ok.commerciale === false, String(commerciale));
  }
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

test("validaRegistrazione: niente numeri, indirizzi web o email nel nome del titolare (finisce nelle email)", () => {
  for (const nome of ["Chiama 3331234567", "Mario 2", "vai su evil.example.com", "Mario www.rossi", "https://x.it", "mario@rossi.it", "Conto sospeso rossi.it", "vai su evil . example", "evil．example", "evil。example", "ｅｖｉｌ.ｅｘａｍｐｌｅ", "verifica-conto.ai", "evil[.]ws"]) {
    assert.match(errore({ ...buono, nome }), /titolare/, nome);
  }
  for (const nome of ["Mario Rossi", "D'Angelo Maria", "Anna-Maria De Luca", "F. Bianchi", "Ñúñez José", "Rossi M."]) {
    assert.ok("ok" in validaRegistrazione({ ...buono, nome }), nome);
  }
});

test("validaRegistrazione: niente indirizzi web o email nel nome dell'azienda", () => {
  for (const azienda of ["Vai su https://evil.example.com", "www.rossi", "https://x.it", "info@rossi.it"]) {
    assert.match(errore({ ...buono, azienda }), /azienda/, azienda);
  }
  for (const azienda of ["Autodemolizioni 2000 S.r.l.", "F.lli Rossi s.n.c.", "Rossi & C.", "SI.ME. srl", "DE.CO. Ricambi", "Ricambi-Auto.it"]) {
    assert.ok("ok" in validaRegistrazione({ ...buono, azienda }), azienda);
  }
});
