// Catalogo pubblico: solo annunci del negozio o di eBay, solo i campi che le pagine pubbliche leggono. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { catalogoPubblico, fotoPubblica } from "./catalogo-pubblico.ts";

const veicolo = {
  id: "V-000001", plate: "AB123CD", vin: "ZFA12345678901234", make: "Fiat", model: "Panda", version: "1.2", platform: "panda-312", year: 2015, fuel: "benzina",
  conferente: { tipo: "privato", nome: "Mario Rossi", cf: "RSSMRA80A01H501U" }, visura: { intestatario: "Mario Rossi" }, notes: "nota interna", intakeAt: "2026-01-01",
};
const pezzo = (id: string, annuncioId: string | undefined, over: Record<string, unknown> = {}) => ({
  id, vehicleId: "V-000001", typeId: "faro", description: "faro", condition: "B", status: "disponibile", oemVerified: true, oem: "123", labelPrints: 0,
  price: 40, notes: "pagato 5 euro a Mario", createdAt: "2026-02-01", createdBy: "Luca", photos: [`/api/foto/${id.toLowerCase().replace("-", "")}.jpg`], annuncioId,
  location: { mag: "A", corsia: "T01", scaffale: "101", ripiano: "A" }, defects: "graffio", km: 90000, ...over,
});
const annuncio = (id: string, over: Record<string, unknown> = {}) => ({
  id, typeId: "faro", condition: "B", spedibile: true, price: 50, titolo: "Faro", descrizione: "desc", testoModificato: false, caratteristiche: {}, gpsr: {}, createdAt: "2026-02-01", ...over,
});
const st = () => ({
  vehicles: [veicolo],
  annunci: [annuncio("A-000001", { negozio: { stato: "online" } }), annuncio("A-000002"), annuncio("A-000003", { ebay: { stato: "attivo", daRiallineare: false, errore: "x", quantitaInviata: 2, prezzoInviato: 55 } })],
  parts: [pezzo("R-000001", "A-000001"), pezzo("R-000002", "A-000001"), pezzo("R-000003", "A-000002", { status: "bozza" }), pezzo("R-000004", undefined), pezzo("R-000005", "A-000003")],
}) as unknown as Parameters<typeof catalogoPubblico>[0];

test("annuncio online con due pezzi e uno in bozza: solo il primo con i suoi due pezzi", () => {
  const c = catalogoPubblico(st());
  assert.deepEqual(c.annunci.map((a) => a.id), ["A-000001", "A-000003"]);
  assert.deepEqual(c.parts.map((p) => p.id), ["R-000001", "R-000002", "R-000005"]);
});

test("il veicolo restituito non ha targa, telaio, proprietario o note", () => {
  const v = catalogoPubblico(st()).vehicles[0] as unknown as Record<string, unknown>;
  assert.deepEqual(Object.keys(v).sort(), ["id", "make", "model", "platform", "version", "year"]);
});

test("i pezzi non hanno prezzi, note interne, ubicazione, operatore", () => {
  const p = catalogoPubblico(st()).parts[0] as unknown as Record<string, unknown>;
  for (const k of ["price", "notes", "location", "createdBy", "description", "labelPrints"]) assert.equal(k in p, false, k);
  assert.equal(p.defects, "graffio");
});

test("l'annuncio non porta errori eBay né dati GPSR", () => {
  const a = catalogoPubblico(st()).annunci[1] as unknown as Record<string, unknown>;
  assert.equal("gpsr" in a, false);
  assert.deepEqual(a.ebay, { stato: "attivo", quantitaInviata: 2, prezzoInviato: 55 });
});

test("solo i veicoli dei pezzi pubblicati", () => {
  const s = st();
  s.vehicles.push({ ...veicolo, id: "V-000002" } as never);
  assert.deepEqual(catalogoPubblico(s).vehicles.map((v) => v.id), ["V-000001"]);
});

test("fotoPubblica: vera per una foto dei pezzi pubblicati, falsa per bozza, non collegato e nome inventato", () => {
  const s = st();
  assert.equal(fotoPubblica(s, "r000001.jpg"), true);
  assert.equal(fotoPubblica(s, "r000005.jpg"), true);
  assert.equal(fotoPubblica(s, "r000003.jpg"), false);
  assert.equal(fotoPubblica(s, "r000004.jpg"), false);
  assert.equal(fotoPubblica(s, "inventata.jpg"), false);
  assert.equal(fotoPubblica(s, "../state.json"), false);
});

test("stato vuoto o senza liste: catalogo vuoto", () => {
  assert.deepEqual(catalogoPubblico({} as never), { annunci: [], parts: [], vehicles: [] });
});
