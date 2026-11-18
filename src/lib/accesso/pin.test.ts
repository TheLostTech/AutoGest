import { test } from "node:test";
import assert from "node:assert/strict";
import {
  bloccoAttivo,
  dopoTentativo,
  pinValido,
  PIN_BLOCCO_UTENTE_MS,
  PIN_ERRORI_DISPOSITIVO,
  PIN_ERRORI_UTENTE,
  PIN_FINESTRA_DISPOSITIVO_MS,
  type StatoPinDispositivo,
  type StatoPinUtente,
} from "./pin.ts";

const ORA = 1_800_000_000_000;
const libero = (): { utente: StatoPinUtente; dispositivo: StatoPinDispositivo } => ({
  utente: { errori: 0, bloccatoFino: null },
  dispositivo: { errori: [], bloccato: false },
});

test("costanti", () => {
  assert.equal(PIN_ERRORI_UTENTE, 5);
  assert.equal(PIN_BLOCCO_UTENTE_MS, 900_000);
  assert.equal(PIN_ERRORI_DISPOSITIVO, 20);
  assert.equal(PIN_FINESTRA_DISPOSITIVO_MS, 900_000);
});

test("pinValido: solo 4 cifre", () => {
  assert.equal(pinValido("0123"), true);
  assert.equal(pinValido("123"), false);
  assert.equal(pinValido("12a4"), false);
  assert.equal(pinValido("12345"), false);
  assert.equal(pinValido(" 1234"), false);
  assert.equal(pinValido("١٢٣٤"), false); // cifre non latine
});

test("4 errori poi PIN giusto: ok ed errori a zero", () => {
  let s = libero();
  for (let i = 0; i < 4; i++) {
    const r = dopoTentativo(s, false, ORA + i);
    assert.equal(r.esito, "sbagliato");
    s = r;
  }
  assert.equal(s.utente.errori, 4);
  const r = dopoTentativo(s, true, ORA + 10);
  assert.equal(r.esito, "ok");
  assert.equal(r.utente.errori, 0);
  assert.equal(r.utente.bloccatoFino, null);
});

test("5 errori bloccano il nome per 15 minuti, anche col PIN giusto", () => {
  let s = libero();
  let r = dopoTentativo(s, false, ORA);
  for (let i = 1; i < 5; i++) {
    s = r;
    r = dopoTentativo(s, false, ORA + i);
  }
  assert.equal(r.esito, "sbagliato");
  assert.equal(r.utente.bloccatoFino, ORA + 4 + 900_000);
  const sesto = dopoTentativo(r, true, ORA + 5);
  assert.equal(sesto.esito, "utente-bloccato");
  assert.deepEqual(sesto.utente, r.utente); // il PIN non si valuta: niente cambia
  assert.deepEqual(sesto.dispositivo, r.dispositivo);
  // Scaduto il blocco il PIN giusto entra e azzera
  const dopo = dopoTentativo(r, true, ORA + 4 + 900_000 + 1);
  assert.equal(dopo.esito, "ok");
  assert.equal(dopo.utente.errori, 0);
  assert.equal(dopo.utente.bloccatoFino, null);
});

test("dopo il blocco scaduto un errore riparte da 1", () => {
  const s = { ...libero(), utente: { errori: 5, bloccatoFino: ORA } };
  const r = dopoTentativo(s, false, ORA + 1);
  assert.equal(r.esito, "sbagliato");
  assert.equal(r.utente.errori, 1);
  assert.equal(r.utente.bloccatoFino, null);
});

test("20 errori su nomi diversi in 14 minuti bloccano il dispositivo", () => {
  let disp: StatoPinDispositivo = { errori: [], bloccato: false };
  const passo = Math.floor((14 * 60_000) / 19);
  for (let i = 0; i < 20; i++) {
    const r = dopoTentativo({ utente: { errori: 0, bloccatoFino: null }, dispositivo: disp }, false, ORA + i * passo);
    assert.equal(r.esito, "sbagliato");
    disp = r.dispositivo;
    assert.equal(disp.bloccato, i === 19);
  }
  const dopo = dopoTentativo({ utente: { errori: 0, bloccatoFino: null }, dispositivo: disp }, true, ORA + 20 * passo);
  assert.equal(dopo.esito, "dispositivo-bloccato");
  assert.deepEqual(dopo.dispositivo, disp);
  // Il blocco del dispositivo non scade da solo
  assert.equal(dopoTentativo({ utente: { errori: 0, bloccatoFino: null }, dispositivo: disp }, true, ORA + 86_400_000).esito, "dispositivo-bloccato");
});

test("20 errori sparsi in 30 minuti non bloccano il dispositivo", () => {
  let disp: StatoPinDispositivo = { errori: [], bloccato: false };
  const passo = Math.floor((30 * 60_000) / 19);
  for (let i = 0; i < 20; i++) {
    const r = dopoTentativo({ utente: { errori: 0, bloccatoFino: null }, dispositivo: disp }, false, ORA + i * passo);
    disp = r.dispositivo;
  }
  assert.equal(disp.bloccato, false);
  assert.ok(disp.errori.length < 20);
  assert.ok(disp.errori.every((t) => t > ORA + 19 * passo - 900_000));
});

test("un PIN giusto non cancella gli errori del dispositivo", () => {
  const s = { ...libero(), dispositivo: { errori: [ORA - 1000, ORA - 500], bloccato: false } };
  const r = dopoTentativo(s, true, ORA);
  assert.equal(r.esito, "ok");
  assert.deepEqual(r.dispositivo.errori, [ORA - 1000, ORA - 500]);
});

test("dispositivo bloccato vince sul nome bloccato", () => {
  const s = { utente: { errori: 5, bloccatoFino: ORA + 1000 }, dispositivo: { errori: [], bloccato: true } };
  assert.equal(dopoTentativo(s, true, ORA).esito, "dispositivo-bloccato");
  assert.equal(bloccoAttivo(s, ORA), "dispositivo-bloccato");
  assert.equal(bloccoAttivo({ ...s, dispositivo: { errori: [], bloccato: false } }, ORA), "utente-bloccato");
  assert.equal(bloccoAttivo(libero(), ORA), null);
});
