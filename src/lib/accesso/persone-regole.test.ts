// Regole delle persone dell'azienda (accessi dei dipendenti). Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { ALTRA_AZIENDA, cambiNegatiAltraAzienda, cambioRuoliPermesso, modificheDaCorpo, nuovoMembroDaCorpo, ruoliDaCorpo, scritturaPersoneNegata, SERVE_PASSWORD } from "./persone-regole.ts";

test("scritture sulle persone: solo con la sessione email e password", () => {
  assert.equal(scritturaPersoneNegata("password"), null);
  assert.equal(scritturaPersoneNegata("pin"), SERVE_PASSWORD);
  assert.equal(SERVE_PASSWORD, "Serve l'accesso con email e password.");
});

test("chi lavora anche per un'altra azienda: solo i ruoli di questa", () => {
  assert.equal(ALTRA_AZIENDA, "Questa persona lavora anche per un'altra azienda: chiedi all'assistenza.");
  assert.equal(cambiNegatiAltraAzienda({ ruoli: ["vendite"] }, 1), null);
  assert.equal(cambiNegatiAltraAzienda({ password: "1234567890" }, 1), ALTRA_AZIENDA);
  assert.equal(cambiNegatiAltraAzienda({ password: "1234567890", email: "a@b.it" }, 2), ALTRA_AZIENDA);
  assert.equal(cambiNegatiAltraAzienda({ pin: "1234" }, 1), ALTRA_AZIENDA);
  assert.equal(cambiNegatiAltraAzienda({ attivo: false }, 1), ALTRA_AZIENDA);
  assert.equal(cambiNegatiAltraAzienda({ attivo: true }, 1), ALTRA_AZIENDA);
  assert.equal(cambiNegatiAltraAzienda({ ruoli: ["vendite"], pin: "1234" }, 1), ALTRA_AZIENDA);
  // Solo in questa azienda: tutto si può
  assert.equal(cambiNegatiAltraAzienda({ password: "1234567890", pin: "1234", attivo: false }, 0), null);
});
import type { Role } from "../types.ts";

const m = (userId: string, ruoli: Role[], sospeso = false) => ({ userId, ruoli, sospeso });

test("l'unico responsabile che toglie a sé responsabile: no", () => {
  const membri = [m("tit", ["responsabile"]), m("s1", ["smontatore"])];
  assert.equal(cambioRuoliPermesso(membri, "tit", ["smontatore"]), false);
});

test("con due responsabili: sì", () => {
  const membri = [m("tit", ["responsabile"]), m("socio", ["responsabile", "vendite"]), m("s1", ["smontatore"])];
  assert.equal(cambioRuoliPermesso(membri, "tit", ["smontatore"]), true);
  assert.equal(cambioRuoliPermesso(membri, "socio", ["vendite"]), true);
});

test("il secondo responsabile sospeso non conta", () => {
  const membri = [m("tit", ["responsabile"]), m("socio", ["responsabile"], true)];
  assert.equal(cambioRuoliPermesso(membri, "tit", ["vendite"]), false);
});

test("aggiungere ruoli vale sempre", () => {
  const membri = [m("tit", ["responsabile"]), m("s1", ["smontatore"])];
  assert.equal(cambioRuoliPermesso(membri, "s1", ["smontatore", "magazziniere"]), true);
  assert.equal(cambioRuoliPermesso(membri, "tit", ["responsabile", "vendite"]), true);
  // Anche in un'azienda che un responsabile attivo non l'ha (creata dal super admin, titolare sospeso)
  const senza = [m("tit", ["responsabile"], true), m("s1", ["smontatore"])];
  assert.equal(cambioRuoliPermesso(senza, "s1", ["smontatore", "vendite"]), true);
});

test("sospendere l'unico responsabile: no; con un altro responsabile attivo: sì", () => {
  const membri = [m("tit", ["responsabile"]), m("s1", ["smontatore"])];
  assert.equal(cambioRuoliPermesso(membri, "tit", ["responsabile"], true), false);
  assert.equal(cambioRuoliPermesso(membri, "s1", ["smontatore"], true), true);
  const due = [...membri, m("socio", ["responsabile"])];
  assert.equal(cambioRuoliPermesso(due, "tit", ["responsabile"], true), true);
});

