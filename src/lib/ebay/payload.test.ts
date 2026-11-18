// Costruttori dei corpi delle chiamate eBay (puri). Si eseguono con: npm test
/* eslint-disable @typescript-eslint/no-explicit-any -- nei test si leggono i corpi JSON per campo */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  aspettiPerEbay, compatibilityBody, conditionFor, controllaAspetti, ErroreEbay, fileFoto, inventoryItemBody, nomiCompat,
  offerBody, politicaPagamentoBody, politicaResoBody, politicaSpedizioneBody, posizionamento, rinominaCompat, statoDaOfferta,
  traduciErrore, urlConsenso, venditeDaOrdini,
} from "./payload.ts";
import { CONDITIONS } from "../catalog.ts";
import type { RichiestaAllinea } from "./contratto.ts";

const base: RichiestaAllinea = {
  sku: "A-000001", attivo: true, quantita: 2, prezzo: 102.6, titolo: "Faro anteriore sx Fiat Punto Evo", descrizione: "Faro in buono stato.\nFunzionante.",
  categoriaQuery: "faro anteriore auto", condizione: "B",
  caratteristiche: { Tipo: "Faro anteriore", Marca: "Fiat", "Posizionamento sul veicolo": "Anteriore sx" },
  foto: ["/api/foto/abc123.jpg"], compatibilita: [{ marca: "Fiat", modello: "Punto Evo", anno: 2010, motore: "1.2" }],
  spedizione: "corriere", gpsr: { tipo: "esente" },
};
const politiche = { pagamento: "PAY-1", reso: "RET-1", spedizione: "FUL-1" };

test("offerta a prezzo fisso, eBay Italia, senza scadenza", () => {
  const o = offerBody(base, "33710", politiche, "sede") as Record<string, any>;
  assert.equal(o.sku, "A-000001");
  assert.equal(o.format, "FIXED_PRICE");
  assert.equal(o.marketplaceId, "EBAY_IT");
  assert.equal(o.listingDuration, "GTC");
  assert.deepEqual(o.pricingSummary.price, { value: "102.60", currency: "EUR" });
  assert.equal(o.availableQuantity, 2);
  assert.equal(o.categoryId, "33710");
  assert.equal(o.listingPolicies.fulfillmentPolicyId, "FUL-1");
  assert.equal(o.listingPolicies.paymentPolicyId, "PAY-1");
  assert.equal(o.listingPolicies.returnPolicyId, "RET-1");
  assert.equal(o.merchantLocationKey, "sede");
});

test("quantità zero resta nell'articolo", () => {
  const i = inventoryItemBody({ ...base, quantita: 0 }, []) as Record<string, any>;
  assert.equal(i.availability.shipToLocationAvailability.quantity, 0);
  assert.equal((offerBody({ ...base, quantita: 0 }, "1", politiche, "sede") as Record<string, any>).availableQuantity, 0);
});

test("articolo: titolo entro 80, foto di eBay, caratteristiche come elenchi", () => {
  const i = inventoryItemBody({ ...base, titolo: "x".repeat(95) }, ["https://i.ebayimg.sandbox.ebay.com/1.jpg"]) as Record<string, any>;
  assert.equal(i.product.title.length, 80);
  assert.deepEqual(i.product.imageUrls, ["https://i.ebayimg.sandbox.ebay.com/1.jpg"]);
  assert.deepEqual(i.product.aspects.Marca, ["Fiat"]);
  assert.deepEqual(i.product.aspects["Posizionamento sul veicolo"], ["Anteriore", "Sinistra"]);
});

test("descrizione senza HTML del testo e con gli a capo", () => {
  const o = offerBody({ ...base, descrizione: "Faro <b>x</b> & co\nriga 2" }, "1", politiche, "sede") as Record<string, any>;
  assert.equal(o.listingDescription, "Faro &lt;b&gt;x&lt;/b&gt; &amp; co<br>riga 2");
});

test("condizioni", () => {
  assert.equal(conditionFor("A"), "USED_EXCELLENT");
  assert.equal(conditionFor("B"), "USED_EXCELLENT");
  assert.equal(conditionFor("C"), "USED_EXCELLENT");
  assert.equal(conditionFor("D"), "FOR_PARTS_OR_NOT_WORKING");
  for (const c of ["A", "B", "C", "D"] as const) {
    const i = inventoryItemBody({ ...base, condizione: c }, []) as Record<string, any>;
    assert.equal(i.condition, conditionFor(c));
    assert.ok(i.conditionDescription.includes(`Condizione ${c}`), i.conditionDescription);
    assert.ok(i.conditionDescription.includes(CONDITIONS[c].label));
    assert.ok(i.conditionDescription.includes(CONDITIONS[c].hint));
  }
});

