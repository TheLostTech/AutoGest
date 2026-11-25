// Nuovo tentativo di avvio quando la piattaforma non è pronta: al massimo ogni 30 secondi, uno per volta.
// Orologio finto e avvio finto. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { RIPROVA_AVVIO_MS, riprovaAvvio, type StatoAvvio } from "./pronta.ts";

const nonPronta = (ultimoTentativo: number): StatoAvvio => ({ nonPronta: true, ultimoTentativo, inCorso: null });
const orologio = (inizio: number) => {
  let t = inizio;
  return { ora: () => t, avanti: (ms: number) => void (t += ms) };
};
const zitto = <T>(fn: () => Promise<T>) => {
  const prima = console.error;
  console.error = () => {};
  return fn().finally(() => (console.error = prima));
};

test("piattaforma pronta: nessun tentativo, si passa", async () => {
  let chiamate = 0;
  const s: StatoAvvio = { nonPronta: false, ultimoTentativo: 0, inCorso: null };
  assert.equal(await riprovaAvvio(s, async () => (chiamate++, true), () => 0), true);
  assert.equal(chiamate, 0);
});

test("non pronta da meno di 30 secondi: niente tentativo, resta il 503", async () => {
  let chiamate = 0;
  const c = orologio(1_000_000);
  const s = nonPronta(c.ora());
  c.avanti(RIPROVA_AVVIO_MS - 1);
  assert.equal(await riprovaAvvio(s, async () => (chiamate++, true), c.ora), false);
  assert.equal(chiamate, 0);
  assert.equal(s.nonPronta, true);
});

test("dopo 30 secondi si riprova; riuscito: pronta e il segno si toglie", async () => {
  let chiamate = 0;
  const c = orologio(1_000_000);
  const s = nonPronta(c.ora());
  c.avanti(RIPROVA_AVVIO_MS);
  assert.equal(await riprovaAvvio(s, async () => (chiamate++, true), c.ora), true);
  assert.equal(chiamate, 1);
  assert.equal(s.nonPronta, false);
  assert.equal(s.inCorso, null);
  // Da qui in poi nessun altro tentativo
  assert.equal(await riprovaAvvio(s, async () => (chiamate++, true), c.ora), true);
  assert.equal(chiamate, 1);
});

test("tentativo fallito: resta non pronta e il prossimo aspetta 30 secondi dalla fine del tentativo", async () => {
  let chiamate = 0;
  const c = orologio(1_000_000);
  const s = nonPronta(c.ora() - RIPROVA_AVVIO_MS);
  // Un avvio lento: 10 secondi
  const avvia = async () => {
    chiamate++;
    c.avanti(10_000);
    return false;
  };
  assert.equal(await riprovaAvvio(s, avvia, c.ora), false);
  assert.equal(chiamate, 1);
  assert.equal(s.nonPronta, true);
  assert.equal(s.ultimoTentativo, c.ora());
  c.avanti(RIPROVA_AVVIO_MS - 1);
  assert.equal(await riprovaAvvio(s, avvia, c.ora), false);
  assert.equal(chiamate, 1);
  c.avanti(1);
  await riprovaAvvio(s, avvia, c.ora);
  assert.equal(chiamate, 2);
});

test("richieste insieme: un solo tentativo, tutte aspettano lo stesso esito", async () => {
  let chiamate = 0;
  let finisci!: (ok: boolean) => void;
  const s = nonPronta(0);
  const avvia = () => {
    chiamate++;
    return new Promise<boolean>((r) => (finisci = r));
  };
  const attese = Array.from({ length: 5 }, () => riprovaAvvio(s, avvia, () => RIPROVA_AVVIO_MS));
  await new Promise((r) => setImmediate(r));
  assert.equal(chiamate, 1);
  assert.ok(s.inCorso);
  finisci(true);
  assert.deepEqual(await Promise.all(attese), [true, true, true, true, true]);
  assert.equal(chiamate, 1);
  assert.equal(s.nonPronta, false);
});

test("avvio che lancia (subito o dopo): non pronta, nessun tentativo rimasto appeso, poi si riprova", async () => {
  const c = orologio(0);
  for (const avvia of [
    () => {
      throw new Error("subito");
    },
    async () => {
      throw new Error("dopo");
    },
  ]) {
    c.avanti(RIPROVA_AVVIO_MS);
    const s = nonPronta(0);
    assert.equal(await zitto(() => riprovaAvvio(s, avvia as () => Promise<boolean>, c.ora)), false);
    assert.equal(s.inCorso, null);
    assert.equal(s.nonPronta, true);
    c.avanti(RIPROVA_AVVIO_MS);
    assert.equal(await riprovaAvvio(s, async () => true, c.ora), true);
  }
});
