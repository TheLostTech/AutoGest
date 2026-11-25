import { test } from "node:test";
import assert from "node:assert/strict";
import {
  ACCOUNT_BLOCCO_MS,
  ACCOUNT_ERRORI_MAX,
  ACCOUNT_FINESTRA_MS,
  IN_VOLO_MS,
  SCONOSCIUTI_FINESTRA_MS,
  SCONOSCIUTI_MAX,
  accountBloccato,
  chiaveAccount,
  chiudi,
  prenota,
  tentativoSconosciuto,
  type Conti,
} from "./tentativi-account.ts";

const ORA = 1_800_000_000_000;
const K = "u:mario";
let n = 0;
const gettone = () => `g${++n}`;

/** n tentativi uno dopo l'altro, tutti con password sbagliata. Restituisce a quale si è bloccato (o null). */
function sbaglia(conti: Conti, quanti: number, da = ORA, passo = 1000): number | null {
  let bloccatoAl: number | null = null;
  for (let i = 0; i < quanti; i++) {
    const t = da + i * passo;
    const g = gettone();
    if (prenota(conti, K, g, t) !== "ok") continue;
    if (chiudi(conti, K, g, t, "sbagliata")) bloccatoAl = i + 1;
  }
  return bloccatoAl;
}

test("9 password sbagliate: si entra ancora; la decima blocca l'account per 15 minuti, anche con la password giusta", () => {
  const c: Conti = new Map();
  assert.equal(sbaglia(c, ACCOUNT_ERRORI_MAX - 1), null);
  const g = gettone();
  assert.equal(prenota(c, K, g, ORA + 20_000), "ok");
  chiudi(c, K, g, ORA + 20_000, "altro");
  const d: Conti = new Map();
  assert.equal(sbaglia(d, ACCOUNT_ERRORI_MAX), ACCOUNT_ERRORI_MAX);
  const fine = ORA + (ACCOUNT_ERRORI_MAX - 1) * 1000;
  assert.equal(prenota(d, K, gettone(), fine + 1), "bloccato");
  assert.equal(accountBloccato(d.get(K), fine + ACCOUNT_BLOCCO_MS - 1), true);
  assert.equal(prenota(d, K, gettone(), fine + ACCOUNT_BLOCCO_MS), "ok");
});

test("errori più vecchi di 15 minuti non contano (cambiare IP non serve, aspettare sì)", () => {
  const c: Conti = new Map();
  assert.equal(sbaglia(c, ACCOUNT_ERRORI_MAX * 2, ORA, ACCOUNT_FINESTRA_MS / (ACCOUNT_ERRORI_MAX - 1) + 1000), null);
});

test("20 tentativi in parallelo sullo stesso account: al massimo 10 arrivano alla verifica della password", () => {
  const c: Conti = new Map();
  const esiti = Array.from({ length: 20 }, () => prenota(c, K, gettone(), ORA));
  assert.equal(esiti.filter((e) => e === "ok").length, ACCOUNT_ERRORI_MAX);
  const d: Conti = new Map();
  sbaglia(d, 5);
  const altri = Array.from({ length: 20 }, () => prenota(d, K, gettone(), ORA + 10_000));
  assert.equal(altri.filter((e) => e === "ok").length, ACCOUNT_ERRORI_MAX - 5);
});

test("ogni esito toglie solo il suo gettone; un gettone sconosciuto o già chiuso non conta e non libera altri", () => {
  const c: Conti = new Map();
  const gs = Array.from({ length: ACCOUNT_ERRORI_MAX }, () => gettone());
  for (const g of gs) prenota(c, K, g, ORA);
  assert.equal(prenota(c, K, gettone(), ORA), "bloccato");
  chiudi(c, K, "mai-visto", ORA, "altro");
  chiudi(c, K, gs[0], ORA, "altro");
  chiudi(c, K, gs[0], ORA, "sbagliata"); // seconda volta: niente
  assert.equal(c.get(K)!.inVolo.size, ACCOUNT_ERRORI_MAX - 1);
  assert.equal(c.get(K)!.errori.length, 0);
  assert.equal(prenota(c, K, gettone(), ORA), "ok");
});

