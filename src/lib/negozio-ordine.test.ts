// Ordine e pagamento del negozio: stesse regole per lo store del browser e per il server. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { ordineNegozio, pagaOrdine, rilasciaScaduti, type StatoCondiviso } from "./negozio-ordine.ts";

const cliente = { user: "Anna Verdi", role: "cliente", device: "Negozio online" };
const pezzo = (id: string, over: Record<string, unknown> = {}) => ({
  id, vehicleId: "V-000001", typeId: "faro", description: "faro anteriore sinistro", condition: "B", status: "disponibile", oemVerified: false, labelPrints: 0,
  price: 50, createdAt: "2026-02-0" + id.slice(-1), createdBy: "Luca", photos: ["/api/foto/a.jpg"], annuncioId: "A-000001",
  location: { mag: "A", corsia: "T01", scaffale: "101", ripiano: "A" }, ...over,
});
const stato = (): StatoCondiviso =>
  ({
    vehicles: [{ id: "V-000001", plate: "AB123CD", vin: "X", make: "Fiat", model: "Panda", version: "1.2", year: 2015, fuel: "benzina", verification: "verificato", intakeAt: "2026-01-01", createdBy: "x" }],
    parts: [pezzo("R-000001"), pezzo("R-000002")],
    annunci: [{ id: "A-000001", typeId: "faro", condition: "B", spedibile: true, price: 50, titolo: "Faro", descrizione: "d", testoModificato: true, caratteristiche: {}, negozio: { stato: "online" }, createdAt: "2026-02-01" }],
    orders: [],
    audit: [],
    counters: { order: 0, event: 0 },
  }) as unknown as StatoCondiviso;

test("ordine: riserva il pezzo più vecchio, crea l'ordine e scrive il registro", () => {
  const prima = stato();
  const r = ordineNegozio(prima, { annuncioIds: ["A-000001"], cliente: "Anna Verdi", consegna: "corriere", attore: cliente }, "2026-03-01T10:00:00.000Z");
  assert.equal(r.ok, true);
  if (!r.ok) return;
  assert.equal(r.ordineId, "O-000001");
  assert.deepEqual(r.st.parts.map((p) => p.status), ["riservato", "disponibile"]);
  assert.equal(r.st.orders[0].status, "in attesa di pagamento");
  assert.equal(r.st.orders[0].channel, "negozio");
  assert.equal(r.st.orders[0].delivery, "corriere");
  assert.deepEqual(r.st.audit.map((e) => e.action), ["Ordine creato", "Stato: disponibile → riservato"]);
  assert.ok(r.st.audit.every((e) => e.user === "Anna Verdi" && e.role === "cliente"));
  assert.equal(r.st.counters.order, 1);
  assert.equal(r.st.counters.event, 2);
  // lo stato di partenza non cambia
  assert.equal(prima.orders.length, 0);
  assert.equal(prima.audit.length, 0);
});

test("ordine: due pezzi esauriscono l'annuncio e lo scrivono nel registro", () => {
  const r = ordineNegozio(stato(), { annuncioIds: ["A-000001", "A-000001"], cliente: "Anna", consegna: "ritiro", attore: cliente }, "2026-03-01T10:00:00.000Z");
  assert.ok(r.ok);
  if (!r.ok) return;
  assert.equal(r.st.annunci[0].negozio?.stato, "esaurito");
  assert.ok(r.st.audit.some((e) => e.action === "Annuncio esaurito"));
});

test("ordine: carrello vuoto o pezzo non disponibile = errore; il rifiuto lascia una riga di registro", () => {
  const vuoto = ordineNegozio(stato(), { annuncioIds: [], cliente: "A" }, "x");
  assert.equal(vuoto.ok, false);
  const tre = ordineNegozio(stato(), { annuncioIds: ["A-000001", "A-000001", "A-000001"], cliente: "A", attore: cliente }, "2026-03-01T10:00:00.000Z");
  assert.equal(tre.ok, false);
  if (tre.ok) return;
  assert.deepEqual(tre.conflicts, ["A-000001"]);
  assert.equal(tre.st.audit[0].action, "Riserva rifiutata");
  assert.equal(tre.st.orders.length, 0);
  assert.ok(tre.st.parts.every((p) => p.status === "disponibile"));
});

test("pagamento riuscito: ordine pagato, pezzo venduto, eventi del cliente", () => {
  const o = ordineNegozio(stato(), { annuncioIds: ["A-000001"], cliente: "Anna", consegna: "corriere", attore: cliente }, "2026-03-01T10:00:00.000Z");
  assert.ok(o.ok);
  if (!o.ok) return;
  const provider = { ...cliente, device: "Provider di pagamento (simulato)" };
  const st = pagaOrdine(o.st, o.ordineId, true, provider, "2026-03-01T10:01:00.000Z");
  assert.equal(st.orders[0].status, "pagato");
  assert.equal(st.orders[0].paymentRef, "PAY-DEMO-000001");
  assert.equal(st.parts[0].status, "venduto");
  const ev = st.audit.filter((e) => e.device === provider.device).map((e) => e.action);
  assert.deepEqual(ev, ["Pagamento confermato", "Stato: riservato → venduto"]);
});

test("pagamento rifiutato: il pezzo torna disponibile e nell'annuncio", () => {
  const o = ordineNegozio(stato(), { annuncioIds: ["A-000001"], cliente: "Anna", attore: cliente }, "2026-03-01T10:00:00.000Z");
  assert.ok(o.ok);
  if (!o.ok) return;
  const st = pagaOrdine(o.st, o.ordineId, false, cliente, "2026-03-01T10:01:00.000Z");
  assert.equal(st.orders[0].status, "pagamento fallito");
  assert.equal(st.parts[0].status, "disponibile");
  assert.equal(st.parts[0].annuncioId, "A-000001");
});

test("riserva scaduta: ordine non pagato rilasciato, pezzo disponibile, riga di registro", () => {
  const o = ordineNegozio(stato(), { annuncioIds: ["A-000001"], cliente: "Anna", attore: cliente }, "2026-03-01T10:00:00.000Z");
  assert.ok(o.ok);
  if (!o.ok) return;
  const t0 = Date.parse("2026-03-01T10:00:00.000Z");
  assert.equal(rilasciaScaduti(o.st, t0 + 30 * 60_000), o.st);
  const r = rilasciaScaduti(o.st, t0 + 30 * 60_000 + 1);
  assert.equal(r.orders[0].status, "pagamento fallito");
  assert.equal(r.parts[0].status, "disponibile");
  assert.ok(r.audit.some((e) => e.action === "Riserva scaduta" && e.entityId === o.ordineId));
  assert.equal(r.annunci[0].negozio?.stato, "online");
});

test("pagamento: ordine inesistente o già chiuso non cambia nulla (stesso oggetto)", () => {
  const s = stato();
  assert.equal(pagaOrdine(s, "O-999999", true, cliente, "x"), s);
  const o = ordineNegozio(s, { annuncioIds: ["A-000001"], cliente: "Anna", attore: cliente }, "2026-03-01T10:00:00.000Z");
  assert.ok(o.ok);
  if (!o.ok) return;
  const pagato = pagaOrdine(o.st, o.ordineId, true, cliente, "2026-03-01T10:01:00.000Z");
  assert.equal(pagaOrdine(pagato, o.ordineId, false, cliente, "2026-03-01T10:02:00.000Z"), pagato);
});
