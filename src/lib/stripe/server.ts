// Stripe sul server: chiave, cliente (in prova dentro un orologio di prova), prezzi, IVA e sincronizzazione
// dell'abbonamento. Solo server. Spec registrazione-pagamento, sezioni 4, 5, 7, 9.
import Stripe from "stripe";
import { ABBONAMENTO_NUOVO, abbonamentoDaStripe, lookupKey, rifiutoCambio, righeCambio, scegli, type Abbonamento, type RichiestaModuli } from "@/lib/abbonamento";
import { aggiornaAbbonamento, leggiAbbonamento } from "@/lib/abbonamento-server";
import { aggiungiEventi } from "@/lib/archivio-azienda";
import type { Periodo } from "@/lib/listino";
import type { Modulo } from "@/lib/moduli";
import { azioneCliente, ESPANSIONI, modalitaDaChiave, pagamentoInCorso, sessioniDaScadere, sincronizzazioneLimitata, stessoAmbiente, type ModalitaStripe, type SessioneCheckout } from "./chiavi";
import { creaFila, type Fila } from "./fila";
import { abbonamentoModificabile, importoSenzaTasse, pagamentoRifiutato, subMinima, voceDelModulo, type SubDaStripe } from "./forma";

// Versione dell'API fissata: quella che porta con sé stripe@23.2.0 (Stripe.API_VERSION). Si cambia insieme alla libreria.
const VERSIONE_API = "2026-11-18.endive";

type Globali = typeof globalThis & {
  __stripe?: { chiave: string; client: Stripe };
  __clientiStripe?: Map<string, Promise<string>>;
  __filaSincronizzazioni?: Fila<Abbonamento>;
  __tentativiSincronizzazione?: Map<string, number>;
  __ivaStripe?: Promise<string>;
  __checkoutInCorso?: Map<string, Promise<unknown>>;
  __cambiModuliInCorso?: Map<string, Promise<unknown>>;
};
const g = globalThis as Globali;

export function modalitaStripe(): ModalitaStripe {
  return modalitaDaChiave(process.env.STRIPE_SECRET_KEY, process.env.STRIPE_LIVE);
}

/** Il client Stripe. Lancia se la modalità è "spenta" (chiave assente, sbagliata o live senza STRIPE_LIVE=1). */
export function stripe(): Stripe {
  const chiave = process.env.STRIPE_SECRET_KEY;
  if (modalitaStripe() === "spenta" || !chiave) throw new Error("Stripe non configurato: manca STRIPE_SECRET_KEY di prova (o STRIPE_LIVE=1 con la chiave vera).");
  if (g.__stripe?.chiave !== chiave) {
    g.__stripe = { chiave, client: new Stripe(chiave, { apiVersion: VERSIONE_API, appInfo: { name: "AutoLost" } }) };
  }
  return g.__stripe.client;
}

const ALTRO_AMBIENTE = "Abbonamento di un altro ambiente Stripe: serve l'assistenza";

/**
 * Il cliente Stripe dell'azienda: quello salvato in abbonamento.json, altrimenti uno nuovo con metadata.azienda.
 * In prova nasce dentro un orologio di prova tutto suo, che parte da adesso. Due chiamate insieme aspettano lo stesso cliente.
 * Abbonamento di un altro ambiente (prova ↔ live): mai pagato si riparte da zero, pagato si rifiuta (vedi azioneCliente).
 */