test("riattivare un responsabile sospeso: sì", () => {
  const membri = [m("tit", ["responsabile"]), m("socio", ["responsabile"], true)];
  assert.equal(cambioRuoliPermesso(membri, "socio", ["responsabile"], false), true);
});

test("ruoliDaCorpo: almeno un ruolo, tutti validi", () => {
  assert.deepEqual(ruoliDaCorpo(["vendite", "smontatore"]), ["smontatore", "vendite"]);
  assert.equal(ruoliDaCorpo([]), null);
  assert.equal(ruoliDaCorpo(["smontatore", "boh"]), null);
  assert.equal(ruoliDaCorpo("smontatore"), null);
});

test("nuovoMembroDaCorpo: solo PIN", () => {
  assert.deepEqual(nuovoMembroDaCorpo({ nome: " Luca Bianchi ", ruoli: ["smontatore"], pin: "1234" }, 10), {
    dati: { nome: "Luca Bianchi", ruoli: ["smontatore"], pin: "1234" },
  });
});

test("nuovoMembroDaCorpo: email e password, con la lunghezza minima chiesta", () => {
  const corpo = { nome: "Anna", ruoli: ["vendite"], email: " Anna@Esempio.it ", password: "123456789" };
  assert.ok("errore" in nuovoMembroDaCorpo(corpo, 10));
  const r = nuovoMembroDaCorpo({ ...corpo, password: "1234567890" }, 10);
  assert.deepEqual(r, { dati: { nome: "Anna", ruoli: ["vendite"], email: "anna@esempio.it", password: "1234567890" } });
  assert.match((nuovoMembroDaCorpo(corpo, 10) as { errore: string }).errore, /almeno 10 caratteri/);
  assert.ok("dati" in nuovoMembroDaCorpo(corpo, 8));
});

test("nuovoMembroDaCorpo: i rifiuti", () => {
  const e = (c: Record<string, unknown>) => (nuovoMembroDaCorpo(c, 10) as { errore?: string }).errore;
  assert.equal(e({ nome: "A", ruoli: ["smontatore"], pin: "1234" }), "Scrivi il nome della persona (da 2 a 80 caratteri).");
  assert.match(e({ nome: "Luca", ruoli: [], pin: "1234" }) ?? "", /^Scegli almeno un ruolo tra/);
  assert.equal(e({ nome: "Luca", ruoli: ["smontatore"], pin: "12a4" }), "Il PIN è di 4 cifre.");
  assert.equal(e({ nome: "Luca", ruoli: ["smontatore"] }), "Scegli come entra: email e password, PIN, o tutti e due.");
  assert.ok(e({ nome: "Luca", ruoli: ["smontatore"], email: "x@pin.invalid", password: "1234567890" }));
  assert.ok(e({ nome: "Luca", ruoli: ["smontatore"], email: "non-email", password: "1234567890" }));
  assert.ok(e({ nome: "Luca", ruoli: ["smontatore"], email: "a@b.it", password: "x".repeat(129) }));
});

test("modificheDaCorpo: i campi riconosciuti", () => {
  assert.deepEqual(modificheDaCorpo({ ruoli: ["vendite"] }, 10), { cambi: { ruoli: ["vendite"] } });
  assert.deepEqual(modificheDaCorpo({ pin: "0000" }, 10), { cambi: { pin: "0000" } });
  assert.deepEqual(modificheDaCorpo({ password: "1234567890", email: " Nuova@Esempio.it " }, 10), { cambi: { password: "1234567890", email: "nuova@esempio.it" } });
  assert.deepEqual(modificheDaCorpo({ attivo: false }, 10), { cambi: { attivo: false } });
});

test("modificheDaCorpo: i rifiuti", () => {
  const e = (c: Record<string, unknown>, min = 10) => (modificheDaCorpo(c, min) as { errore?: string }).errore;
  assert.equal(e({}), "Niente da modificare.");
  assert.equal(e({ ruoli: [] }), "Scegli almeno un ruolo valido.");
  assert.equal(e({ pin: "123" }), "Il PIN è di 4 cifre.");
  assert.equal(e({ password: "123456789" }), "La password deve avere almeno 10 caratteri.");
  assert.equal(e({ password: "1234567" }, 8), "La password deve avere almeno 8 caratteri.");
  assert.equal(e({ attivo: "no" }), "Richiesta non valida.");
  assert.equal(e({ password: "1234567890", email: "x@pin.invalid" }), "Email non valida.");
});
