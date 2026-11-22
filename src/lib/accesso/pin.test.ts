import { test } from "node:test";
import assert from "node:assert/strict";
import {
  bloccoAttivo,
  dopoTentativo,
  pinValido,
  PIN_BLOCCHI_DISATTIVA,
  PIN_BLOCCO_UTENTE_MS,
  PIN_ERRORI_DISPOSITIVO,
  PIN_ERRORI_DISPOSITIVO_GIORNO,
  PIN_ERRORI_UTENTE,
  PIN_FINESTRA_DISPOSITIVO_MS,
  PIN_GIORNO_MS,
  type StatoPinDispositivo,
  type StatoPinUtente,
} from "./pin.ts";

const ORA = 1_800_000_000_000;
const MIN = 60_000;
const ORA_MS = 3_600_000;
const utenteLibero = (): StatoPinUtente => ({ errori: 0, bloccatoFino: null, blocchi: [], disattivato: false });
const dispLibero = (): StatoPinDispositivo => ({ errori: [], bloccato: false });
const libero = () => ({ utente: utenteLibero(), dispositivo: dispLibero() });

// Cinque errori di fila su un nome a partire da `da`: restituisce lo stato dopo il quinto
function cicloDiBlocco(s: { utente: StatoPinUtente; dispositivo: StatoPinDispositivo }, da: number) {
  let r = { ...s, esito: "ok" as string };
  for (let i = 0; i < 5; i++) r = dopoTentativo(r, false, da + i);
  return r;
}

test("costanti", () => {
  assert.equal(PIN_ERRORI_UTENTE, 5);
  assert.equal(PIN_BLOCCO_UTENTE_MS, 900_000);
  assert.equal(PIN_ERRORI_DISPOSITIVO, 20);
  assert.equal(PIN_FINESTRA_DISPOSITIVO_MS, 900_000);
  assert.equal(PIN_ERRORI_DISPOSITIVO_GIORNO, 50);
  assert.equal(PIN_GIORNO_MS, 86_400_000);
  assert.equal(PIN_BLOCCHI_DISATTIVA, 3);
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
  const r = cicloDiBlocco(libero(), ORA);
  assert.equal(r.esito, "sbagliato");
  assert.equal(r.utente.bloccatoFino, ORA + 4 + 900_000);
  assert.deepEqual(r.utente.blocchi, [ORA + 4]);
  assert.equal(r.utente.disattivato, false);
  const sesto = dopoTentativo(r, true, ORA + 5);
  assert.equal(sesto.esito, "utente-bloccato");
  assert.deepEqual(sesto.utente, r.utente); // il PIN non si valuta: niente cambia
  assert.deepEqual(sesto.dispositivo, r.dispositivo);
  // Scaduto il blocco il PIN giusto entra e azzera gli errori (il ciclo di blocco resta contato)
  const dopo = dopoTentativo(r, true, ORA + 4 + 900_000 + 1);
  assert.equal(dopo.esito, "ok");
  assert.equal(dopo.utente.errori, 0);
  assert.equal(dopo.utente.bloccatoFino, null);
  assert.deepEqual(dopo.utente.blocchi, [ORA + 4]);
});

test("dopo il blocco scaduto un errore riparte da 1", () => {
  const s = { ...libero(), utente: { ...utenteLibero(), errori: 5, bloccatoFino: ORA, blocchi: [ORA - 900_000] } };
  const r = dopoTentativo(s, false, ORA + 1);
  assert.equal(r.esito, "sbagliato");
  assert.equal(r.utente.errori, 1);
  assert.equal(r.utente.bloccatoFino, null);
});

test("3 cicli di blocco in un giorno disattivano il PIN fino al reset", () => {
  let s = libero();
  let r = cicloDiBlocco(s, ORA);
  r = cicloDiBlocco(r, ORA + 2 * ORA_MS);
  assert.equal(r.utente.disattivato, false);
  r = cicloDiBlocco(r, ORA + 4 * ORA_MS);
  assert.equal(r.utente.disattivato, true);
  assert.equal(r.utente.blocchi.length, 3);
  // Anche passato il quarto d'ora, e anche col PIN giusto: resta bloccato
  s = r;
  for (const t of [ORA + 4 * ORA_MS + 20 * MIN, ORA + 30 * ORA_MS, ORA + 365 * 24 * ORA_MS]) {
    const x = dopoTentativo(s, true, t);
    assert.equal(x.esito, "utente-bloccato");
    assert.equal(bloccoAttivo(s, t), "utente-bloccato");
  }
});

