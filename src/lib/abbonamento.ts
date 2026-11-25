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
  // Prova gratuita (spec prova-15-giorni, sezione 4): stato "nuovo" con una fine. null = prova non ancora partita
  // (email non confermata). Pagando lo stato diventa "attivo" e la prova non conta più.
  fineProva: number | null; // ms
  // Strumenti di prova (solo con le chiavi di prova): di quanto l'orologio dell'app è avanti per la prova. Di serie 0.
  spostamentoProva: number; // ms
};

export const ABBONAMENTO_NUOVO = (prova: boolean, ora: number): Abbonamento => ({
  stato: "nuovo", periodo: null, moduli: [], rinnovo: null,
  customerId: null, subscriptionId: null, orologioId: null, oraOrologio: null,
  prova, pagatoAlmenoUnaVolta: false, aggiornato: ora,
  fineProva: null, spostamentoProva: 0,
});

// Documenti salvati prima della prova di 15 giorni non hanno fineProva e spostamentoProva: si leggono come null e 0
// (anche un valore non valido vale come assente). Chi legge l'abbonamento dal deposito passa di qui.
export function normalizzaAbbonamento(a: Abbonamento): Abbonamento {
  const { fineProva, spostamentoProva } = a as { fineProva?: unknown; spostamentoProva?: unknown };
  return {
    ...a,
    fineProva: typeof fineProva === "number" && Number.isFinite(fineProva) ? fineProva : null,
    spostamentoProva: typeof spostamentoProva === "number" && Number.isFinite(spostamentoProva) ? spostamentoProva : 0,
  };
}

export const GIORNI_PROVA = 15;

const GIORNO_MS = 86_400_000;

// La prova parte una volta sola (alla conferma dell'email) e solo per un'azienda nuova: altrimenti niente cambia.
export function avviaProva(a: Abbonamento, ora: number): Abbonamento {
  if (a.stato !== "nuovo" || a.fineProva !== null) return a;
  return { ...a, fineProva: ora + GIORNI_PROVA * GIORNO_MS };
}

// L'ora con cui si conta la prova: quella vera più lo spostamento degli strumenti di prova (l'orologio di Stripe no).
// Lo spostamento conta solo con le chiavi di prova (a.prova): un'azienda con le chiavi vere non lo vede mai.
export function oraProva(a: Abbonamento, ora: number): number {
  return a.prova ? ora + a.spostamentoProva : ora;
}

export function inProva(a: Abbonamento, ora: number): boolean {
  return a.stato === "nuovo" && a.fineProva !== null && oraProva(a, ora) < a.fineProva;
}

const NOMI_STRIPE: Record<Modulo, "magazzino" | "pratiche" | "ambiente" | "banco"> = {
  magazzino: "magazzino", accettazione: "pratiche", ambiente: "ambiente", vendite: "banco",
};

export function nomeStripe(m: Modulo) {
  return NOMI_STRIPE[m];
}

export function lookupKey(m: Modulo, p: Periodo): string {
  return `${NOMI_STRIPE[m]}_${p === "anno" ? "anno" : "mese"}`;
}

// La scelta mandata a Checkout dal riquadro di pagamento: periodo "mese" o "anno" e moduli conosciuti.
// Il magazzino c'è sempre, i doppioni e i moduli sconosciuti si scartano; `moduli` assente vale solo magazzino.
export function sceltaValida(corpo: unknown): { periodo: Periodo; moduli: Modulo[] } | null {
  if (!corpo || typeof corpo !== "object") return null;
  const { periodo, moduli } = corpo as { periodo?: unknown; moduli?: unknown };
  if (periodo !== "mese" && periodo !== "anno") return null;
  if (moduli !== undefined && !Array.isArray(moduli)) return null;
  const scelti = new Set<unknown>(["magazzino", ...(moduli ?? [])]);
  return { periodo, moduli: ORDINE_MODULI.filter((m) => scelti.has(m)) };
}

// I moduli pagati: il magazzino base c'è sempre, gli altri solo con un abbonamento in corso.
function moduliPagati(a: Abbonamento): Modulo[] {
  const attivi = a.stato === "nuovo" || a.stato === "scaduto" ? [] : a.moduli;
  const set = new Set<Modulo>(["magazzino", ...attivi]);
  return ORDINE_MODULI.filter((m) => set.has(m));
}

