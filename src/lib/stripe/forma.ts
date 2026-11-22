// Da un abbonamento come lo restituisce Stripe (voci in items.data) alla forma minima SubStripe di abbonamento.ts.
// Pura: i tipi sono strutturali, così il test non dipende dalla libreria.
import { conDisdetta, type SubStripe } from "../abbonamento.ts";
import { prezzo, type Periodo } from "../listino.ts";
import type { Modulo } from "../moduli.ts";

type ProdottoStripe = string | { id: string; deleted?: boolean; metadata?: Record<string, string> | null };

export type SubDaStripe = {
  id: string;
  status: string;
  cancel_at_period_end: boolean;
  cancel_at?: number | null;
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
    cancel_at: s.cancel_at ?? null,
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

// L'abbonamento appena riletto da Stripe si può cambiare? I moduli solo se è active o trialing (anche disdetto);
// la riattivazione solo se è active o trialing e ha la disdetta (a fine periodo o a una data, vedi conDisdetta).
// Tutto il resto: "Abbonamento non attivo".
export function abbonamentoModificabile(s: { status: string; cancel_at_period_end: boolean; cancel_at?: number | null }, azione: "aggiungi" | "togli" | "anteprima" | "riattiva"): boolean {
  if (!IN_CORSO.has(s.status)) return false;
  return azione === "riattiva" ? conDisdetta(s) : true;
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

// Anteprima della fattura: quanto costa subito, IVA esclusa (in centesimi), mai sotto zero. Il totale IVA esclusa
// e non amount_due: un credito del cliente abbassa quello da pagare, non il costo del modulo.
export function importoSenzaTasse(f: { total_excluding_tax: number | null }): number {
  return Math.max(0, f.total_excluding_tax ?? 0);
}

export const PREZZI_DIVERSI = "Prezzi di Stripe diversi dal listino: avvisa l'assistenza";

// Forma minima di un prezzo Stripe, così il test non dipende dalla libreria
export type PrezzoStripe = { unit_amount: number | null; currency: string; recurring: { interval: string } | null; tax_behavior: string | null };

// Il prezzo trovato su Stripe per lookup key va con il listino dell'app? Importo in centesimi, euro, periodo
// (month/year) e IVA esclusa (l'aliquota del 22% si aggiunge sopra). null se va bene, altrimenti cosa non va.
export function differenzaDalListino(p: PrezzoStripe, m: Modulo, periodo: Periodo): string | null {
  const atteso = prezzo(m, periodo);
  const intervallo = periodo === "anno" ? "year" : "month";
  const no: string[] = [];
  if (p.unit_amount !== atteso) no.push(`importo ${p.unit_amount ?? "assente"} invece di ${atteso}`);
  if (p.currency !== "eur") no.push(`valuta ${p.currency} invece di eur`);
  if (p.recurring?.interval !== intervallo) no.push(`periodo ${p.recurring?.interval ?? "assente"} invece di ${intervallo}`);
  if (p.tax_behavior !== "exclusive") no.push(`IVA ${p.tax_behavior ?? "non indicata"} invece di exclusive`);
  return no.length ? no.join(", ") : null;
}

// Stripe non trova il cliente o l'abbonamento (cancellati dalla dashboard, conto di prova ripulito).
export function risorsaMancante(e: unknown): boolean {
  if (!e || typeof e !== "object") return false;
  const x = e as { type?: unknown; code?: unknown };
  return x.type === "StripeInvalidRequestError" && x.code === "resource_missing";
}
