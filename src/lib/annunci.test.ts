// Modello degli annunci con più pezzi. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  categoriaEbayDa,
  groupKey,
  gpsrAfterVehicleChange,
  gpsrBlocksEbay,
  isWithdrawn,
  alignedPrice,
  listingOf,
  listingFieldsChanged,
  membershipAfter,
  missingNote,
  nextToShip,
  negozioStato,
  normalizeOem,
  partsOf,
  pickForSale,
  placementFor,
  quantityOf,
  refreshAnnuncio,
  shopPicks,
} from "./annunci.ts";
import type { Annuncio, Part, Vehicle } from "./types.ts";

let n = 0;
function part(over: Partial<Part> = {}): Part {
  n += 1;
  return {
    id: `R-${String(n).padStart(6, "0")}`,
    vehicleId: "V-1",
    typeId: "faro",
    description: "Faro",
    condition: "B",
    status: "disponibile",
    oem: "50510123A",
    oemVerified: true,
    photos: [],
    labelPrints: 0,
    price: 90,
    createdAt: "2026-01-01T10:00:00.000Z",
    createdBy: "test",
    ...over,
  };
}

function annuncio(over: Partial<Annuncio> = {}): Annuncio {
  return {
    id: "A-000001",
    chiave: "faro|50510123A|-|B|R",
    typeId: "faro",
    condition: "B",
    oem: "50510123A",
    spedibile: false,
    price: 90,
    titolo: "Faro",
    descrizione: "",
    testoModificato: false,
    caratteristiche: {},
    gpsr: { tipo: "da confermare" },
    negozio: { stato: "online" },
    createdAt: "2026-01-01T10:00:00.000Z",
    ...over,
  };
}

test("codici scritti in modi diversi danno la stessa chiave", () => {
  assert.equal(normalizeOem("50 510.123-a"), "50510123A");
  const a = part({ oem: "50 510.123-a" });
  const b = part({ oem: "50510123A" });
  assert.equal(groupKey(a, false), groupKey(b, false));
  assert.equal(groupKey(b, false), "faro|50510123A|-|B|R");
});

test("senza codice verificato nessuna chiave", () => {
  assert.equal(groupKey(part({ oemVerified: false }), false), undefined);
  assert.equal(groupKey(part({ oem: undefined }), false), undefined);
});

test("lato, condizione o spedibilità diversi danno chiavi diverse", () => {
  const base = groupKey(part(), false);
  assert.notEqual(groupKey(part({ side: "DX" }), false), base);
  assert.notEqual(groupKey(part({ condition: "A" }), false), base);
  assert.notEqual(groupKey(part(), true), base);
});

test("la quantità conta solo i disponibili", () => {
  const a = annuncio();
  const parts = [
    part({ annuncioId: a.id }),
    part({ annuncioId: a.id }),
    part({ annuncioId: a.id, status: "riservato" }),
    part({ annuncioId: a.id, status: "venduto" }),
    part({ annuncioId: "A-000002" }),
  ];
  assert.equal(partsOf(a, parts).length, 4);
  assert.equal(quantityOf(a, parts), 2);
});

test("parte per primo il pezzo entrato prima", () => {
  const a = annuncio();
  const p1 = part({ annuncioId: a.id, createdAt: "2026-03-01T00:00:00.000Z" });
  const p2 = part({ annuncioId: a.id, createdAt: "2026-01-01T00:00:00.000Z" });
  const p3 = part({ annuncioId: a.id, createdAt: "2026-02-01T00:00:00.000Z" });
  assert.deepEqual(nextToShip(a, [p1, p2, p3], 2).map((p) => p.id), [p2.id, p3.id]);
  assert.deepEqual(nextToShip(a, [p1, p2, p3]).map((p) => p.id), [p2.id]);
});

test("un pezzo reso non conta finché non torna disponibile", () => {
  const a = annuncio();
  const reso = part({ annuncioId: a.id, status: "bozza" });
  assert.equal(quantityOf(a, [reso]), 0);
  assert.equal(listingOf(reso, [a]), "ritirato");
  const torna = { ...reso, status: "disponibile" as const };
  assert.equal(quantityOf(a, [torna]), 1);
  assert.equal(listingOf(torna, [a]), "pubblicato");
  assert.equal(listingOf(part(), [a]), "non pubblicato");
});