// In prova tutti i moduli (offerta massima); fuori prova i moduli pagati (nuovo e scaduto: solo il magazzino).
export function moduliDaAbbonamento(a: Abbonamento, ora: number): Modulo[] {
  return inProva(a, ora) ? [...ORDINE_MODULI] : moduliPagati(a);
}

// Scaduto: sempre bloccato (i dati restano). Nuovo: bloccato se la prova non è partita o è finita. I veicoli non contano.
export function bloccato(a: Abbonamento, ora: number): boolean {
  if (a.stato === "scaduto") return true;
  if (a.stato === "nuovo") return a.fineProva === null || oraProva(a, ora) >= a.fineProva;
  return false;
}

// Modifiche rimaste in attesa del pagamento (rifiuto 402): ripartono quando l'azienda non è più bloccata (pagato,
// oppure ancora in prova), o per un'azienda senza abbonamento. Prova finita o scaduto: il server le rifiuterebbe di
// nuovo, niente giro di 402.
export function riprendeDopoPagamento(a: Abbonamento | null | undefined, ora: number): boolean {
  return a == null || !bloccato(a, ora);
}

// Il cliente Stripe non c'è più (cancellato dalla dashboard, conto di prova ripulito): si dimenticano i suoi id, così
// lo stato diventa "senza abbonamenti" (scaduto se aveva pagato, altrimenti nuovo) e il prossimo Checkout crea un
// cliente nuovo invece di sbagliare per sempre.
export function senzaCliente(a: Abbonamento): Abbonamento {
  return { ...a, customerId: null, subscriptionId: null, orologioId: null, oraOrologio: null };
}

// Il negozio online di un'azienda registrata chiude quando è bloccata; le altre aziende non sono toccate.
export function negozioAperto(registrata: boolean, a: Abbonamento | null, ora: number): boolean {
  return !registrata || !bloccato(a ?? ABBONAMENTO_NUOVO(true, 0), ora);
}

// Forma minima di un abbonamento Stripe, così il test non dipende dalla libreria. cancel_at in secondi.
export type SubStripe = {
  id: string; status: string; cancel_at_period_end: boolean; cancel_at: number | null; created: number;
  items: { price: { recurring: { interval: "month" | "year" } | null; product: { metadata: Record<string, string> } | string }; current_period_end: number }[];
};

const VIVI = new Set(["active", "trialing", "past_due"]);

// Disdetta: a fine periodo (cancel_at_period_end) oppure a una data (cancel_at, che dall'API 2026 il portale può usare)
export function conDisdetta(s: { cancel_at_period_end: boolean; cancel_at?: number | null }): boolean {
  return s.cancel_at_period_end || s.cancel_at != null;
}

