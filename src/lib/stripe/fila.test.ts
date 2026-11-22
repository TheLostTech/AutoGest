import { test } from "node:test";
import assert from "node:assert/strict";
import { creaFila } from "./fila.ts";

// Un lavoro che resta aperto finché il test non lo chiude
function aperto<T>() {
  let chiudi!: (v: T) => void;
  let rompi!: (e: unknown) => void;
  const p = new Promise<T>((r, f) => { chiudi = r; rompi = f; });
  return { p, chiudi, rompi };
}
const giro = () => new Promise((r) => setImmediate(r));

test("creaFila: i lavori della stessa chiave vanno uno per volta", async () => {
  const fila = creaFila<string>();
  const ordine: string[] = [];
  const a = aperto<string>();
  const pa = fila.metti("az", () => { ordine.push("a"); return a.p; });
  const b = aperto<string>();
  const pb = fila.metti("az", () => { ordine.push("b"); return b.p; });
  await giro();
  assert.deepEqual(ordine, ["a"]);
  a.chiudi("A");
  assert.equal(await pa, "A");
  await giro();
  assert.deepEqual(ordine, ["a", "b"]);
  b.chiudi("B");
  assert.equal(await pb, "B");
});

test("creaFila: un lavoro in coda e non ancora partito si riusa invece di metterne un altro", async () => {
  const fila = creaFila<number>();
  let partiti = 0;
  const a = aperto<number>();
  const pa = fila.metti("az", () => { partiti++; return a.p; });
  const p2 = fila.metti("az", async () => { partiti++; return 2; });
  const p3 = fila.metti("az", async () => { partiti++; return 3; });
  assert.equal(p3, p2);
  assert.equal(fila.inAttesa("az"), p2);
  a.chiudi(1);
  assert.equal(await pa, 1);
  assert.equal(await p2, 2);
  assert.equal(partiti, 2);
});

test("creaFila: una volta partito il lavoro, quello dopo ne mette uno nuovo (rilegge dopo)", async () => {
  const fila = creaFila<number>();
  const a = aperto<number>();
  const pa = fila.metti("az", () => a.p);
  await giro(); // a è partito: niente da riusare
  assert.equal(fila.inAttesa("az"), null);
  const pb = fila.metti("az", async () => 2);
  assert.notEqual(pb, pa);
  a.chiudi(1);
  assert.equal(await pb, 2);
});

test("creaFila: un errore non ferma la coda, e chiavi diverse non si aspettano", async () => {
  const fila = creaFila<number>();
  const a = aperto<number>();
  const pa = fila.metti("az", () => a.p);
  const pb = fila.metti("az", async () => 2);
  const pc = fila.metti("altra", async () => 3);
  assert.equal(await pc, 3);
  a.rompi(new Error("Stripe giù"));
  await assert.rejects(pa, /Stripe giù/);
  assert.equal(await pb, 2);
});