test("placementFor: nuovo, unisci, prezzo diverso, annuncio ritirato", () => {
  const p = part();
  const key = groupKey(p, false);
  assert.deepEqual(placementFor(p, key, []), { kind: "nuovo" });
  const a = annuncio();
  assert.deepEqual(placementFor(p, key, [a]), { kind: "unisci", annuncioId: a.id });
  assert.deepEqual(placementFor(part({ price: 95 }), key, [a]), {
    kind: "prezzo diverso",
    annuncioId: a.id,
    prezzoAnnuncio: 90,
  });
  const ritirato = annuncio({ negozio: { stato: "ritirato" } });
  assert.equal(isWithdrawn(ritirato), true);
  assert.deepEqual(placementFor(p, key, [ritirato]), {
    kind: "annuncio ritirato",
    annuncioId: ritirato.id,
  });
  assert.deepEqual(placementFor(part({ price: undefined }), key, [a]), { kind: "nuovo" });
});

test("senza chiave il pezzo fa sempre un annuncio nuovo", () => {
  assert.deepEqual(placementFor(part(), undefined, [annuncio()]), { kind: "nuovo" });
});

test("negozioStato", () => {
  const a = annuncio();
  assert.equal(negozioStato(a, 0), "esaurito");
  assert.equal(negozioStato(a, 2), "online");
  assert.equal(negozioStato(annuncio({ negozio: { stato: "ritirato" } }), 2), "ritirato");
  assert.equal(negozioStato(annuncio({ negozio: undefined }), 2), undefined);
});

test("isWithdrawn: ritirato solo se ogni canale esistente è ritirato", () => {
  const eb = (stato: "online" | "ritirato") => ({ stato, daRiallineare: false });
  assert.equal(isWithdrawn(annuncio({ negozio: { stato: "ritirato" }, ebay: eb("online") })), false);
  assert.equal(isWithdrawn(annuncio({ negozio: undefined, ebay: eb("ritirato") })), true);
  assert.equal(isWithdrawn(annuncio({ negozio: { stato: "ritirato" }, ebay: eb("ritirato") })), true);
  assert.equal(isWithdrawn(annuncio({ negozio: { stato: "online" } })), false);
  assert.equal(isWithdrawn(annuncio({ negozio: undefined })), false);
});

test("placementFor: con più annunci uguali sceglie quello vivo", () => {
  const p = part();
  const key = groupKey(p, false);
  const morto = annuncio({ id: "A-000001", negozio: { stato: "ritirato" } });
  const vivo = annuncio({ id: "A-000002" });
  assert.deepEqual(placementFor(p, key, [morto, vivo]), { kind: "unisci", annuncioId: "A-000002" });
});

test("nextToShip: a parità di data parte l'id più basso", () => {
  const a = annuncio();
  const t = "2026-01-01T00:00:00.000Z";
  const p2 = part({ id: "R-000002", annuncioId: a.id, createdAt: t });
  const p1 = part({ id: "R-000001", annuncioId: a.id, createdAt: t });
  assert.deepEqual(nextToShip(a, [p2, p1]).map((p) => p.id), ["R-000001"]);
});

test("una vendita eBay prende i pezzi entrati per primi", () => {
  const a = annuncio();
  const p1 = part({ annuncioId: a.id, createdAt: "2026-03-01T00:00:00.000Z" });
  const p2 = part({ annuncioId: a.id, createdAt: "2026-01-01T00:00:00.000Z" });
  const p3 = part({ annuncioId: a.id, createdAt: "2026-02-01T00:00:00.000Z" });
  assert.deepEqual(pickForSale(a, [p1, p2, p3], 2), { partIds: [p2.id, p3.id], mancano: 0 });
});

test("importa vendita con più pezzi di quelli disponibili", () => {
  const a = annuncio();
  const solo = part({ annuncioId: a.id });
  const riservato = part({ annuncioId: a.id, status: "riservato" });
  const venduto = part({ annuncioId: a.id, status: "venduto" });
  assert.deepEqual(pickForSale(a, [solo, riservato, venduto], 3), { partIds: [solo.id], mancano: 2 });
  assert.deepEqual(pickForSale(a, [venduto], 1), { partIds: [], mancano: 1 });
});