// L'abbonamento che conta tra quelli del cliente: uno vivo prima di tutto, poi il più recente.
export function scegli(subs: SubStripe[]): SubStripe | null {
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
    case "active": case "trialing": stato = conDisdetta(s) ? "disdetto" : "attivo"; break;
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
  // Fine del periodo pagato; con una disdetta a una data che viene prima, quella data
  const finePeriodo = primo ? primo.current_period_end * 1000 : null;
  const fineDisdetta = s.cancel_at != null ? s.cancel_at * 1000 : null;
  const rinnovo = fineDisdetta !== null && (finePeriodo === null || fineDisdetta < finePeriodo) ? fineDisdetta : finePeriodo;
  return {
    ...prima,
    stato,
    periodo: primo?.price.recurring?.interval === "year" ? "anno" : "mese",
    moduli: ORDINE_MODULI.filter((m) => trovati.has(m)),
    rinnovo,
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
  if (a.fineProva !== null && inProva(a, oraMac)) {
    const giorni = Math.max(0, Math.ceil((a.fineProva - oraProva(a, oraMac)) / GIORNO_MS));
    return {
      tono: giorni <= 3 ? "avviso" : "ok",
      testo: giorni === 0 ? "Prova gratuita: finisce oggi" : `Prova gratuita: ${tra(giorni)} il gestionale si blocca`,
      giorni,
    };
  }
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

// Fascia in cima al gestionale (solo per il titolare): per tutta la prova gratuita, pagamento non riuscito sempre,
// disdetta negli ultimi 7 giorni. I giorni sono quelli della riga del conto alla rovescia (con l'orologio di prova
// contano da oraOrologio).
export function fasciaDaMostrare(a: Abbonamento, ora: number): boolean {
  if (inProva(a, ora)) return true;
  if (a.stato === "in-ritardo") return true;
  if (a.stato !== "disdetto") return false;
  const c = contoAllaRovescia(a, ora);
  return c?.giorni != null && c.giorni <= 7;
}

// Strumenti di prova: di quanto si fa avanzare l'orologio di prova di Stripe (spec registrazione-pagamento, sezione 7).
export type Passo = "giorno" | "settimana" | "mese" | "anno";

const PASSI: readonly Passo[] = ["giorno", "settimana", "mese", "anno"];

// Il corpo di POST /api/abbonamento/prova/avanza: { passo } con uno dei quattro passi, altrimenti null.
export function passoValido(corpo: unknown): Passo | null {
  if (!corpo || typeof corpo !== "object" || Array.isArray(corpo)) return null;
  const p = (corpo as { passo?: unknown }).passo;
  return PASSI.find((x) => x === p) ?? null;
}

const ROMA = new Intl.DateTimeFormat("en-US", {
  timeZone: "Europe/Rome", hourCycle: "h23",
  year: "numeric", month: "numeric", day: "numeric", hour: "numeric", minute: "numeric", second: "numeric",
});

// Data e ora di Roma di un istante, come se fossero in UTC (ms): la differenza con l'istante è lo scarto del fuso.
function oraDiRoma(ms: number): number {
  const p = Object.fromEntries(ROMA.formatToParts(new Date(ms)).map((x) => [x.type, Number(x.value)]));
  return Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second, ((ms % 1000) + 1000) % 1000);
}

// L'istante in cui a Roma è l'ora indicata (in UTC "finta", come da oraDiRoma). Due passi bastano per lo scarto del fuso.
function daOraDiRoma(finta: number): number {
  let ms = finta - (oraDiRoma(finta) - finta);
  ms = finta - (oraDiRoma(ms) - ms);
  return ms;
}

/**
 * Dove arriva l'orologio di prova da `ora` (ms). Giorno e settimana: 24 ore e 7 × 24 ore. Mese e anno: di calendario,
 * a Roma e alla stessa ora; se il giorno non c'è si va all'ultimo del mese (31/01 → 28/02).
 */
export function nuovaOraOrologio(ora: number, passo: Passo): number {
  if (passo === "giorno") return ora + 86_400_000;
  if (passo === "settimana") return ora + 7 * 86_400_000;
  const r = new Date(oraDiRoma(ora));
  const mesi = r.getUTCMonth() + (passo === "mese" ? 1 : 12);
  const anno = r.getUTCFullYear() + Math.floor(mesi / 12);
  const mese = mesi % 12;
  const ultimo = new Date(Date.UTC(anno, mese + 1, 0)).getUTCDate();
  const finta = Date.UTC(anno, mese, Math.min(r.getUTCDate(), ultimo), r.getUTCHours(), r.getUTCMinutes(), r.getUTCSeconds(), r.getUTCMilliseconds());
  return daOraDiRoma(finta);
}

/**
 * Il passo si può chiedere a Stripe? Stripe non fa avanzare l'orologio di più di due periodi dell'abbonamento più corto:
 * +1 anno solo con l'annuale; giorno, settimana e mese sempre (stanno sempre entro due periodi).
 */
export function avanzamentoPermesso(a: Abbonamento, passo: Passo): boolean {
  return passo !== "anno" || a.periodo === "anno";
}

// Strumenti della prova gratuita: di quanto si sposta in avanti l'orologio dell'app (spec prova-15-giorni, sezione 4).
// Nella prova il cliente Stripe e il suo orologio non ci sono ancora: si sposta solo l'ora con cui si conta la prova.
export type PassoProva = "giorno" | "settimana";

const GIORNI_PASSO: Record<PassoProva, number> = { giorno: 1, settimana: 7 };

// Il corpo di POST /api/abbonamento/prova/sposta: { passo: "giorno" | "settimana" }, altrimenti null.
export function passoProvaValido(corpo: unknown): PassoProva | null {
  if (!corpo || typeof corpo !== "object" || Array.isArray(corpo)) return null;
  const p = (corpo as { passo?: unknown }).passo;
  return p === "giorno" || p === "settimana" ? p : null;
}

// Si sposta solo una prova partita, non ancora pagata, con le chiavi di prova (anche già finita: resta bloccata).
export function spostamentoPermesso(a: Abbonamento | null): a is Abbonamento {
  return !!a && a.prova && a.stato === "nuovo" && a.fineProva !== null;
}

export function spostaProva(a: Abbonamento, passo: PassoProva): Abbonamento {
  return { ...a, spostamentoProva: a.spostamentoProva + GIORNI_PASSO[passo] * GIORNO_MS };
}

export type RichiestaModuli ={ azione: "aggiungi" | "togli" | "anteprima"; modulo: Modulo } | { azione: "riattiva" };

const AZIONI_MODULO = ["aggiungi", "togli", "anteprima"] as const;

// Il corpo di POST /api/abbonamento/moduli: una sola chiave tra aggiungi, togli, anteprima (con un id di modulo
// dell'app) oppure { riattiva: true }.
export function richiestaModuli(corpo: unknown): RichiestaModuli | null {
  if (!corpo || typeof corpo !== "object" || Array.isArray(corpo)) return null;
  const o = corpo as Record<string, unknown>;
  const chiavi = Object.keys(o);
  if (chiavi.length !== 1) return null;
  if (chiavi[0] === "riattiva") return o.riattiva === true ? { azione: "riattiva" } : null;
  const azione = AZIONI_MODULO.find((x) => x === chiavi[0]);
  const modulo = ORDINE_MODULI.find((m) => m === o[chiavi[0]]);
  return azione && modulo ? { azione, modulo } : null;
}

const CAMBIABILE = new Set<StatoAbbonamento>(["attivo", "disdetto"]);

// Perché un cambio non si può fare con l'abbonamento salvato (stato HTTP e messaggio), oppure null.
export function rifiutoCambio(a: Abbonamento, r: RichiestaModuli): { stato: number; messaggio: string } | null {
  if (r.azione === "riattiva") return a.stato === "disdetto" ? null : { stato: 409, messaggio: "L'abbonamento non è disdetto" };
  if (!CAMBIABILE.has(a.stato) || !a.periodo) return { stato: 409, messaggio: "Abbonamento non attivo" };
  if (r.azione === "togli" && r.modulo === "magazzino") return { stato: 400, messaggio: "Il Magazzino non si toglie" };
  const presente = moduliPagati(a).includes(r.modulo); // qui lo stato è attivo o disdetto: niente prova
  if (r.azione === "togli") return presente ? null : { stato: 409, messaggio: "Modulo non attivo" };
  return presente ? { stato: 409, messaggio: "Modulo già attivo" } : null;
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
// e, se l'azienda è bloccata (prova non partita o finita, abbonamento scaduto), non si scrive nulla.
// File assente: nuovo senza prova, quindi bloccato.
export function scritturaAzienda(registrata: boolean, a: Abbonamento | null, ora: number, corpo: Push): Scrittura {
  if (!registrata) return { esito: "ok", corpo };
  if (bloccato(a ?? ABBONAMENTO_NUOVO(true, 0), ora)) return { esito: "bloccato" };
  if (!corpo.whole) return { esito: "ok", corpo };
  const whole = { ...corpo.whole };
  delete whole.moduli;
  return { esito: "ok", corpo: { ...corpo, whole } };
}

// Lo stato mandato al browser: per le aziende registrate i moduli vengono dall'abbonamento (in prova tutti).
export function statoPerBrowser(registrata: boolean, a: Abbonamento | null, ora: number, stato: unknown): unknown {
  if (!registrata || !stato || typeof stato !== "object") return stato;
  const attivi = new Set(moduliDaAbbonamento(a ?? ABBONAMENTO_NUOVO(true, 0), ora));
  return { ...(stato as object), moduli: ORDINE_MODULI.map((id) => ({ id, attivo: attivi.has(id) })) };
}
