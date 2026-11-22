// Da un abbonamento come lo restituisce Stripe (voci in items.data) alla forma minima SubStripe di abbonamento.ts.
// Pura: i tipi sono strutturali, così il test non dipende dalla libreria.
import type { SubStripe } from "../abbonamento.ts";
import type { Modulo } from "../moduli.ts";

type ProdottoStripe = string | { id: string; deleted?: boolean; metadata?: Record<string, string> | null };

export type SubDaStripe = {
  id: string;
  status: string;
  cancel_at_period_end: boolean;
  created: number;
  items: { data: { price: { recurring: { interval: string } | null; product: ProdottoStripe | unknown }; current_period_end: number }[] };
};

function prodotto(p: unknown): SubStripe["items"][number]["price"]["product"] {
  if (typeof p === "string") return p;
  const o = p as { id?: string; deleted?: boolean; metadata?: Record<string, string> | null } | null;
  // Prodotto cancellato: niente metadata, il modulo si scarta come per un id non espanso
  if (!o || o.deleted) return o?.id ?? "";
  return { metadata: o.metadata ?? {} };
}

export function subMinima(s: SubDaStripe): SubStripe {
  return {
    id: s.id,
    status: s.status,
    cancel_at_period_end: s.cancel_at_period_end,
    created: s.created,
    items: s.items.data.map((it) => ({
      price: {
        recurring: it.price.recurring ? { interval: it.price.recurring.interval === "year" ? "year" : "month" } : null,
        product: prodotto(it.price.product),
      },
      current_period_end: it.current_period_end,
    })),
  };
}

// La voce dell'abbonamento di un modulo: quella il cui prodotto (espanso) ha metadata.modulo uguale all'id dell'app.
export function voceDelModulo(voci: { id: string; price: { product: unknown } }[], modulo: Modulo): string | null {
  for (const v of voci) {
    const p = prodotto(v.price.product);
    if (typeof p !== "string" && p.metadata?.modulo === modulo) return v.id;
  }
  return null;
}

// Anteprima della fattura: quanto si paga subito, IVA esclusa (in centesimi), mai sotto zero.
export function importoSenzaTasse(f: { amount_due: number; total_taxes: { amount: number }[] | null }): number {
  const tasse = (f.total_taxes ?? []).reduce((s, t) => s + t.amount, 0);
  return Math.max(0, f.amount_due - tasse);
}
