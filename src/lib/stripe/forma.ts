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

const IN_CORSO = new Set(["active", "trialing"]);

// L'abbonamento appena riletto da Stripe si può cambiare? I moduli solo se è active o trialing (anche disdetto a fine
// periodo); la riattivazione solo se è active o trialing e ha la disdetta. Tutto il resto: "Abbonamento non attivo".
export function abbonamentoModificabile(s: { status: string; cancel_at_period_end: boolean }, azione: "aggiungi" | "togli" | "anteprima" | "riattiva"): boolean {
  if (!IN_CORSO.has(s.status)) return false;
  return azione === "riattiva" ? s.cancel_at_period_end : true;
}

// Stripe ha rifiutato il pagamento (carta rifiutata, autenticazione richiesta, fattura non pagata): errore della
// carta o risposta 402. Gli altri errori (rete, richiesta sbagliata) non sono un pagamento rifiutato.
export function pagamentoRifiutato(e: unknown): boolean {
  if (!e || typeof e !== "object") return false;
  const x = e as { type?: unknown; statusCode?: unknown };
  return x.type === "StripeCardError" || x.statusCode === 402;
}

export const TROPPI_PERIODI = "Stripe fa avanzare l'orologio al massimo di due periodi alla volta";
export const OROLOGIO_IN_AVANZAMENTO = "L'orologio sta già avanzando";

// Un rifiuto di Stripe all'avanzamento dell'orologio di prova che si spiega a chi prova: oltre due periodi
// dell'abbonamento più corto (400) oppure orologio che sta già avanzando (409). Gli altri errori: null (502).
// Stripe non dà un codice per questi casi: si riconoscono dal messaggio della richiesta rifiutata.
export function rifiutoAvanzamento(e: unknown): { stato: number; messaggio: string } | null {
  if (!e || typeof e !== "object") return null;
  const x = e as { type?: unknown; statusCode?: unknown; message?: unknown };
  if (x.type !== "StripeInvalidRequestError" || x.statusCode !== 400 || typeof x.message !== "string") return null;
  if (/interval/i.test(x.message)) return { stato: 400, messaggio: TROPPI_PERIODI };
  if (/advancing/i.test(x.message)) return { stato: 409, messaggio: OROLOGIO_IN_AVANZAMENTO };
  return null;
}

// Anteprima della fattura: quanto si paga subito, IVA esclusa (in centesimi), mai sotto zero.
export function importoSenzaTasse(f: { amount_due: number; total_taxes: { amount: number }[] | null }): number {
  const tasse = (f.total_taxes ?? []).reduce((s, t) => s + t.amount, 0);
  return Math.max(0, f.amount_due - tasse);
}
