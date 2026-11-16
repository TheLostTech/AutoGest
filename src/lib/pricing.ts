// Prezzi: suggerimento dell'usato a partire dal prezzo del nuovo, e listini per tipo di cliente.
// Percentuali dimostrative: ogni impianto le configura (es. con le fasce L/T/B/2/3/4 del gestionale attuale).
import type { Condition } from "./types";

export interface Listino {
  id: string;
  name: string;
  pct: number; // variazione sul prezzo base, es. -15
}

export const DEFAULT_LISTINI: Listino[] = [
  { id: "base", name: "Privati", pct: 0 },
  { id: "officine", name: "Officine", pct: -15 },
  { id: "ricambisti", name: "Ricambisti", pct: -25 },
];

// Quota del prezzo del nuovo per condizione del pezzo
export const USED_SHARE: Record<Condition, number> = { A: 0.45, B: 0.35, C: 0.25, D: 0.15 };

export function suggestUsedPrice(newPrice: number, condition: Condition, inStock: number, max: number) {
  const crowded = inStock >= max; // magazzino già pieno di questa tipologia: prezzo più aggressivo
  const p = newPrice * USED_SHARE[condition] * (crowded ? 0.9 : 1);
  return Math.max(5, Math.round(p / 5) * 5);
}

export const listPrice = (base: number | undefined, l: Listino | undefined) => (base === undefined ? undefined : Math.round(base * (1 + (l?.pct ?? 0) / 100)));