test("gettoni rimasti senza esito (errore del server) scadono dopo 60 secondi", () => {
  const c: Conti = new Map();
  for (let i = 0; i < ACCOUNT_ERRORI_MAX; i++) prenota(c, K, gettone(), ORA);
  assert.equal(prenota(c, K, gettone(), ORA + IN_VOLO_MS - 1), "bloccato");
  assert.equal(prenota(c, K, gettone(), ORA + IN_VOLO_MS), "ok");
});

test("bloccato mentre una richiesta era in corso: resta bloccato anche se quella aveva la password giusta", () => {
  const c: Conti = new Map();
  const lento = gettone();
  prenota(c, K, lento, ORA);
  // Con il lento in corso al massimo 9 errori: il decimo posto è suo
  assert.equal(sbaglia(c, ACCOUNT_ERRORI_MAX, ORA + 1), null);
  assert.equal(c.get(K)!.errori.length, ACCOUNT_ERRORI_MAX - 1);
  // Il lento resta appeso oltre i 60 secondi: il suo posto si libera e il decimo errore blocca
  const t = ORA + IN_VOLO_MS + 10;
  const g = gettone();
  assert.equal(prenota(c, K, g, t), "ok");
  assert.equal(chiudi(c, K, g, t, "sbagliata"), true);
  // Ora arriva l'esito del lento, con la password giusta: l'account resta bloccato
  chiudi(c, K, lento, t + 1, "giusta");
  assert.equal(accountBloccato(c.get(K), t + 2), true);
  assert.equal(prenota(c, K, gettone(), t + 2), "bloccato");
});

test("email inesistenti: un solo contatore comune da 30 al minuto, che non tocca gli account veri", () => {
  const comune: number[] = [];
  const esiti = Array.from({ length: 100 }, (_, i) => tentativoSconosciuto(comune, ORA + i));
  assert.equal(esiti.filter(Boolean).length, SCONOSCIUTI_MAX);
  assert.equal(tentativoSconosciuto(comune, ORA + SCONOSCIUTI_FINESTRA_MS + 200), true);
  // L'account vero non ne risente
  const c: Conti = new Map();
  assert.equal(prenota(c, K, gettone(), ORA + 50), "ok");
});

test("chiave per email senza maiuscole e spazi; password giusta azzera gli errori", () => {
  assert.equal(chiaveAccount("  Mario@Esempio.IT "), "mario@esempio.it");
  assert.equal(chiaveAccount(""), null);
  assert.equal(chiaveAccount(42), null);
  const c: Conti = new Map();
  sbaglia(c, 5);
  const g = gettone();
  prenota(c, K, g, ORA + 10_000);
  chiudi(c, K, g, ORA + 10_000, "giusta");
  assert.equal(c.has(K), false);
});

test("un errore e un gettone con timestamp futuro (lock preso fuori ordine) non vengono scartati", () => {
  const conti: Conti = new Map();
  const errori = Array.from({ length: ACCOUNT_ERRORI_MAX - 2 }, (_, i) => ORA + 5000 + i);
  conti.set(K, { errori, bloccatoFino: null, inVolo: new Map([["futuro", ORA + 5000]]) });
  // 8 errori futuri + 1 gettone futuro = 9: ne resta uno solo, il secondo viene rifiutato
  assert.equal(prenota(conti, K, gettone(), ORA), "ok");
  assert.equal(conti.get(K)!.errori.length, ACCOUNT_ERRORI_MAX - 2);
  assert.ok(conti.get(K)!.inVolo.has("futuro"));
  assert.equal(prenota(conti, K, gettone(), ORA), "bloccato");
  chiudi(conti, K, "futuro", ORA, "giusta");
  assert.equal(conti.get(K)!.errori.length, 0); // giusta: si riparte da zero, come prima
  // chiudi con "altro" non cancella il gettone futuro di un'altra richiesta
  conti.set(K, { errori: [], bloccatoFino: null, inVolo: new Map([["a", ORA + 5000], ["b", ORA]]) });
  chiudi(conti, K, "b", ORA, "altro");
  assert.ok(conti.get(K)!.inVolo.has("a"));
});
