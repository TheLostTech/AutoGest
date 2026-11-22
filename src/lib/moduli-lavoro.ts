// Lavoro ancora aperto di un modulo: si mostra prima di spegnerlo. Spegnere non cambia nulla nei dati.
// Modulo puro: solo import type (si prova con node --test).
import type { Order, SalesDoc, Vehicle, WasteMove } from "./types";
import type { Modulo } from "./moduli";

const conta = (n: number, uno: string, tanti: string) => (n ? [`${n} ${n === 1 ? uno : tanti}`] : []);

export function lavoroAperto(m: Modulo, s: { orders: Order[]; docs: SalesDoc[]; vehicles: Vehicle[]; wasteMoves: WasteMove[] }): string[] {
  if (m === "vendite")
    return [
      ...conta(
        s.orders.filter((o) => o.channel === "banco" && o.status === "in attesa di pagamento").length,
        "ordine al banco in attesa di pagamento (i pezzi restano riservati)",
        "ordini al banco in attesa di pagamento (i pezzi restano riservati)",
      ),
      ...conta(s.docs.filter((d) => d.type === "preventivo" && d.status === "aperto").length, "preventivo aperto", "preventivi aperti"),
    ];
  if (m === "accettazione")
    return conta(
      s.vehicles.filter((v) => (v.conferente || v.presaInCarico) && v.radiazione?.stato !== "completata").length,
      "pratica non conclusa",
      "pratiche non concluse",
    );
  if (m === "ambiente")
    // In bozza = senza numero progressivo (come isDraft in periodo.ts)
    return conta(s.wasteMoves.filter((x) => x.numero === undefined).length, "registrazione in bozza nel registro rifiuti", "registrazioni in bozza nel registro rifiuti");
  return [];
}