export function clientePer(aziendaId: string, nome: string, email: string): Promise<string> {
  const inCorso = (g.__clientiStripe ??= new Map());
  const gia = inCorso.get(aziendaId);
  if (gia) return gia;
  const run = (async () => {
    const s = stripe(); // spento: lancia con il messaggio di configurazione
    const m = modalitaStripe();
    const a = await leggiAbbonamento(aziendaId);
    const azione = azioneCliente(a, m);
    if (azione === "riusa" && a?.customerId) return a.customerId;
    if (azione === "rifiuta") throw new Error(ALTRO_AMBIENTE);
    if (azione === "azzera-e-crea") console.warn("Abbonamento di un altro ambiente Stripe, mai pagato: si riparte da zero", aziendaId, a?.customerId);
    const prova = m === "prova";
    const ora = Date.now();
    const orologio = prova ? await s.testHelpers.testClocks.create({ frozen_time: Math.floor(ora / 1000), name: aziendaId }) : null;
    const cliente = await s.customers.create({
      name: nome,
      email,
      metadata: { azienda: aziendaId },
      ...(orologio ? { test_clock: orologio.id } : {}),
    });
    const ids = { customerId: cliente.id, orologioId: orologio?.id ?? null, oraOrologio: orologio ? orologio.frozen_time * 1000 : null };
    // Si decide di nuovo sul file appena letto, dentro il blocco: un altro processo può averlo cambiato
    const scritto = await aggiornaAbbonamento(aziendaId, (prima) => {
      switch (azioneCliente(prima, m)) {
        case "riusa":
          console.warn("Cliente Stripe già presente: quello nuovo resta inutilizzato", aziendaId, cliente.id);
          return prima!;
        case "rifiuta":
          throw new Error(ALTRO_AMBIENTE);
        case "azzera-e-crea":
          return { ...ABBONAMENTO_NUOVO(prova, ora), ...ids };
        case "crea":
          return { ...(prima ?? ABBONAMENTO_NUOVO(prova, ora)), ...ids };
      }
    });
    return scritto.customerId ?? cliente.id;
  })();
  inCorso.set(aziendaId, run);
  void run.then(
    () => inCorso.delete(aziendaId),
    () => inCorso.delete(aziendaId),
  );
  return run;
}

/** I price id dei moduli per il periodo, cercati per lookup key (<nomeStripe>_mese / _anno), nello stesso ordine. */
export async function prezziPer(moduli: Modulo[], periodo: Periodo): Promise<string[]> {
  const chiavi = moduli.map((m) => lookupKey(m, periodo));
  if (!chiavi.length) return [];
  const r = await stripe().prices.list({ lookup_keys: chiavi, active: true, limit: 100 });
  const perChiave = new Map(r.data.map((p) => [p.lookup_key, p.id]));
  return chiavi.map((k) => {
    const id = perChiave.get(k);
    if (!id) throw new Error(`Prezzo Stripe mancante: lookup key ${k}`);
    return id;
  });
}

/** L'aliquota fissa "IVA 22%" esclusiva, marcata con metadata.autolost = "iva22": si trova o si crea una volta sola. */
export function aliquotaIva(): Promise<string> {
  if (g.__ivaStripe) return g.__ivaStripe;
  const run = (async () => {
    const s = stripe();
    for await (const t of s.taxRates.list({ active: true, limit: 100 })) {
      if (t.metadata?.autolost === "iva22") return t.id;
    }
    const t = await s.taxRates.create({
      display_name: "IVA 22%",
      percentage: 22,
      inclusive: false,
      country: "IT",
      jurisdiction: "IT",
      tax_type: "vat",
      metadata: { autolost: "iva22" },
    });
    return t.id;
  })();
  g.__ivaStripe = run;
  // Un errore non resta in memoria: la prossima chiamata riprova
  run.catch(() => {
    if (g.__ivaStripe === run) g.__ivaStripe = undefined;
  });
  return run;
}

