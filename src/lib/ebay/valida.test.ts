// Controllo della richiesta per POST /api/ebay/allinea. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { validaRichiesta } from "./valida.ts";
import type { RichiestaAllinea } from "./contratto.ts";

const base: RichiestaAllinea = {
  sku: "A-000001", attivo: true, quantita: 2, prezzo: 102.6, titolo: "Faro", descrizione: "x", categoriaQuery: "faro",
  condizione: "B", caratteristiche: { Marca: "Fiat" }, foto: ["/api/foto/a.jpg"], compatibilita: [{ marca: "Fiat", modello: "Punto" }],
  spedizione: "corriere", gpsr: { tipo: "esente" },
};

test("richiesta giusta passa", () => {
  assert.ok(validaRichiesta(base));
});

test("massimo 24 foto", () => {
  assert.ok(validaRichiesta({ ...base, foto: Array(24).fill("/api/foto/a.jpg") }));
  assert.equal(validaRichiesta({ ...base, foto: Array(25).fill("/api/foto/a.jpg") }), undefined);
});

test("testi troppo lunghi rifiutati", () => {
  assert.equal(validaRichiesta({ ...base, sku: "A-" + "1".repeat(60) }), undefined);
  assert.equal(validaRichiesta({ ...base, titolo: "x".repeat(300) }), undefined);
  assert.equal(validaRichiesta({ ...base, descrizione: "x".repeat(60_000) }), undefined);
  assert.equal(validaRichiesta({ ...base, categoriaQuery: "x".repeat(300) }), undefined);
  assert.equal(validaRichiesta({ ...base, foto: ["/api/foto/" + "a".repeat(600) + ".jpg"] }), undefined);
  assert.equal(validaRichiesta({ ...base, caratteristiche: { Marca: "x".repeat(300) } }), undefined);
  assert.equal(validaRichiesta({ ...base, compatibilita: [{ marca: "x".repeat(300), modello: "y" }] }), undefined);
});

test("elenchi troppo lunghi rifiutati", () => {
  const molte = Object.fromEntries(Array.from({ length: 60 }, (_, i) => [`c${i}`, "v"]));
  assert.equal(validaRichiesta({ ...base, caratteristiche: molte }), undefined);
  assert.equal(validaRichiesta({ ...base, compatibilita: Array(300).fill({ marca: "Fiat", modello: "Punto" }) }), undefined);
});

test("GPSR con dati del produttore troppo lunghi rifiutato", () => {
  const p = { ragioneSociale: "x".repeat(300), indirizzo: "via", citta: "Roma", cap: "00100", paese: "IT" };
  assert.equal(validaRichiesta({ ...base, gpsr: { tipo: "produttore", produttore: p } }), undefined);
});