test("nota da gestire per i pezzi che mancano", () => {
  assert.equal(missingNote(0), undefined);
  assert.equal(missingNote(1), "manca 1 pezzo");
  assert.equal(missingNote(2), "mancano 2 pezzi");
});

test("un pezzo scartato o invendibile esce dall'annuncio", () => {
  assert.equal(membershipAfter(part({ annuncioId: "A-000001", status: "scartato" }), true), undefined);
  assert.equal(membershipAfter(part({ annuncioId: "A-000001", status: "invendibile" }), true), undefined);
});

test("un pezzo che torna disponibile resta nell'annuncio solo se passa i controlli", () => {
  assert.equal(membershipAfter(part({ annuncioId: "A-000001" }), true), "A-000001");
  assert.equal(membershipAfter(part({ annuncioId: "A-000001" }), false), undefined);
  // reso in bozza: tiene l'annuncio, non conta finché non torna disponibile
  assert.equal(membershipAfter(part({ annuncioId: "A-000001", status: "bozza" }), false), "A-000001");
  assert.equal(membershipAfter(part({ annuncioId: "A-000001", status: "venduto" }), false), "A-000001");
  assert.equal(membershipAfter(part(), true), undefined);
});

test("negozio: si compra solo un annuncio online sul negozio con pezzi disponibili", () => {
  const vivo = annuncio({ id: "A-000001" });
  const soloEbay = annuncio({ id: "A-000002", negozio: { stato: "ritirato" }, ebay: { stato: "online", daRiallineare: false } });
  const esaurito = annuncio({ id: "A-000003", negozio: { stato: "esaurito" } });
  const p1 = part({ annuncioId: vivo.id, createdAt: "2026-02-01T00:00:00.000Z" });
  const p2 = part({ annuncioId: vivo.id, createdAt: "2026-01-01T00:00:00.000Z" });
  const p3 = part({ annuncioId: soloEbay.id });
  const parts = [p1, p2, p3];
  const annunci = [vivo, soloEbay, esaurito];
  assert.deepEqual(shopPicks([vivo.id], annunci, parts), {
    picks: [{ annuncioId: vivo.id, partId: p2.id, price: 90 }],
    conflicts: [],
  });
  assert.deepEqual(shopPicks([soloEbay.id], annunci, parts).conflicts, [soloEbay.id]);
  assert.deepEqual(shopPicks([esaurito.id, "A-999999"], annunci, parts).conflicts, [esaurito.id, "A-999999"]);
  // lo stesso annuncio due volte vuol dire due pezzi
  assert.deepEqual(shopPicks([vivo.id, vivo.id], annunci, parts).picks.map((x) => x.partId), [p2.id, p1.id]);
  assert.deepEqual(shopPicks([vivo.id, vivo.id, vivo.id], annunci, parts).conflicts, [vivo.id]);
});

test("refreshAnnuncio: esaurito a zero, di nuovo online sopra zero", () => {
  const a = annuncio();
  const at = "2026-05-01T00:00:00.000Z";
  const zero = refreshAnnuncio(a, [part({ annuncioId: a.id, status: "venduto" })], at);
  assert.equal(zero.negozio?.stato, "esaurito");
  assert.equal(zero.esauritoDa, at);
  const ancora = refreshAnnuncio(zero, [], "2026-06-01T00:00:00.000Z");
  assert.equal(ancora.esauritoDa, at);
  const torna = refreshAnnuncio(zero, [part({ annuncioId: a.id })], "2026-06-01T00:00:00.000Z");
  assert.equal(torna.negozio?.stato, "online");
  assert.equal(torna.esauritoDa, undefined);
  const ritirato = refreshAnnuncio(annuncio({ negozio: { stato: "ritirato" } }), [part({ annuncioId: a.id })], at);
  assert.equal(ritirato.negozio?.stato, "ritirato");
});

test("refreshAnnuncio: eBay da riallineare, tranne se ritirato", () => {
  const at = "2026-05-01T00:00:00.000Z";
  const online = annuncio({ ebay: { stato: "online", daRiallineare: false } });
  assert.equal(refreshAnnuncio(online, [], at).ebay?.daRiallineare, true);
  const ritirato = annuncio({ ebay: { stato: "ritirato", daRiallineare: false } });
  assert.equal(refreshAnnuncio(ritirato, [], at).ebay?.daRiallineare, false);
  assert.equal(refreshAnnuncio(annuncio(), [], at).ebay, undefined);
});

