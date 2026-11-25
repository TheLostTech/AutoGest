// Regole pure per Stripe: che modalità danno le chiavi, da dove si prende l'azienda di un avviso,
// quando si risincronizza. Nessun accesso a rete o disco: si provano con i test (spec registrazione-pagamento, 5, 7, 9).
import { ABBONAMENTO_NUOVO, type Abbonamento } from "../abbonamento.ts";

export type ModalitaStripe = "prova" | "live" | "spenta";

/** sk_test_/rk_test_ → prova; sk_live_/rk_live_ → live solo con STRIPE_LIVE=1; tutto il resto (o niente) → spenta. */
export function modalitaDaChiave(chiave: string | undefined, live: string | undefined): ModalitaStripe {
  if (!chiave) return "spenta";
  if (chiave.startsWith("sk_test_") || chiave.startsWith("rk_test_")) return "prova";
  if (chiave.startsWith("sk_live_") || chiave.startsWith("rk_live_")) return live === "1" ? "live" : "spenta";
  return "spenta";
}

/**
 * Un avviso firmato ma di un altro ambiente (prova ↔ live, per esempio lo stesso indirizzo registrato nei due conti):
 * si scarta. Con Stripe spento decide la route (503, così Stripe ritenta quando la chiave c'è).
 */
export function eventoDiUnAltroAmbiente(livemode: boolean, m: ModalitaStripe): boolean {
  return m !== "spenta" && livemode !== (m === "live");
}

/**
 * Indirizzo per i ritorni da Stripe (Checkout, portale): l'Origin della richiesta, cioè l'indirizzo da cui il titolare
 * usa il gestionale e dove ha il cookie della sessione (le route lo controllano già contro Host). Senza un Origin valido:
 * INDIRIZZO_GESTIONALE, poi l'indirizzo della richiesta.
 */