// Su eBay i dati GPSR stanno nell'offerta (offer.regulatory), non nell'articolo: vedi payload.ts
test("GPSR esente senza produttore", () => {
  const o = offerBody(base, "1", politiche, "sede") as Record<string, any>;
  assert.equal(o.regulatory, undefined);
  assert.equal((inventoryItemBody(base, []) as Record<string, any>).product.regulatory, undefined);
  const p = offerBody(
    { ...base, gpsr: { tipo: "produttore", produttore: { ragioneSociale: "Stellantis Europe S.p.A.", indirizzo: "Corso Agnelli 200", citta: "Torino", cap: "10135", paese: "Italia", email: "info@example.com" } } },
    "1", politiche, "sede",
  ) as Record<string, any>;
  assert.equal(p.regulatory.manufacturer.companyName, "Stellantis Europe S.p.A.");
  assert.equal(p.regulatory.manufacturer.addressLine1, "Corso Agnelli 200");
  assert.equal(p.regulatory.manufacturer.city, "Torino");
  assert.equal(p.regulatory.manufacturer.postalCode, "10135");
  assert.equal(p.regulatory.manufacturer.country, "IT");
  assert.equal(p.regulatory.manufacturer.email, "info@example.com");
});

test("GPSR da confermare non arriva a eBay", () => {
  assert.throws(() => offerBody({ ...base, gpsr: { tipo: "da confermare" } }, "1", politiche, "sede"), ErroreEbay);
});

test("compatibilità per proprietà", () => {
  const c = compatibilityBody({
    ...base,
    compatibilita: [
      { marca: "Fiat", modello: "Punto Evo", anno: 2010, motore: "1.2" },
      { marca: "Fiat", modello: "Punto Evo", anni: "2009–2012" },
      { marca: "Lancia", modello: "Ypsilon", anni: "2024–" },
    ],
  }, 2026) as { compatibleProducts: { compatibilityProperties: { name: string; value: string }[] }[] };
  const veicoli = c.compatibleProducts.map((p) => Object.fromEntries(p.compatibilityProperties.map((x) => [x.name, x.value])));
  assert.deepEqual(veicoli[0], { make: "Fiat", model: "Punto Evo", year: "2010", engine: "1.2" });
  assert.deepEqual(veicoli.slice(1, 5).map((v) => v.year), ["2009", "2010", "2011", "2012"]);
  assert.ok(veicoli.slice(1, 5).every((v) => v.make === "Fiat" && v.model === "Punto Evo" && !("engine" in v)));
  assert.deepEqual(veicoli.slice(5).map((v) => v.year), ["2024", "2025", "2026"]);
  assert.equal(veicoli.length, 8);
});

test("compatibilità: anni con trattino normale e doppioni tolti", () => {
  const c = compatibilityBody({ ...base, compatibilita: [{ marca: "VW", modello: "Golf", anni: "2008-2009" }, { marca: "VW", modello: "Golf", anno: 2008 }] }, 2026) as { compatibleProducts: unknown[] };
  assert.equal(c.compatibleProducts.length, 2);
});

test("nomi delle proprietà dei veicoli come li chiama eBay Italia", () => {
  const n = nomiCompat([{ name: "Make", localizedName: "Marca" }, { name: "Model", localizedName: "Modello" }, { name: "Cars Year", localizedName: "Anno" }, { name: "Engine", localizedName: "Motore" }, { name: "Platform" }]);
  assert.deepEqual(n, { make: "Make", model: "Model", year: "Cars Year", engine: "Engine" });
  const r = rinominaCompat([{ make: "Fiat", model: "Punto", year: "2010" }], n);
  assert.deepEqual(r, { compatibleProducts: [{ compatibilityProperties: [{ name: "Make", value: "Fiat" }, { name: "Model", value: "Punto" }, { name: "Cars Year", value: "2010" }] }] });
});