async function rileggi(aziendaId: string): Promise<Abbonamento> {
  const prima = await leggiAbbonamento(aziendaId);
  if (!prima) return ABBONAMENTO_NUOVO(modalitaStripe() !== "live", Date.now());
  // Le aziende scritte con chiavi di prova non si sincronizzano con le chiavi vere (e viceversa): i loro id non esistono lì.
  if (!prima.customerId || !stessoAmbiente(prima, modalitaStripe())) return prima;
  const s = stripe();
  // Elenco senza espansioni (data.items.data.price.product sarebbero 5 livelli: Stripe ne accetta 4), poi si rilegge
  // solo l'abbonamento scelto con i prodotti, che servono per metadata.modulo. Gli altri non contano per lo stato.
  const [subs, orologio] = await Promise.all([
    s.subscriptions.list({ customer: prima.customerId, status: "all", limit: 100 }),
    prima.orologioId ? s.testHelpers.testClocks.retrieve(prima.orologioId) : Promise.resolve(null),
  ]);
  const scelto = scegli(subs.data.map((x) => subMinima(x as unknown as SubDaStripe)));
  // Allo stato si passa solo l'abbonamento riletto: lo stesso che sceglie scegli, ora con i prodotti espansi
  const pieno = scelto ? subMinima((await s.subscriptions.retrieve(scelto.id, { expand: [...ESPANSIONI.abbonamento] })) as unknown as SubDaStripe) : null;
  let righe: string[] = [];
  const dopo = await aggiornaAbbonamento(aziendaId, (cur) => {
    const base = cur ?? prima;
    const nuovo = abbonamentoDaStripe(pieno ? [pieno] : [], base, Date.now(), orologio ? orologio.frozen_time * 1000 : null);
    righe = righeCambio(base, nuovo);
    return nuovo;
  });
  if (righe.length) {
    try {
      await aggiungiEventi(aziendaId, righe.map((action) => ({ user: "Stripe", role: "sistema", device: "Stripe", entity: "sistema", entityId: aziendaId, action })));
    } catch (e) {
      console.error("Registro attività non aggiornato", aziendaId, righe, e);
    }
  }
  return dopo;
}

const fila = (g.__filaSincronizzazioni ??= creaFila<Abbonamento>());
// Ultimo tentativo di sincronizzazione per azienda (riuscito o no): separato da `aggiornato`, così uno Stripe che
// sbaglia non viene martellato.
const tentativi = (g.__tentativiSincronizzazione ??= new Map<string, number>());

/**
 * Rilegge da Stripe l'abbonamento corrente del cliente e riscrive abbonamento.json. Una per volta per azienda, così una
 * lettura vecchia non scrive sopra una più nuova; chi arriva mentre una è in coda e non ancora partita riusa quella.
 * Mai limitata (avvisi di Stripe, ritorno da Checkout). Lancia se Stripe non risponde (per il webhook: 500, Stripe ritenta).
 */
export function sincronizzaOLancia(aziendaId: string): Promise<Abbonamento> {
  return fila.metti(aziendaId, () => {
    tentativi.set(aziendaId, Date.now());
    return rileggi(aziendaId);
  });
}

const salvato = async (aziendaId: string) => (await leggiAbbonamento(aziendaId)) ?? ABBONAMENTO_NUOVO(modalitaStripe() !== "live", Date.now());

// Stati con un abbonamento in corso: niente nuovo Checkout (i moduli si aggiungono da Abbonamento)
export const STATI_IN_CORSO = new Set<Abbonamento["stato"]>(["attivo", "in-ritardo", "disdetto"]);

const checkoutInCorso = (g.__checkoutInCorso ??= new Map<string, Promise<unknown>>());
const cambiInCorso = (g.__cambiModuliInCorso ??= new Map<string, Promise<unknown>>());

// Un lavoro per volta per azienda nella mappa: quello dopo parte quando quello prima è finito, riuscito o no.
function unoAllaVolta<T>(mappa: Map<string, Promise<unknown>>, aziendaId: string, lavoro: () => Promise<T>): Promise<T> {
  const prima = mappa.get(aziendaId) ?? Promise.resolve();
  const run = prima.then(lavoro, lavoro);
  const fine = run.catch(() => undefined);
  mappa.set(aziendaId, fine);
  void fine.then(() => {
    if (mappa.get(aziendaId) === fine) mappa.delete(aziendaId);
  });
  return run;
}

/**
 * Un Checkout per volta per azienda: due schede che pagano insieme non creano due sessioni aperte. Il lavoro dopo parte
 * quando quello prima è finito, riuscito o no.
 */
export function unCheckoutAllaVolta<T>(aziendaId: string, lavoro: () => Promise<T>): Promise<T> {
  return unoAllaVolta(checkoutInCorso, aziendaId, lavoro);
}

