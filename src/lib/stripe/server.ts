// Stripe sul server: chiave, cliente (in prova dentro un orologio di prova), prezzi, IVA e sincronizzazione
// dell'abbonamento. Solo server. Spec registrazione-pagamento, sezioni 4, 5, 7, 9.
import Stripe from "stripe";
import { ABBONAMENTO_NUOVO, abbonamentoDaStripe, lookupKey, righeCambio, scegli, type Abbonamento } from "@/lib/abbonamento";
import { aggiornaAbbonamento, leggiAbbonamento } from "@/lib/abbonamento-server";
import { aggiungiEventi } from "@/lib/archivio-azienda";
import type { Periodo } from "@/lib/listino";
import type { Modulo } from "@/lib/moduli";
import { azioneCliente, ESPANSIONI, modalitaDaChiave, sincronizzazioneLimitata, stessoAmbiente, type ModalitaStripe } from "./chiavi";
import { creaFila, type Fila } from "./fila";
import { subMinima, type SubDaStripe } from "./forma";

// Versione dell'API fissata: quella che porta con sé stripe@23.2.0 (Stripe.API_VERSION). Si cambia insieme alla libreria.
const VERSIONE_API = "2026-11-18.endive";

type Globali = typeof globalThis & {
  __stripe?: { chiave: string; client: Stripe };
  __clientiStripe?: Map<string, Promise<string>>;
  __filaSincronizzazioni?: Fila<Abbonamento>;
  __tentativiSincronizzazione?: Map<string, number>;
  __ivaStripe?: Promise<string>;
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