test("cicli di blocco più vecchi di 24 ore non contano", () => {
  let r = cicloDiBlocco(libero(), ORA);
  r = cicloDiBlocco(r, ORA + 10 * ORA_MS);
  // Il terzo blocco scatta 24 h + 1 ms dopo il primo (ORA + 4): restano solo 2 cicli nella finestra
  r = cicloDiBlocco(r, ORA + PIN_GIORNO_MS + 1);
  assert.equal(r.utente.disattivato, false);
  assert.deepEqual(r.utente.blocchi, [ORA + 10 * ORA_MS + 4, ORA + PIN_GIORNO_MS + 5]);
  assert.equal(dopoTentativo(r, true, ORA + PIN_GIORNO_MS + 20 * MIN).esito, "ok");
});

test("20 errori su nomi diversi in 14 minuti bloccano il dispositivo", () => {
  let disp = dispLibero();
  const passo = Math.floor((14 * MIN) / 19);
  for (let i = 0; i < 20; i++) {
    const r = dopoTentativo({ utente: utenteLibero(), dispositivo: disp }, false, ORA + i * passo);
    assert.equal(r.esito, "sbagliato");
    disp = r.dispositivo;
    assert.equal(disp.bloccato, i === 19);
  }
  const dopo = dopoTentativo({ utente: utenteLibero(), dispositivo: disp }, true, ORA + 20 * passo);
  assert.equal(dopo.esito, "dispositivo-bloccato");
  assert.deepEqual(dopo.dispositivo, disp);
  // Il blocco del dispositivo non scade da solo
  assert.equal(dopoTentativo({ utente: utenteLibero(), dispositivo: disp }, true, ORA + 86_400_000).esito, "dispositivo-bloccato");
});

test("20 errori sparsi in 30 minuti non bloccano il dispositivo", () => {
  let disp = dispLibero();
  const passo = Math.floor((30 * MIN) / 19);
  for (let i = 0; i < 20; i++) disp = dopoTentativo({ utente: utenteLibero(), dispositivo: disp }, false, ORA + i * passo).dispositivo;
  assert.equal(disp.bloccato, false);
});

test("50 errori sparsi in 20 ore bloccano il dispositivo", () => {
  let disp = dispLibero();
  const passo = Math.floor((20 * ORA_MS) / 49); // ~24 minuti: mai 20 in un quarto d'ora
  for (let i = 0; i < 50; i++) {
    disp = dopoTentativo({ utente: utenteLibero(), dispositivo: disp }, false, ORA + i * passo).dispositivo;
    assert.equal(disp.bloccato, i === 49, `tentativo ${i + 1}`);
  }
  assert.equal(dopoTentativo({ utente: utenteLibero(), dispositivo: disp }, true, ORA + 50 * passo).esito, "dispositivo-bloccato");
});

test("50 errori in più di 24 ore non bloccano il dispositivo; gli istanti più vecchi di un giorno si scartano", () => {
  let disp = dispLibero();
  const passo = Math.floor((30 * ORA_MS) / 49);
  for (let i = 0; i < 50; i++) disp = dopoTentativo({ utente: utenteLibero(), dispositivo: disp }, false, ORA + i * passo).dispositivo;
  assert.equal(disp.bloccato, false);
  const ultimo = ORA + 49 * passo;
  assert.ok(disp.errori.every((t) => ultimo - t < PIN_GIORNO_MS));
  assert.ok(disp.errori.length < 50);
});

test("un PIN giusto non cancella gli errori del dispositivo", () => {
  const s = { ...libero(), dispositivo: { errori: [ORA - 1000, ORA - 500], bloccato: false } };
  const r = dopoTentativo(s, true, ORA);
  assert.equal(r.esito, "ok");
  assert.deepEqual(r.dispositivo.errori, [ORA - 1000, ORA - 500]);
});

test("dispositivo bloccato vince sul nome bloccato o disattivato", () => {
  const s = { utente: { ...utenteLibero(), errori: 5, bloccatoFino: ORA + 1000 }, dispositivo: { errori: [], bloccato: true } };
  assert.equal(dopoTentativo(s, true, ORA).esito, "dispositivo-bloccato");
  assert.equal(bloccoAttivo(s, ORA), "dispositivo-bloccato");
  assert.equal(bloccoAttivo({ ...s, dispositivo: dispLibero() }, ORA), "utente-bloccato");
  assert.equal(bloccoAttivo({ utente: { ...utenteLibero(), disattivato: true }, dispositivo: dispLibero() }, ORA), "utente-bloccato");
  assert.equal(bloccoAttivo(libero(), ORA), null);
});