test("lato dell'app → posizionamento in stile eBay", () => {
  assert.deepEqual(posizionamento("Anteriore dx"), ["Anteriore", "Destra"]);
  assert.deepEqual(posizionamento("Posteriore sx"), ["Posteriore", "Sinistra"]);
  assert.deepEqual(posizionamento("Sinistro"), ["Sinistra"]);
  assert.deepEqual(posizionamento("Destro"), ["Destra"]);
  assert.equal(posizionamento("Anteriore dx").join(", "), "Anteriore, Destra");
  assert.deepEqual(posizionamento("Centrale"), ["Centrale"]);
  assert.deepEqual(aspettiPerEbay({ Tipo: "Porta", "Posizionamento sul veicolo": "Posteriore dx", Vuoto: " " }), { Tipo: ["Porta"], "Posizionamento sul veicolo": ["Posteriore", "Destra"] });
});

test("caratteristiche obbligatorie mancanti e valori non riconosciuti diventano avvisi", () => {
  const meta = {
    aspects: [
      { localizedAspectName: "Marca", aspectConstraint: { aspectRequired: true, aspectMode: "FREE_TEXT" } },
      { localizedAspectName: "Numero ricambio produttore", aspectConstraint: { aspectRequired: true, aspectMode: "FREE_TEXT" } },
      { localizedAspectName: "Posizionamento sul veicolo", aspectConstraint: { aspectMode: "SELECTION_ONLY" }, aspectValues: [{ localizedValue: "Anteriore" }, { localizedValue: "Sinistra" }] },
      { localizedAspectName: "Colore", aspectConstraint: { aspectMode: "SELECTION_ONLY" }, aspectValues: [{ localizedValue: "Nero" }] },
    ],
  };
  const r = controllaAspetti({ Marca: ["Fiat"], "Posizionamento sul veicolo": ["Anteriore", "Destra"], Colore: ["Blu"] }, meta);
  assert.deepEqual(r.aspetti, { Marca: ["Fiat"], "Posizionamento sul veicolo": ["Anteriore"] });
  assert.equal(r.avvisi.length, 3);
  assert.ok(r.avvisi.some((a) => a.includes("Numero ricambio produttore")));
  assert.ok(r.avvisi.some((a) => a.includes("Destra")));
  assert.ok(r.avvisi.some((a) => a.includes("Blu")));
});

test("foto: solo file del gestionale, niente percorsi strani", () => {
  assert.deepEqual(fileFoto("/api/foto/abc123.jpg"), { cartella: "foto", nome: "abc123.jpg", tipo: "image/jpeg" });
  assert.deepEqual(fileFoto("/renders/faro-anteriore.png"), { cartella: "public", nome: "renders/faro-anteriore.png", tipo: "image/png" });
  assert.equal(fileFoto("/api/foto/../../chiave.jpg"), undefined);
  assert.equal(fileFoto("/renders/../.env"), undefined);
  assert.equal(fileFoto("https://altro.sito/x.jpg"), undefined);
});

test("stato dell'annuncio dalla risposta di eBay", () => {
  assert.equal(statoDaOfferta({ status: "PUBLISHED", listing: { listingId: "1", listingStatus: "ACTIVE" } }), "pubblicata");
  assert.equal(statoDaOfferta({ status: "PUBLISHED", listing: { listingId: "1", listingStatus: "OUT_OF_STOCK" } }), "pubblicata");
  assert.equal(statoDaOfferta({ status: "PUBLISHED", listing: { listingId: "1", listingStatus: "ENDED" } }), "chiusa");
  assert.equal(statoDaOfferta({ status: "UNPUBLISHED" }), "non pubblicata");
  assert.equal(statoDaOfferta(undefined), "non pubblicata");
});