/** Un cambio di moduli (o una riattivazione) per volta per azienda: due schede non aggiungono lo stesso modulo due volte. */
export function unCambioAllaVolta<T>(aziendaId: string, lavoro: () => Promise<T>): Promise<T> {
  return unoAllaVolta(cambiInCorso, aziendaId, lavoro);
}

const PAGAMENTO_RIFIUTATO = "Pagamento non riuscito: controlla la carta da «Carta, fatture e disdetta».";

export type EsitoCambio ={ abbonamento: Abbonamento } | { importo: number } | { errore: string; stato: number };

/**
 * Aggiunge o toglie un modulo sull'abbonamento in corso, ne calcola l'anteprima, oppure toglie la disdetta.
 * Il controllo sulla voce si fa sull'abbonamento letto adesso da Stripe, non solo su quello salvato.
 * Dopo un cambio si sincronizza subito (senza limite): le righe del registro le scrive la sincronizzazione.
 * Lancia se Stripe non risponde. Da chiamare dentro unCambioAllaVolta.
 */
export async function cambiaModuli(aziendaId: string, r: RichiestaModuli): Promise<EsitoCambio> {
  const ab = await salvato(aziendaId);
  const no = rifiutoCambio(ab, r);
  if (no) return { errore: no.messaggio, stato: no.stato };
  if (!stessoAmbiente(ab, modalitaStripe())) return { errore: ALTRO_AMBIENTE, stato: 409 };
  if (!ab.subscriptionId || !ab.customerId) return { errore: "Abbonamento non attivo", stato: 409 };
  const s = stripe();
  const sub = await s.subscriptions.retrieve(ab.subscriptionId, { expand: [...ESPANSIONI.abbonamento] });
  // Il file salvato può essere vecchio (avviso di Stripe non ancora arrivato): conta l'abbonamento appena riletto,
  // e il file si rimette in pari subito
  if (!abbonamentoModificabile(sub, r.azione)) {
    await sincronizza(aziendaId);
    return { errore: "Abbonamento non attivo", stato: 409 };
  }
  if (r.azione === "riattiva") {
    await s.subscriptions.update(ab.subscriptionId, { cancel_at_period_end: false });
    return { abbonamento: await sincronizza(aziendaId) };
  }
  const voce = voceDelModulo(sub.items.data, r.modulo);
  if (r.azione === "togli") {
    if (!voce) return { errore: "Modulo non attivo", stato: 409 };
    await s.subscriptionItems.del(voce, { proration_behavior: "create_prorations" });
    return { abbonamento: await sincronizza(aziendaId) };
  }
  if (voce) return { errore: "Modulo già attivo", stato: 409 };
  const [[price], iva] = await Promise.all([prezziPer([r.modulo], ab.periodo!), aliquotaIva()]);
  if (r.azione === "anteprima") {
    const fattura = await s.invoices.createPreview({
      customer: ab.customerId,
      subscription: ab.subscriptionId,
      subscription_details: {
        items: [...sub.items.data.map((it) => ({ id: it.id })), { price, tax_rates: [iva] }],
        proration_behavior: "always_invoice",
      },
    });
    return { importo: importoSenzaTasse(fattura) };
  }
  try {
    // error_if_incomplete: se la fattura della parte fino al rinnovo non si paga, la voce non entra e l'abbonamento
    // non va in past_due (niente modulo senza pagamento)
    await s.subscriptionItems.create({
      subscription: ab.subscriptionId,
      price,
      tax_rates: [iva],
      proration_behavior: "always_invoice",
      payment_behavior: "error_if_incomplete",
    });
  } catch (e) {
    if (!pagamentoRifiutato(e)) throw e;
    console.warn("Modulo non aggiunto: pagamento rifiutato da Stripe", aziendaId, r.modulo, (e as { code?: unknown }).code);
    return { errore: PAGAMENTO_RIFIUTATO, stato: 402 };
  }
  return { abbonamento: await sincronizza(aziendaId) };
}

/**
 * Prima di un nuovo Checkout, solo per questo cliente: fa scadere le sessioni aperte (altre schede, ritorni annullati),
 * tranne quella con la stessa chiave di idempotenza, e dice se c'è già un pagamento in attesa di Stripe
 * (abbonamento `incomplete` o sessione completata ma non pagata). Vedi pagamentoInCorso.
 */
