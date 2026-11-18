import { test } from "node:test";
import assert from "node:assert/strict";
import { ACCOUNT_BLOCCO_MS, ACCOUNT_ERRORI_MAX, ACCOUNT_FINESTRA_MS, IN_VOLO_MS, accountBloccato, chiaveAccount, chiudi, prenota, type Conti } from "./tentativi-account.ts";

const ORA = 1_800_000_000_000;
const K = "mario@esempio.it";

/** n tentativi uno dopo l'altro, tutti con password sbagliata. Restituisce a quale si è bloccato (o null). */
function sbaglia(conti: Conti, n: number, da = ORA, passo = 1000): number | null {
  let bloccatoAl: number | null = null;
  for (let i = 0; i < n; i++) {
    const t = da + i * passo;
    if (prenota(conti, K, t) !== "ok") continue;
    if (chiudi(conti, K, t, "sbagliata")) bloccatoAl = i + 1;
  }
  return bloccatoAl;
}

test("9 password sbagliate: si entra ancora; la decima blocca l'account per 15 minuti, anche con la password giusta", () => {
  const c: Conti = new Map();
  assert.equal(sbaglia(c, ACCOUNT_ERRORI_MAX - 1), null);
  assert.equal(prenota(c, K, ORA + 20_000), "ok");
  chiudi(c, K, ORA + 20_000, "altro");
  const d: Conti = new Map();
  assert.equal(sbaglia(d, ACCOUNT_ERRORI_MAX), ACCOUNT_ERRORI_MAX);
  const fine = ORA + (ACCOUNT_ERRORI_MAX - 1) * 1000;
  assert.equal(prenota(d, K, fine + 1), "bloccato");
  assert.equal(accountBloccato(d.get(K), fine + ACCOUNT_BLOCCO_MS - 1), true);
  assert.equal(prenota(d, K, fine + ACCOUNT_BLOCCO_MS), "ok");
});

test("errori più vecchi di 15 minuti non contano (cambiare IP non serve, aspettare sì)", () => {
  const c: Conti = new Map();
  assert.equal(sbaglia(c, ACCOUNT_ERRORI_MAX * 2, ORA, ACCOUNT_FINESTRA_MS / (ACCOUNT_ERRORI_MAX - 1) + 1000), null);
});

test("20 tentativi in parallelo sullo stesso account: al massimo 10 arrivano alla verifica della password", () => {
  const c: Conti = new Map();
  const esiti = Array.from({ length: 20 }, () => prenota(c, K, ORA));
  assert.equal(esiti.filter((e) => e === "ok").length, ACCOUNT_ERRORI_MAX);
  assert.ok(esiti.slice(ACCOUNT_ERRORI_MAX).every((e) => e === "bloccato"));
  // Con 5 errori già registrati ne passano solo altri 5
  const d: Conti = new Map();
  sbaglia(d, 5);
  const altri = Array.from({ length: 20 }, () => prenota(d, K, ORA + 10_000));
  assert.equal(altri.filter((e) => e === "ok").length, ACCOUNT_ERRORI_MAX - 5);
});

test("prenotazioni senza esito (errore del server) scadono da sole", () => {
  const c: Conti = new Map();
  for (let i = 0; i < ACCOUNT_ERRORI_MAX; i++) prenota(c, K, ORA);
  assert.equal(prenota(c, K, ORA + 1), "bloccato");
  assert.equal(prenota(c, K, ORA + IN_VOLO_MS + 1), "ok");
});

test("inondare il server di email a caso non libera un account con errori o bloccato; da pieno le email nuove si rifiutano", () => {
  const c: Conti = new Map();
  const MAX = 50;
  // Account bersaglio con 9 errori, un altro bloccato
  for (let i = 0; i < 9; i++) {
    prenota(c, K, ORA, MAX);
    chiudi(c, K, ORA, "sbagliata");
  }
  for (let i = 0; i < ACCOUNT_ERRORI_MAX; i++) {
    prenota(c, "bloccato@esempio.it", ORA, MAX);
    chiudi(c, "bloccato@esempio.it", ORA, "sbagliata");
  }
  // Migliaia di email a caso, ognuna con un errore
  const esiti: string[] = [];
  for (let i = 0; i < 2000; i++) {
    const k = `caso${i}@x.it`;
    const e = prenota(c, k, ORA + 1, MAX);
    esiti.push(e);
    if (e === "ok") chiudi(c, k, ORA + 1, "sbagliata");
  }
  assert.ok(c.size <= MAX);
  assert.ok(esiti.includes("pieno"));
  assert.equal(c.get(K)?.errori.length, 9, "il conto del bersaglio resta");
  assert.equal(prenota(c, "bloccato@esempio.it", ORA + 2, MAX), "bloccato");
  // Il decimo errore del bersaglio lo blocca comunque
  assert.equal(prenota(c, K, ORA + 2, MAX), "ok");
  assert.equal(chiudi(c, K, ORA + 2, "sbagliata"), true);
  // Passati 15 minuti le voci vecchie si dimenticano e le email nuove tornano a passare
  assert.equal(prenota(c, "nuova@x.it", ORA + ACCOUNT_FINESTRA_MS + 10, MAX), "ok");
});

test("chiave per email senza maiuscole e spazi; password giusta azzera gli errori", () => {
  assert.equal(chiaveAccount("  Mario@Esempio.IT "), "mario@esempio.it");
  assert.equal(chiaveAccount(""), null);
  assert.equal(chiaveAccount(42), null);
  const c: Conti = new Map();
  sbaglia(c, 5);
  prenota(c, K, ORA + 10_000);
  chiudi(c, K, ORA + 10_000, "giusta");
  assert.equal(c.has(K), false);
});
