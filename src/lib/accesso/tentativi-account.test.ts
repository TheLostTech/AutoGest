import { test } from "node:test";
import assert from "node:assert/strict";
import { ACCOUNT_BLOCCO_MS, ACCOUNT_ERRORI_MAX, ACCOUNT_FINESTRA_MS, accountBloccato, chiaveAccount, daRicordare, dopoPasswordSbagliata, type StatoAccount } from "./tentativi-account.ts";

const ORA = 1_800_000_000_000;

function sbaglia(n: number, da = ORA, passo = 1000): { s: StatoAccount | undefined; bloccatoAl: number | null } {
  let s: StatoAccount | undefined;
  let bloccatoAl: number | null = null;
  for (let i = 0; i < n; i++) {
    const r = dopoPasswordSbagliata(s, da + i * passo);
    s = r.stato;
    if (r.appenaBloccato) bloccatoAl = i + 1;
  }
  return { s, bloccatoAl };
}

test("9 password sbagliate: non bloccato; la decima blocca l'account per 15 minuti", () => {
  const nove = sbaglia(ACCOUNT_ERRORI_MAX - 1);
  assert.equal(accountBloccato(nove.s, ORA + 10_000), false);
  const dieci = sbaglia(ACCOUNT_ERRORI_MAX);
  assert.equal(dieci.bloccatoAl, ACCOUNT_ERRORI_MAX);
  const fine = ORA + (ACCOUNT_ERRORI_MAX - 1) * 1000;
  assert.equal(accountBloccato(dieci.s, fine + 1), true);
  assert.equal(accountBloccato(dieci.s, fine + ACCOUNT_BLOCCO_MS - 1), true);
  assert.equal(accountBloccato(dieci.s, fine + ACCOUNT_BLOCCO_MS), false);
});

test("errori più vecchi di 15 minuti non contano (cambiare IP non serve, aspettare sì)", () => {
  const lenti = sbaglia(ACCOUNT_ERRORI_MAX * 2, ORA, ACCOUNT_FINESTRA_MS / (ACCOUNT_ERRORI_MAX - 1) + 1000);
  assert.equal(lenti.bloccatoAl, null);
});

test("durante il blocco altri errori non lo allungano e non lo ri-segnalano", () => {
  const { s } = sbaglia(ACCOUNT_ERRORI_MAX);
  const r = dopoPasswordSbagliata(s, ORA + 60_000);
  assert.equal(r.appenaBloccato, false);
  assert.equal(r.stato.bloccatoFino, s!.bloccatoFino);
});

test("chiave per email senza maiuscole e spazi; stato dimenticabile senza errori recenti", () => {
  assert.equal(chiaveAccount("  Mario@Esempio.IT "), "mario@esempio.it");
  assert.equal(chiaveAccount(""), null);
  assert.equal(chiaveAccount(42), null);
  const uno = dopoPasswordSbagliata(undefined, ORA).stato;
  assert.equal(daRicordare(uno, ORA + 1000), true);
  assert.equal(daRicordare(uno, ORA + ACCOUNT_FINESTRA_MS + 1), false);
});
