// Letture di abbonamento, archivio eBay e registro delle richieste: documento assente o rovinato come prima
// (null / vuoto), ma un errore del database arriva a chi chiama, così un'azienda che paga non sembra senza
// abbonamento per un guasto passeggero. Deposito finto. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { DocumentoIlleggibile, type Deposito, type TipoDocumento } from "./deposito/tipi.ts";

type Esito = { tipo: "assente" } | { tipo: "rovinato" } | { tipo: "guasto" } | { tipo: "dati"; v: unknown };
let esito: Esito = { tipo: "assente" };
const guasto = new Error("Connection terminated due to connection timeout");

const finto = {
  async leggiDocumento(az: string, tipo: TipoDocumento) {
    if (esito.tipo === "assente") return null;
    if (esito.tipo === "rovinato") throw new DocumentoIlleggibile(tipo, az, new SyntaxError("JSON"));
    if (esito.tipo === "guasto") throw guasto;
    return esito.v;
  },
} as unknown as Deposito;
(globalThis as typeof globalThis & { __deposito?: Deposito }).__deposito = finto;

const { leggiAbbonamento, ABBONAMENTO_NON_LEGGIBILE } = await import("./abbonamento-server.ts");
const { leggiArchivio } = await import("./ebay/archivio.ts");
const { elencoRichieste } = await import("./piattaforma/richieste-file.ts");
const { rispostaModuloSpento } = await import("./moduli-server.ts");

const zitto = async <T>(fn: () => Promise<T>): Promise<T> => {
  const prima = console.error;
  console.error = () => {};
  try {
    return await fn();
  } finally {
    console.error = prima;
  }
};

test("assente: null, archivio eBay vuoto, nessuna richiesta", async () => {
  esito = { tipo: "assente" };
  assert.equal(await leggiAbbonamento("az-1"), null);
  assert.deepEqual((await leggiArchivio("az-1")).consegnati, {});
  assert.deepEqual(await elencoRichieste("az-1"), []);
});

test("rovinato (DocumentoIlleggibile): come oggi, null o vuoto, con l'errore nel log", async () => {
  esito = { tipo: "rovinato" };
  await zitto(async () => {
    assert.equal(await leggiAbbonamento("az-1"), null);
    assert.deepEqual((await leggiArchivio("az-1")).politiche, {});
    assert.deepEqual(await elencoRichieste("az-1"), []);
  });
});

test("errore del database: arriva a chi chiama, mai trattato come documento assente", async () => {
  esito = { tipo: "guasto" };
  await assert.rejects(leggiAbbonamento("az-1"), guasto);
  await assert.rejects(leggiArchivio("az-1"), guasto);
  await assert.rejects(elencoRichieste("az-1"), guasto);
});

test("dati presenti: letti come sono", async () => {
  esito = { tipo: "dati", v: [{ userId: "u", azione: "crea", quando: "x", autore: "a" }] };
  assert.equal((await elencoRichieste("az-1")).length, 1);
});

test("modulo di un'azienda registrata con il database guasto: 503 con messaggio generico, non 403 né via libera", async () => {
  esito = { tipo: "guasto" };
  const r = await zitto(() => rispostaModuloSpento({ id: "az-1", registrata: true }, "accettazione", "Accettazione"));
  assert.ok(r);
  assert.equal(r.status, 503);
  const corpo = (await r.json()) as { error: string };
  assert.equal(corpo.error, ABBONAMENTO_NON_LEGGIBILE);
  assert.ok(!corpo.error.includes(guasto.message));
});

test("modulo spento (abbonamento scaduto): 403 con il messaggio di sempre", async () => {
  // Scaduto: resta solo il Magazzino base
  esito = { tipo: "dati", v: { stato: "scaduto", moduli: [], prova: false, aggiornato: 0 } };
  const r = await rispostaModuloSpento({ id: "az-1", registrata: true }, "accettazione", "Accettazione");
  assert.ok(r);
  assert.equal(r.status, 403);
  assert.deepEqual(await r.json(), { error: "Il modulo Accettazione non è attivo" });
});
