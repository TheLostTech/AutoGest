// Lavoro aperto di un modulo, mostrato prima di spegnerlo. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { lavoroAperto } from "./moduli-lavoro.ts";
import type { Order, SalesDoc, Vehicle, WasteMove } from "./types.ts";

const ord = (p: Partial<Order>) => ({ id: "O-1", channel: "banco", partIds: [], amount: 10, status: "pagato", customer: "x", createdAt: "", history: [], ...p }) as Order;
const doc = (p: Partial<SalesDoc>) => ({ id: "P-1", type: "preventivo", at: "", customer: { name: "x" }, lines: [], total: 0, status: "aperto", ...p }) as SalesDoc;
const veh = (p: Partial<Vehicle>) => ({ id: "V-1", dossier: { number: "", kind: "", status: "da registrare" }, ...p }) as Vehicle;
const mv = (p: Partial<WasteMove>) => ({ id: "M-1", at: "", kind: "carico", eer: "16 01 04*", kg: 900, origin: "V-1", note: "", rentri: "da trasmettere", ...p }) as WasteMove;
const vuoto = { orders: [], docs: [], vehicles: [], wasteMoves: [] };

test("lavoroAperto: niente lavoro aperto = nessuna riga", () => {
  for (const m of ["magazzino", "accettazione", "ambiente", "vendite"] as const) assert.deepEqual(lavoroAperto(m, vuoto), []);
});

test("lavoroAperto: vendite, ordini al banco in attesa e preventivi aperti", () => {
  const s = {
    ...vuoto,
    orders: [ord({ status: "in attesa di pagamento" }), ord({ status: "in attesa di pagamento" }), ord({ channel: "negozio", status: "in attesa di pagamento" }), ord({ status: "pagato" })],
    docs: [doc({}), doc({ status: "convertito" }), doc({ type: "fattura", status: "emesso" })],
  };
  assert.deepEqual(lavoroAperto("vendite", s), ["2 ordini al banco in attesa di pagamento (i pezzi restano riservati)", "1 preventivo aperto"]);
});

test("lavoroAperto: vendite al singolare e al plurale", () => {
  const s = { ...vuoto, orders: [ord({ status: "in attesa di pagamento" })], docs: [doc({}), doc({})] };
  assert.deepEqual(lavoroAperto("vendite", s), ["1 ordine al banco in attesa di pagamento (i pezzi restano riservati)", "2 preventivi aperti"]);
});

test("lavoroAperto: accettazione, pratiche iniziate e non radiate", () => {
  const s = {
    ...vuoto,
    vehicles: [
      veh({ conferente: { tipo: "privato", nome: "A" } }),
      veh({ presaInCarico: { at: "", by: "" }, radiazione: { stato: "richiesta" } }),
      veh({ presaInCarico: { at: "", by: "" }, radiazione: { stato: "completata" } }),
      veh({}),
    ],
  };
  assert.deepEqual(lavoroAperto("accettazione", s), ["2 pratiche non concluse"]);
  assert.deepEqual(lavoroAperto("accettazione", { ...vuoto, vehicles: [s.vehicles[0]] }), ["1 pratica non conclusa"]);
});

test("lavoroAperto: ambiente, registrazioni in bozza", () => {
  const s = { ...vuoto, wasteMoves: [mv({}), mv({ numero: 4 }), mv({})] };
  assert.deepEqual(lavoroAperto("ambiente", s), ["2 registrazioni in bozza nel registro rifiuti"]);
  assert.deepEqual(lavoroAperto("ambiente", { ...vuoto, wasteMoves: [mv({})] }), ["1 registrazione in bozza nel registro rifiuti"]);
});
