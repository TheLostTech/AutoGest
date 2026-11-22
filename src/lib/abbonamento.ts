// Regole pure dell'abbonamento Stripe: stati, blocco, conto alla rovescia, righe del registro.
// Nessun accesso a disco o rete: tutto si prova con i test.
import type { Modulo } from "./moduli.ts";
import { MODULI, ORDINE_MODULI } from "./moduli.ts";
import type { Periodo } from "./listino.ts";
import type { Push } from "./archivio-unione.ts";

export type StatoAbbonamento = "nuovo" | "attivo" | "in-ritardo" | "disdetto" | "scaduto";

export type Abbonamento = {
  stato: StatoAbbonamento;
  periodo: Periodo | null;
  moduli: Modulo[];
  rinnovo: number | null; // ms, fine del periodo pagato
  customerId: string | null;
  subscriptionId: string | null;
  orologioId: string | null;
  oraOrologio: number | null; // ms, solo in prova
  prova: boolean;
  pagatoAlmenoUnaVolta: boolean;
  aggiornato: number;
};

export const ABBONAMENTO_NUOVO = (prova: boolean, ora: number): Abbonamento => ({
  stato: "nuovo", periodo: null, moduli: [], rinnovo: null,
  customerId: null, subscriptionId: null, orologioId: null, oraOrologio: null,
  prova, pagatoAlmenoUnaVolta: false, aggiornato: ora,
});

const NOMI_STRIPE: Record<Modulo, "magazzino" | "pratiche" | "ambiente" | "banco"> = {
  magazzino: "magazzino", accettazione: "pratiche", ambiente: "ambiente", vendite: "banco",
};

export function nomeStripe(m: Modulo) {
  return NOMI_STRIPE[m];
}

export function lookupKey(m: Modulo, p: Periodo): string {
  return `${NOMI_STRIPE[m]}_${p === "anno" ? "anno" : "mese"}`;
}

// Il magazzino base c'è sempre; gli altri solo con un abbonamento in corso.
export function moduliDaAbbonamento(a: Abbonamento): Modulo[] {
  const attivi = a.stato === "nuovo" || a.stato === "scaduto" ? [] : a.moduli;
  const set = new Set<Modulo>(["magazzino", ...attivi]);
  return ORDINE_MODULI.filter((m) => set.has(m));
}

// Nuovo: si prova finché non si carica il primo veicolo. Scaduto: sempre bloccato (i dati restano).
export function bloccato(a: Abbonamento, veicoli: number): boolean {
  if (a.stato === "scaduto") return true;
  if (a.stato === "nuovo") return veicoli >= 1;
  return false;
}

// Forma minima di un abbonamento Stripe, così il test non dipende dalla libreria
export type SubStripe = {
  id: string; status: string; cancel_at_period_end: boolean; created: number;
  items: { price: { recurring: { interval: "month" | "year" } | null; product: { metadata: Record<string, string> } | string }; current_period_end: number }[];
};

const VIVI = new Set(["active", "trialing", "past_due"]);

function scegli(subs: SubStripe[]): SubStripe | null {
  let best: SubStripe | null = null;
  for (const s of subs) {
    if (!best) { best = s; continue; }
    const v = VIVI.has(s.status), vb = VIVI.has(best.status);
    if (v !== vb ? v : s.created > best.created) best = s;
  }
  return best;
}

export function abbonamentoDaStripe(subs: SubStripe[], prima: Abbonamento, ora: number, oraOrologio: number | null): Abbonamento {
  const orologio = oraOrologio ?? prima.oraOrologio;
  const s = scegli(subs);
  if (!s) {
    return { ...prima, stato: prima.pagatoAlmenoUnaVolta ? "scaduto" : "nuovo", periodo: null, moduli: [], rinnovo: null, subscriptionId: null, oraOrologio: orologio, aggiornato: ora };
  }
  let stato: StatoAbbonamento;
  switch (s.status) {
    case "active": case "trialing": stato = s.cancel_at_period_end ? "disdetto" : "attivo"; break;
    case "past_due": stato = "in-ritardo"; break;
    case "canceled": case "unpaid": case "incomplete_expired": stato = "scaduto"; break;
    default: return { ...prima, oraOrologio: orologio, aggiornato: ora }; // incomplete e sconosciuti: niente cambia
  }
  const trovati = new Set<Modulo>();
  for (const it of s.items) {
    const nome = typeof it.price.product === "string" ? null : it.price.product.metadata?.modulo;
    const m = ORDINE_MODULI.find((x) => x === nome);
    if (m) trovati.add(m);
  }
  const primo = s.items[0];
  return {
    ...prima,
    stato,
    periodo: primo?.price.recurring?.interval === "year" ? "anno" : "mese",
    moduli: ORDINE_MODULI.filter((m) => trovati.has(m)),
    rinnovo: primo ? primo.current_period_end * 1000 : null,
    subscriptionId: s.id,
    oraOrologio: orologio,
    pagatoAlmenoUnaVolta: prima.pagatoAlmenoUnaVolta || stato === "attivo" || stato === "disdetto" || stato === "in-ritardo",
    aggiornato: ora,
  };
}

