import { test } from "node:test";
import assert from "node:assert/strict";
import { subMinima } from "./forma.ts";

const voce = (product: unknown, interval: string | null, fine = 1_800_000_000) => ({
  price: { recurring: interval ? { interval } : null, product },
  current_period_end: fine,
});

test("subMinima: le voci passano da items.data a una lista, con il prodotto espanso", () => {
  const s = subMinima({
    id: "sub_1", status: "active", cancel_at_period_end: false, created: 100,
    items: { data: [voce({ id: "prod_1", metadata: { modulo: "ambiente" } }, "month", 123)] },
  });
  assert.deepEqual(s, {
    id: "sub_1", status: "active", cancel_at_period_end: false, created: 100,
    items: [{ price: { recurring: { interval: "month" }, product: { metadata: { modulo: "ambiente" } } }, current_period_end: 123 }],
  });
});

test("subMinima: anno resta anno, ogni altro intervallo vale mese", () => {
  const s = subMinima({ id: "s", status: "active", cancel_at_period_end: false, created: 1, items: { data: [voce("prod_x", "year"), voce("prod_y", "week"), voce("prod_z", null)] } });
  assert.deepEqual(s.items.map((i) => i.price.recurring), [{ interval: "year" }, { interval: "month" }, null]);
});

test("subMinima: prodotto non espanso o cancellato resta una stringa (il modulo si scarta)", () => {
  const s = subMinima({ id: "s", status: "active", cancel_at_period_end: false, created: 1, items: { data: [voce("prod_a", "month"), voce({ id: "prod_b", deleted: true }, "month")] } });
  assert.deepEqual(s.items.map((i) => i.price.product), ["prod_a", "prod_b"]);
});

test("subMinima: metadata assente diventa un oggetto vuoto", () => {
  const s = subMinima({ id: "s", status: "active", cancel_at_period_end: false, created: 1, items: { data: [voce({ id: "prod_c" }, "month")] } });
  assert.deepEqual(s.items[0].price.product, { metadata: {} });
});
