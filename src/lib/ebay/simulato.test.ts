// Ponte eBay simulato. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { creaPonteSimulato } from "./simulato.ts";
import type { RichiestaAllinea } from "./contratto.ts";

const base: RichiestaAllinea = {
  sku: "A-000001", attivo: true, quantita: 2, prezzo: 102.6, titolo: "Faro", descrizione: "x", categoriaQuery: "faro",
  condizione: "B", caratteristiche: {}, foto: [], compatibilita: [], spedizione: "corriere", gpsr: { tipo: "esente" },
};

test("pubblica con numero e link finti", async () => {
  const e = await creaPonteSimulato().allinea(base);
  assert.equal(e.stato, "online");
  assert.equal(e.listingId, "SIM-A-000001");
  assert.equal(e.url, "/ebay-simulato/A-000001");
  assert.ok(e.categoria);
});

test("quantità 0 → esaurito; attivo false → ritirato", async () => {
  const p = creaPonteSimulato();
  assert.equal((await p.allinea({ ...base, quantita: 0 })).stato, "esaurito");
  assert.equal((await p.allinea({ ...base, attivo: false })).stato, "ritirato");
});

test("prezzo che finisce in ,13 dà errore simulato", async () => {
  const e = await creaPonteSimulato().allinea({ ...base, prezzo: 102.13 });
  assert.equal(e.stato, "errore");
  assert.ok(e.errore && e.errore.length > 0);
});

test("vendite restituisce [] e lo stato è simulato", async () => {
  const p = creaPonteSimulato();
  assert.deepEqual(await p.vendite("2026-01-01T00:00:00.000Z"), []);
  const s = await p.stato();
  assert.equal(s.modo, "Simulato");
  assert.equal(s.collegato, true);
});
