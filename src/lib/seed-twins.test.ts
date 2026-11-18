// Pezzi gemelli dei dati demo: un annuncio con più pezzi uguali deve esserci sempre. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { twinSource, withTwins, type TwinCatalog } from "./seed-twins.ts";
import { groupKey } from "./annunci.ts";
import type { Part } from "./types.ts";

let n = 0;
function part(over: Partial<Part> = {}): Part {
  n += 1;
  return {
    id: `R-${String(n).padStart(6, "0")}`,
    vehicleId: "V-1",
    typeId: "cerchio",
    description: "Cerchio",
    condition: "B",
    status: "disponibile",
    oemVerified: false,
    photos: ["/renders/cerchio.png"],
    labelPrints: 1,
    price: 60,
    location: { mag: "M1", corsia: "T01", scaffale: "101", ripiano: "A" },
    createdAt: "2026-01-01T10:00:00.000Z",
    createdBy: "test",
    ...over,
  };
}

const cat: TwinCatalog = { oem: "59 755.443", manufacturer: "Ronal", platforms: ["P1", "P2"], source: "Catalogo" };
const catalogOf = (p: Part) => (p.typeId === "batteria" ? null : cat);
const shippable = (typeId: string) => typeId !== "porta";

test("sceglie prima un cerchio disponibile con codice di catalogo", () => {
  const alt = part({ typeId: "alternatore" });
  const venduto = part({ status: "venduto" });
  const cerchio = part();
  assert.equal(twinSource([alt, venduto, cerchio], catalogOf, shippable)?.id, cerchio.id);
});

test("senza cerchi ripiega su un tipo spedibile con codice di catalogo", () => {
  const porta = part({ typeId: "porta" });
  const batteria = part({ typeId: "batteria" });
  const alt = part({ typeId: "alternatore" });
  assert.equal(twinSource([porta, batteria, alt], catalogOf, shippable)?.id, alt.id);
  assert.equal(twinSource([porta, batteria], catalogOf, shippable), undefined);
});

test("il pezzo non verificato diventa verificato dal catalogo e i gemelli hanno la sua stessa chiave", () => {
  const src = part();
  const { source, twins } = withTwins(src, cat, ["R-900001", "R-900002"]);
  assert.equal(source.oemVerified, true);
  assert.equal(source.oem, cat.oem);
  assert.deepEqual(source.compat, { platforms: ["P1", "P2"], source: "Catalogo", verified: true });
  const key = groupKey(source, true);
  assert.ok(key);
  assert.equal(twins.length, 2);
  for (const t of twins) assert.equal(groupKey(t, true), key);
  assert.deepEqual(twins.map((t) => t.id), ["R-900001", "R-900002"]);
  // entrano dopo l'originale, che resta il primo a partire
  assert.ok(twins.every((t) => t.createdAt > source.createdAt));
  assert.equal(twins[0].price, source.price);
});

test("un pezzo già verificato resta com'è", () => {
  const src = part({ oem: "ABC", oemVerified: true });
  assert.equal(withTwins(src, cat, ["R-900003"]).source, src);
});