test("refreshAnnuncio: riscrive il testo solo se non è stato modificato", () => {
  const at = "2026-05-01T00:00:00.000Z";
  const a = annuncio();
  const parts = [part({ annuncioId: a.id }), part({ annuncioId: a.id })];
  const regen = (q: number) => ({ titolo: `Faro x${q}`, descrizione: `${q} pezzi` });
  const r = refreshAnnuncio(a, parts, at, regen);
  assert.equal(r.titolo, "Faro x2");
  assert.equal(r.descrizione, "2 pezzi");
  const scritto = refreshAnnuncio({ ...a, testoModificato: true, titolo: "Mio" }, parts, at, regen);
  assert.equal(scritto.titolo, "Mio");
});

test("vendita annullata dopo un cambio di prezzo: il pezzo rientra al prezzo dell'annuncio", () => {
  // Venduto a 90; intanto l'annuncio è passato a 80 (i venduti non cambiano prezzo); poi l'ordine si annulla
  const a = annuncio({ price: 80 });
  const tornato = part({ annuncioId: a.id, price: 90, status: "disponibile" });
  assert.equal(membershipAfter(tornato, true), a.id);
  assert.equal(alignedPrice(tornato, a), 80);
  // reso approvato: stesso allineamento
  assert.equal(alignedPrice({ ...tornato, price: 70 }, a), 80);
  // già allineato, non disponibile o senza annuncio: niente da fare
  assert.equal(alignedPrice(part({ annuncioId: a.id, price: 80 }), a), undefined);
  assert.equal(alignedPrice(part({ annuncioId: a.id, price: 90, status: "venduto" }), a), undefined);
  assert.equal(alignedPrice(part({ annuncioId: a.id, price: 90, status: "bozza" }), a), undefined);
  assert.equal(alignedPrice(part({ annuncioId: "A-000009", price: 90 }), a), undefined);
  assert.equal(alignedPrice(tornato, undefined), undefined);
});

test("veicolo cambiato: testo e GPSR degli annunci solo se cambiano i dati che li usano", () => {
  const v = { make: "Alfa Romeo", model: "Giulietta", version: "1.6", year: 2012, km: 100000, notes: "" } as unknown as Vehicle;
  assert.deepEqual(listingFieldsChanged(v, { ...v, notes: "pratica ok" }), { text: false, gpsr: false });
  assert.deepEqual(listingFieldsChanged(v, { ...v, model: "Giulia" }), { text: true, gpsr: false });
  assert.deepEqual(listingFieldsChanged(v, { ...v, km: 120000 }), { text: true, gpsr: false });
  assert.deepEqual(listingFieldsChanged(v, { ...v, year: 2025 }), { text: true, gpsr: true });
  assert.deepEqual(listingFieldsChanged(v, { ...v, make: "Fiat" }), { text: true, gpsr: true });
});

test("GPSR confermato a mano: non si ricalcola con il veicolo", () => {
  const nuovo = { tipo: "da confermare" } as const;
  assert.equal(gpsrAfterVehicleChange({ gpsrManuale: true }, nuovo), undefined);
  assert.deepEqual(gpsrAfterVehicleChange({}, nuovo), nuovo);
  assert.deepEqual(gpsrAfterVehicleChange({ gpsrManuale: false }, { tipo: "esente" }), { tipo: "esente" });
});

test("numero della categoria eBay: solo cifre, vuoto = la sceglie eBay", () => {
  assert.equal(categoriaEbayDa(" 33710 "), "33710");
  assert.equal(categoriaEbayDa(""), "");
  assert.equal(categoriaEbayDa("   "), "");
  assert.equal(categoriaEbayDa("Fari"), undefined);
  assert.equal(categoriaEbayDa("33-710"), undefined);
  assert.equal(categoriaEbayDa("1".repeat(13)), undefined);
});

test("eBay non si attiva con il GPSR da confermare", () => {
  assert.equal(gpsrBlocksEbay({ tipo: "da confermare" }), true);
  assert.equal(gpsrBlocksEbay({ tipo: "esente" }), false);
  assert.equal(gpsrBlocksEbay({ tipo: "produttore", produttore: { ragioneSociale: "X", indirizzo: "Via 1", citta: "Roma", cap: "00100", paese: "IT" } }), false);
});
