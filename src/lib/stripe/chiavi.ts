// Regole pure per Stripe: che modalità danno le chiavi, da dove si prende l'azienda di un avviso,
// quando si risincronizza. Nessun accesso a rete o disco: si provano con i test (spec registrazione-pagamento, 5, 7, 9).

export type ModalitaStripe = "prova" | "live" | "spenta";

/** sk_test_/rk_test_ → prova; sk_live_/rk_live_ → live solo con STRIPE_LIVE=1; tutto il resto (o niente) → spenta. */
export function modalitaDaChiave(chiave: string | undefined, live: string | undefined): ModalitaStripe {
  if (!chiave) return "spenta";
  if (chiave.startsWith("sk_test_") || chiave.startsWith("rk_test_")) return "prova";
  if (chiave.startsWith("sk_live_") || chiave.startsWith("rk_live_")) return live === "1" ? "live" : "spenta";
  return "spenta";
}

/** La riga nella Piattaforma. */
export function etichettaStripe(m: ModalitaStripe): string {
  if (m === "prova") return "Stripe: prova (AutoLost demo)";
  if (m === "live") return "Stripe: live";
  return "Stripe: spento";
}

/** Gli avvisi che si ascoltano (spec, sezione 5). Gli altri ricevono 200 e non fanno nulla. */
export const EVENTI_ASCOLTATI = new Set([
  "checkout.session.completed",
  "customer.subscription.created",
  "customer.subscription.updated",
  "customer.subscription.deleted",
  "invoice.paid",
  "invoice.payment_failed",
  "test_helpers.test_clock.ready",
]);

// Forma minima di un avviso, così il test non dipende dalla libreria
export type EventoMinimo = {
  type: string;
  data: { object: { id?: string; metadata?: Record<string, string> | null; client_reference_id?: string | null; customer?: string | { id: string } | null } & Record<string, unknown> };
};

export type DaCercare = { azienda: string } | { cliente: string } | { orologio: string };

/**
 * Da dove si arriva all'azienda di un avviso: metadata.azienda (o client_reference_id di Checkout) se c'è,
 * altrimenti il cliente da rileggere; per l'orologio pronto, l'orologio. null: niente da fare.
 */
export function aziendaDaEvento(e: EventoMinimo): DaCercare | null {
  if (!EVENTI_ASCOLTATI.has(e.type)) return null;
  const o = e.data.object;
  if (e.type === "test_helpers.test_clock.ready") return o.id ? { orologio: o.id } : null;
  const azienda = o.metadata?.azienda || o.client_reference_id;
  if (azienda) return { azienda };
  const c = o.customer;
  const cliente = typeof c === "string" ? c : c?.id;
  return cliente ? { cliente } : null;
}

const UN_ORA = 3_600_000;

/** Lo stato si rilegge da Stripe se lo si chiede, o per il titolare quando l'ultimo aggiornamento ha più di un'ora. */
export function daSincronizzare(x: { richiesta: boolean; titolare: boolean; aggiornato: number; ora: number }): boolean {
  return x.richiesta || (x.titolare && x.ora - x.aggiornato > UN_ORA);
}
