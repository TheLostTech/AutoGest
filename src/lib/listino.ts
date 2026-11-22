// Listino del 22/11/2026 (spec moduli-a-pagamento, sezione "Listino"). Importi in centesimi, IVA esclusa.
// Regola di Alessandro: i prezzi finiscono in 9, mai cifre tonde; l'annuale costa circa il 10% in meno e si paga in un'unica soluzione.
import type { Modulo } from "./moduli";

export type Periodo = "mese" | "anno";

export const LISTINO: Record<Modulo, { nome: string; mese: number; anno: number }> = {
  magazzino: { nome: "Magazzino", mese: 29990, anno: 319900 },
  accettazione: { nome: "Pratiche", mese: 1990, anno: 21900 },
  ambiente: { nome: "Ambiente", mese: 4990, anno: 53900 },
  vendite: { nome: "Banco", mese: 4990, anno: 53900 },
};

/** Commissione sui pezzi venduti online (eBay, marketplace, negozio online); al banco niente */
export const COMMISSIONE_ONLINE = 0.08;

export const prezzo = (m: Modulo, p: Periodo) => LISTINO[m][p];

/** Quanto si risparmia in un anno pagando l'annuale invece di dodici mensili */
export const risparmioAnnuale = (m: Modulo) => LISTINO[m].mese * 12 - LISTINO[m].anno;

export const totale = (moduli: Modulo[], p: Periodo) => moduli.reduce((s, m) => s + prezzo(m, p), 0);

/** 29990 → "299,90 €", 319900 → "3.199 €": senza decimali quando sono zero */
export function euro(centesimi: number): string {
  const intero = centesimi % 100 === 0;
  return new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: intero ? 0 : 2,
    maximumFractionDigits: intero ? 0 : 2,
    useGrouping: "always",
  }).format(centesimi / 100);
}