export function origineRitorno(origin: string | null, fissa: string | undefined, urlRichiesta: string): string {
  if (origin) {
    try {
      const u = new URL(origin);
      if (u.protocol === "https:" || u.protocol === "http:") return u.origin;
    } catch {}
  }
  const f = fissa?.trim().replace(/\/+$/, "");
  return f || new URL(urlRichiesta).origin;
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

// Stripe rifiuta un'espansione con più di quattro proprietà ("an expand string can contain no more than four properties").
export function espansioneValida(e: string): boolean {
  const parti = e.split(".");
  return parti.length <= 4 && parti.every((p) => p.length > 0);
}

/** Tutte le espansioni che il server chiede a Stripe: il test controlla che stiano nel limite. */
export const ESPANSIONI = {
  // subscriptions.retrieve dell'abbonamento scelto: i prodotti servono per metadata.modulo
  abbonamento: ["items.data.price.product"],
  // checkout.sessions.list delle sessioni completate: lo stato dell'abbonamento dice se il pagamento lento è finito
  sessioni: ["data.subscription"],
} as const;

/** Le aziende scritte con chiavi di prova non vanno con le chiavi vere (e viceversa): i loro id non esistono lì. Spento: nessuna. */
export function stessoAmbiente(a: Abbonamento, m: ModalitaStripe): boolean {
  return m !== "spenta" && a.prova === (m === "prova");
}

/**
 * Abbonamento di un altro ambiente Stripe, mai pagato, rifatto da zero per l'ambiente `m` (azione "azzera-e-crea"):
 * si tolgono i dati Stripe dell'altro ambiente, non la prova. La fine della prova resta; lo spostamento degli strumenti
 * di prova resta solo con le chiavi di prova, così un'azienda passata alle chiavi vere non lo porta con sé.
 */
export function abbonamentoAzzerato(prima: Abbonamento | null, m: ModalitaStripe, ora: number): Abbonamento {
  const prova = m === "prova";
  return { ...ABBONAMENTO_NUOVO(prova, ora), fineProva: prima?.fineProva ?? null, spostamentoProva: prova ? (prima?.spostamentoProva ?? 0) : 0 };
}

export type AzioneCliente = "riusa" | "crea" | "azzera-e-crea" | "rifiuta";

/**
 * Cosa fa clientePer con l'abbonamento salvato. Di un altro ambiente e mai pagato: si riparte da zero nell'ambiente
 * di adesso. Di un altro ambiente e già pagato: si rifiuta (serve l'assistenza, i soldi stanno nell'altro conto).
 */
export function azioneCliente(a: Abbonamento | null, m: ModalitaStripe): AzioneCliente {
  if (m === "spenta") return "rifiuta";
  if (!a) return "crea";
  if (!stessoAmbiente(a, m)) return a.pagatoAlmenoUnaVolta ? "rifiuta" : "azzera-e-crea";
  return a.customerId ? "riusa" : "crea";
}

const QUINDICI_SECONDI = 15_000;

/** Sincronizzazioni chieste dal browser: niente Stripe se l'ultimo tentativo per l'azienda è di meno di 15 secondi fa. */
export function sincronizzazioneLimitata(ultimoTentativo: number | null, ora: number): boolean {
  return ultimoTentativo !== null && ora - ultimoTentativo < QUINDICI_SECONDI;
}

// Forma minima di una sessione Checkout (lista con data.subscription espanso), così il test non dipende dalla libreria
export type SessioneCheckout = {
  id: string;
  customer: string | null;
  status: string | null; // open, complete, expired
  payment_status: string; // paid, unpaid, no_payment_required
  subscription: string | { status: string } | null;
  metadata: Record<string, string> | null;
};

// Abbonamenti finiti: un pagamento lento fallito lascia la sessione "complete" e "unpaid" per sempre, ma non è più in corso
const FINITI = new Set(["incomplete_expired", "canceled", "unpaid"]);

/**
 * C'è già un pagamento del cliente in attesa di Stripe? Un abbonamento `incomplete` (primo addebito non ancora riuscito),
 * oppure una sessione Checkout completata ma non ancora pagata (SEPA o simili) il cui abbonamento non è finito.
 * Allora un secondo Checkout creerebbe un secondo abbonamento. Conta solo ciò che è di questo cliente.
 */
export function pagamentoInCorso(cliente: string, abbonamenti: { customer: string; status: string }[], sessioni: SessioneCheckout[]): boolean {
  if (abbonamenti.some((a) => a.customer === cliente && a.status === "incomplete")) return true;
  return sessioni.some((s) => {
    if (s.customer !== cliente || s.status !== "complete" || s.payment_status !== "unpaid") return false;
    return !(s.subscription && typeof s.subscription === "object" && FINITI.has(s.subscription.status));
  });
}

/** Le sessioni Checkout aperte di questo cliente da far scadere prima di crearne una nuova, tranne quella con la stessa chiave (doppio clic). */
export function sessioniDaScadere(cliente: string, sessioni: SessioneCheckout[], chiave: string): string[] {
  return sessioni.filter((s) => s.customer === cliente && s.status === "open" && s.metadata?.chiave !== chiave).map((s) => s.id);
}

/** Chiave di idempotenza del Checkout: stessa azienda, stessa scelta e stesso minuto danno la stessa sessione. */
export function chiaveCheckout(aziendaId: string, periodo: string, moduli: string[], ora: number): string {
  return `checkout-${aziendaId}-${periodo}-${[...moduli].sort().join("+")}-${Math.floor(ora / 60_000)}`;
}

const UN_ORA = 3_600_000;

/** Lo stato si rilegge da Stripe se lo si chiede, o per il titolare quando l'ultimo aggiornamento ha più di un'ora. */
export function daSincronizzare(x: { richiesta: boolean; titolare: boolean; aggiornato: number; ora: number }): boolean {
  return x.richiesta || (x.titolare && x.ora - x.aggiornato > UN_ORA);
}
