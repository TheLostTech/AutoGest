// Stripe sul server: chiave, cliente (in prova dentro un orologio di prova), prezzi, IVA e sincronizzazione
// dell'abbonamento. Solo server. Spec registrazione-pagamento, sezioni 4, 5, 7, 9.
import Stripe from "stripe";
import { ABBONAMENTO_NUOVO, abbonamentoDaStripe, lookupKey, righeCambio, type Abbonamento } from "@/lib/abbonamento";
import { aggiornaAbbonamento, leggiAbbonamento } from "@/lib/abbonamento-server";
import { aggiungiEventi } from "@/lib/archivio-azienda";
import type { Periodo } from "@/lib/listino";
import type { Modulo } from "@/lib/moduli";
import { modalitaDaChiave, type ModalitaStripe } from "./chiavi";
import { subMinima, type SubDaStripe } from "./forma";

// Versione dell'API fissata: quella che porta con sé stripe@23.2.0 (Stripe.API_VERSION). Si cambia insieme alla libreria.
const VERSIONE_API = "2026-11-18.endive";

type Globali = typeof globalThis & {
  __stripe?: { chiave: string; client: Stripe };
  __clientiStripe?: Map<string, Promise<string>>;
  __sincronizzazioni?: Map<string, Promise<unknown>>;
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

/**
 * Il cliente Stripe dell'azienda: quello salvato in abbonamento.json, altrimenti uno nuovo con metadata.azienda.
 * In prova nasce dentro un orologio di prova tutto suo, che parte da adesso. Due chiamate insieme aspettano lo stesso cliente.
 */
export function clientePer(aziendaId: string, nome: string, email: string): Promise<string> {
  const inCorso = (g.__clientiStripe ??= new Map());
  const gia = inCorso.get(aziendaId);
  if (gia) return gia;
  const run = (async () => {
    const a = await leggiAbbonamento(aziendaId);
    if (a?.customerId) return a.customerId;
    const s = stripe();
    const prova = modalitaStripe() === "prova";
    const ora = Date.now();
    const orologio = prova ? await s.testHelpers.testClocks.create({ frozen_time: Math.floor(ora / 1000), name: aziendaId }) : null;
    const cliente = await s.customers.create({
      name: nome,
      email,
      metadata: { azienda: aziendaId },
      ...(orologio ? { test_clock: orologio.id } : {}),
    });
    const scritto = await aggiornaAbbonamento(aziendaId, (prima) => {
      const base = prima ?? ABBONAMENTO_NUOVO(prova, ora);
      // Un altro processo l'ha già salvato nel frattempo: si tiene quello (il nuovo resta orfano in Stripe)
      if (base.customerId) {
        console.warn("Cliente Stripe già presente: quello nuovo resta inutilizzato", aziendaId, cliente.id);
        return base;
      }
      return { ...base, customerId: cliente.id, orologioId: orologio?.id ?? null, oraOrologio: orologio ? orologio.frozen_time * 1000 : null };
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

// Le aziende scritte con chiavi di prova non si sincronizzano con le chiavi vere (e viceversa): i loro id non esistono lì.
function stessoAmbiente(a: Abbonamento, m: ModalitaStripe): boolean {
  return m !== "spenta" && a.prova === (m === "prova");
}

async function rileggi(aziendaId: string): Promise<Abbonamento> {
  const prima = await leggiAbbonamento(aziendaId);
  if (!prima) return ABBONAMENTO_NUOVO(modalitaStripe() !== "live", Date.now());
  if (!prima.customerId || !stessoAmbiente(prima, modalitaStripe())) return prima;
  const s = stripe();
  const [subs, orologio] = await Promise.all([
    s.subscriptions.list({ customer: prima.customerId, status: "all", expand: ["data.items.data.price.product"], limit: 100 }),
    prima.orologioId ? s.testHelpers.testClocks.retrieve(prima.orologioId) : Promise.resolve(null),
  ]);
  const minime = subs.data.map((x) => subMinima(x as unknown as SubDaStripe));
  let righe: string[] = [];
  const dopo = await aggiornaAbbonamento(aziendaId, (cur) => {
    const base = cur ?? prima;
    const nuovo = abbonamentoDaStripe(minime, base, Date.now(), orologio ? orologio.frozen_time * 1000 : null);
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

/**
 * Rilegge da Stripe l'abbonamento corrente del cliente e riscrive abbonamento.json. Una per volta per azienda,
 * così una lettura vecchia non scrive sopra una più nuova. Lancia se Stripe non risponde (per il webhook: 500, Stripe ritenta).
 */
export function sincronizzaOLancia(aziendaId: string): Promise<Abbonamento> {
  const code = (g.__sincronizzazioni ??= new Map());
  const prima = code.get(aziendaId) ?? Promise.resolve();
  const run = prima.then(() => rileggi(aziendaId));
  const coda = run.catch(() => undefined);
  code.set(aziendaId, coda);
  void coda.then(() => {
    if (code.get(aziendaId) === coda) code.delete(aziendaId);
  });
  return run;
}

/** Come sincronizzaOLancia, ma non lancia mai: con Stripe irraggiungibile scrive nel log e restituisce quello che c'è. */
export async function sincronizza(aziendaId: string): Promise<Abbonamento> {
  try {
    return await sincronizzaOLancia(aziendaId);
  } catch (e) {
    console.error("Sincronizzazione Stripe non riuscita", aziendaId, e);
    return (await leggiAbbonamento(aziendaId)) ?? ABBONAMENTO_NUOVO(modalitaStripe() !== "live", Date.now());
  }
}