export type Conto = { tono: "ok" | "avviso" | "errore"; testo: string; giorni: number | null };

const FMT = new Intl.DateTimeFormat("it-IT", { timeZone: "Europe/Rome", day: "2-digit", month: "2-digit", year: "numeric" });
const data = (ms: number) => FMT.format(new Date(ms));
const tra = (g: number) => (g === 1 ? "tra 1 giorno" : `tra ${g} giorni`);

export function contoAllaRovescia(a: Abbonamento, oraMac: number): Conto | null {
  const ora = a.oraOrologio ?? oraMac;
  if (a.stato === "nuovo" || a.stato === "scaduto") return null;
  if (a.stato === "in-ritardo") {
    return { tono: "errore", testo: "Pagamento non riuscito: aggiorna la carta. Stripe riprova da solo.", giorni: null };
  }
  if (a.rinnovo == null) return null;
  const giorni = Math.max(0, Math.ceil((a.rinnovo - ora) / 86_400_000));
  const quando = giorni === 0 ? "oggi" : `il ${data(a.rinnovo)} · ${tra(giorni)}`;
  if (a.stato === "disdetto") {
    return { tono: "avviso", testo: `Finisce ${quando}. Poi il gestionale si blocca, i dati restano.`, giorni };
  }
  return { tono: "ok", testo: `Si rinnova ${quando}`, giorni };
}

// Il magazzino base c'è sempre: non genera righe. Righe del registro per il passaggio da `prima` a `dopo`: prima lo stato, poi i moduli aggiunti, poi quelli tolti.
export function righeCambio(prima: Abbonamento, dopo: Abbonamento): string[] {
  const righe: string[] = [];
  if (prima.stato !== dopo.stato) {
    if (dopo.stato === "scaduto") righe.push("Abbonamento scaduto");
    else if (dopo.stato === "attivo") righe.push(prima.stato === "disdetto" ? "Abbonamento riattivato" : prima.stato === "nuovo" ? "Abbonamento attivato" : "Pagamento ripreso");
    else if (dopo.stato === "in-ritardo") righe.push("Pagamento non riuscito");
    else if (dopo.stato === "disdetto") righe.push("Abbonamento disdetto");
  }
  const prime = new Set(prima.moduli), dopoSet = new Set(dopo.moduli);
  for (const m of ORDINE_MODULI) if (m !== "magazzino" && dopoSet.has(m) && !prime.has(m)) righe.push(`Modulo aggiunto: ${MODULI[m].nome}`);
  for (const m of ORDINE_MODULI) if (m !== "magazzino" && prime.has(m) && !dopoSet.has(m)) righe.push(`Modulo tolto: ${MODULI[m].nome}`);
  return righe;
}

export type Scrittura = { esito: "ok"; corpo: Push } | { esito: "bloccato" };

// Un salvataggio dal browser. Per le aziende registrate i moduli non li decide il browser (li decide l'abbonamento)
// e, se l'abbonamento non è in regola, non si scrive nulla.
export function scritturaAzienda(registrata: boolean, a: Abbonamento | null, veicoliPrima: number, corpo: Push): Scrittura {
  if (!registrata) return { esito: "ok", corpo };
  if (bloccato(a ?? ABBONAMENTO_NUOVO(true, 0), veicoliPrima)) return { esito: "bloccato" };
  if (!corpo.whole) return { esito: "ok", corpo };
  const whole = { ...corpo.whole };
  delete whole.moduli;
  return { esito: "ok", corpo: { ...corpo, whole } };
}

// Lo stato mandato al browser: per le aziende registrate i moduli vengono dall'abbonamento.
export function statoPerBrowser(registrata: boolean, a: Abbonamento | null, stato: unknown): unknown {
  if (!registrata || !stato || typeof stato !== "object") return stato;
  const attivi = new Set(moduliDaAbbonamento(a ?? ABBONAMENTO_NUOVO(true, 0)));
  return { ...(stato as object), moduli: ORDINE_MODULI.map((id) => ({ id, attivo: attivi.has(id) })) };
}