test("vendite: una per riga d'ordine con SKU A-, annullati esclusi", () => {
  const v = venditeDaOrdini([
    { orderId: "O1", creationDate: "2026-11-18T10:00:00.000Z", buyer: { username: "mario" }, cancelStatus: { cancelState: "NONE_REQUESTED" },
      lineItems: [{ lineItemId: "L1", sku: "A-000001", quantity: 2, lineItemCost: { value: "205.20", currency: "EUR" } }] },
    { orderId: "O2", creationDate: "2026-11-18T11:00:00.000Z", buyer: { username: "anna" },
      lineItems: [{ lineItemId: "L2", sku: "A-000002", quantity: 1, lineItemCost: { value: "50.00" } }, { lineItemId: "L3", sku: "ALTRO-1", quantity: 1, lineItemCost: { value: "9.00" } }, { lineItemId: "L4", sku: "A-000003", quantity: 1, lineItemCost: { value: "20.00" } }] },
    { orderId: "O3", creationDate: "2026-11-18T12:00:00.000Z", cancelStatus: { cancelState: "CANCELED" }, lineItems: [{ lineItemId: "L5", sku: "A-000004", quantity: 1, lineItemCost: { value: "10.00" } }] },
  ]);
  assert.deepEqual(v, [
    { orderId: "O1", sku: "A-000001", quantita: 2, prezzoUnitario: 102.6, acquirente: "mario", at: "2026-11-18T10:00:00.000Z" },
    { orderId: "O2/L2", sku: "A-000002", quantita: 1, prezzoUnitario: 50, acquirente: "anna", at: "2026-11-18T11:00:00.000Z" },
    { orderId: "O2/L4", sku: "A-000003", quantita: 1, prezzoUnitario: 20, acquirente: "anna", at: "2026-11-18T11:00:00.000Z" },
  ]);
});

test("politiche di base: corriere, ritiro in sede, reso 14 giorni", () => {
  const c = politicaSpedizioneBody("corriere") as Record<string, any>;
  assert.equal(c.name, "Corriere");
  assert.equal(c.marketplaceId, "EBAY_IT");
  assert.equal(c.shippingOptions[0].shippingServices[0].shippingServiceCode, "IT_ExpressCourier");
  assert.equal((politicaSpedizioneBody("voluminoso") as Record<string, any>).name, "Corriere voluminoso");
  const r = politicaSpedizioneBody("ritiro") as Record<string, any>;
  assert.equal(r.name, "Solo ritiro in sede");
  assert.equal(r.localPickup, true);
  const reso = politicaResoBody() as Record<string, any>;
  assert.deepEqual(reso.returnPeriod, { value: 14, unit: "DAY" });
  assert.equal(reso.returnsAccepted, true);
  assert.equal((politicaPagamentoBody() as Record<string, any>).marketplaceId, "EBAY_IT");
});

test("consenso: RuName come indirizzo di ritorno, scope e state", () => {
  const u = new URL(urlConsenso("https://auth.sandbox.ebay.com/oauth2/authorize", "app-1", "Mio_RuName", ["https://api.ebay.com/oauth/api_scope", "https://api.ebay.com/oauth/api_scope/sell.inventory"], "st4te"));
  assert.equal(u.origin + u.pathname, "https://auth.sandbox.ebay.com/oauth2/authorize");
  assert.equal(u.searchParams.get("client_id"), "app-1");
  assert.equal(u.searchParams.get("redirect_uri"), "Mio_RuName");
  assert.equal(u.searchParams.get("response_type"), "code");
  assert.equal(u.searchParams.get("state"), "st4te");
  assert.equal(u.searchParams.get("scope"), "https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.inventory");
  assert.ok(!u.search.includes("+"), "spazi come %20");
});

test("errori di eBay in italiano semplice, senza il testo grezzo", () => {
  const e = traduciErrore(400, { errors: [{ errorId: 25003, message: "Invalid price. token=SEGRETO" }] });
  assert.ok(e.messaggio.includes("prezzo"));
  assert.ok(e.messaggio.includes("Cosa fare"));
  assert.ok(!e.messaggio.includes("SEGRETO"));
  assert.ok(e.log.includes("25003"));
  const m = traduciErrore(400, { errors: [{ errorId: 25029, message: "x", parameters: [{ name: "0", value: "Numero ricambio produttore" }] }] });
  assert.ok(m.messaggio.includes("Numero ricambio produttore"));
  const strano = traduciErrore(400, { errors: [{ errorId: 25029, parameters: [{ name: "0", value: "<script>v^1.1#i^1</script>" }] }] });
  assert.ok(!strano.messaggio.includes("script"));
  assert.ok(traduciErrore(401, { error: "invalid_grant" }).messaggio.includes("Collega account eBay"));
  assert.ok(traduciErrore(503, "").messaggio.includes("riprova"));
  const ignoto = traduciErrore(400, { errors: [{ errorId: 99999, message: "boh" }] });
  assert.ok(ignoto.messaggio.includes("99999") && !ignoto.messaggio.includes("boh"));
});
