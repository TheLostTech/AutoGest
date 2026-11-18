// Modello degli annunci con più pezzi. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  groupKey,
  isWithdrawn,
  listingOf,
  nextToShip,
  negozioStato,
  normalizeOem,
  partsOf,
  placementFor,
  quantityOf,
} from "./annunci.ts";
import type { Annuncio, Part } from "./types.ts";

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
    listing: "non pubblicato",
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