export async function preparaCheckout(customerId: string, chiave: string): Promise<{ pagamentoInCorso: boolean }> {
  const s = stripe();
  const [aperte, complete, incompleti] = await Promise.all([
    s.checkout.sessions.list({ customer: customerId, status: "open", limit: 100 }),
    s.checkout.sessions.list({ customer: customerId, status: "complete", limit: 20, expand: [...ESPANSIONI.sessioni] }),
    s.subscriptions.list({ customer: customerId, status: "incomplete", limit: 10 }),
  ]);
  const forma = (x: Stripe.Checkout.Session): SessioneCheckout => ({
    id: x.id,
    customer: typeof x.customer === "string" ? x.customer : (x.customer?.id ?? null),
    status: x.status,
    payment_status: x.payment_status,
    subscription: typeof x.subscription === "string" || !x.subscription ? (x.subscription ?? null) : { status: x.subscription.status },
    metadata: x.metadata,
  });
  for (const id of sessioniDaScadere(customerId, aperte.data.map(forma), chiave)) {
    await s.checkout.sessions.expire(id);
  }
  const abbonamenti = incompleti.data.map((x) => ({ customer: typeof x.customer === "string" ? x.customer : x.customer.id, status: x.status }));
  return { pagamentoInCorso: pagamentoInCorso(customerId, abbonamenti, complete.data.map(forma)) };
}

export type EsitoCheckout = { pagata: boolean; abbonamento: Abbonamento } | { errore: string; stato: number };

/**
 * Il ritorno da Checkout: legge la sessione da Stripe, controlla che sia di questa azienda e, se è pagata, sincronizza
 * subito (senza limite: può arrivare pochi secondi dopo un'altra sincronizzazione). `pagata` vale vero solo quando
 * anche l'abbonamento salvato è in corso: se Stripe non lo mostra ancora, la pagina ricontrolla.
 */
export async function esitoCheckout(aziendaId: string, sessionId: string): Promise<EsitoCheckout> {
  if (modalitaStripe() === "spenta") return { errore: "Pagamenti non disponibili", stato: 503 };
  if (!/^cs_[A-Za-z0-9_]{1,250}$/.test(sessionId)) return { errore: "Pagamento non trovato.", stato: 404 };
  let sessione: Stripe.Checkout.Session;
  try {
    sessione = await stripe().checkout.sessions.retrieve(sessionId);
  } catch (e) {
    console.error("Sessione Checkout non letta", aziendaId, sessionId, e);
    return { errore: "Non riesco a leggere il pagamento da Stripe: riprova tra poco.", stato: 502 };
  }
  if (sessione.client_reference_id !== aziendaId) return { errore: "Pagamento non trovato.", stato: 404 };
  const pagata = sessione.payment_status === "paid" || sessione.payment_status === "no_payment_required";
  const abbonamento = pagata ? await sincronizza(aziendaId) : await salvato(aziendaId);
  return { pagata: pagata && STATI_IN_CORSO.has(abbonamento.stato), abbonamento };
}

/**
 * Come sincronizzaOLancia, ma non lancia mai: con Stripe irraggiungibile scrive nel log e restituisce quello che c'è.
 * `limita` (le richieste dal browser, che può chiederle qualunque ruolo): se l'ultimo tentativo per l'azienda è di
 * meno di 15 secondi fa non si chiama Stripe e si restituisce quello salvato, oppure quella già in coda se c'è.
 */
export async function sincronizza(aziendaId: string, opzioni: { limita?: boolean } = {}): Promise<Abbonamento> {
  try {
    if (opzioni.limita) {
      const inCoda = fila.inAttesa(aziendaId);
      if (inCoda) return await inCoda;
      if (sincronizzazioneLimitata(tentativi.get(aziendaId) ?? null, Date.now())) return await salvato(aziendaId);
    }
    return await sincronizzaOLancia(aziendaId);
  } catch (e) {
    console.error("Sincronizzazione Stripe non riuscita", aziendaId, e);
    return await salvato(aziendaId);
  }
}
