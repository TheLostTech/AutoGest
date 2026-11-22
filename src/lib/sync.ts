"use client";

// Sincronizzazione della demo tra dispositivi (telefono, computer) tramite /api/demo-state.
// Ruolo e veicolo attivo restano propri di ogni dispositivo; tutto il resto è condiviso.
import { useSyncExternalStore } from "react";
import { abilitaSalvataggioLocale, STORE_SCHEMA, useStore } from "./store";
import { devePubblicareStatoLocale } from "./sync-regole";
import { percorsoPubblico } from "./accesso/percorsi";
import { intestazioniPassive } from "./accesso/attivita";
import { aggiungiInSospeso, corpoDaRiprendere } from "./sync-in-sospeso";
import { aziendaFissata, fetchAzienda, segnalaAziendaCambiata, suAziendaCambiata } from "./accesso/azienda-client";
import { MOTIVO_AZIENDA_CAMBIATA } from "./accesso/regole";
import { riprendeDopoPagamento } from "./abbonamento";

const PREPEND = ["vehicles", "parts", "annunci", "orders", "docs", "firs"] as const;
const APPEND = ["audit", "wasteMoves", "inventory"] as const;
const LISTS = [...PREPEND, ...APPEND] as const;
const WHOLE = ["rules", "listini", "warehouses", "soggetti", "moduli"] as const;
const SHARED = [...LISTS, ...WHOLE, "counters"] as const;

type S = ReturnType<typeof useStore.getState>;
type Rec = { id?: string; typeId?: string };

let version = 0;
let demoAzienda = false; // aggiornato a ogni lettura: solo l'azienda demo può avere lo stato intero scritto dal browser
let applying = false;
let dirty = false;
let pushing = 0; // scritture in corso (a pezzi o intere): un contatore, così la fine di una non sblocca l'altra
let timer: ReturnType<typeof setTimeout> | undefined;
let synced: Partial<S> = {}; // ultimo stato condiviso noto (riferimenti), per calcolare cosa è cambiato

// Primo allineamento vero con il server (lettura riuscita o stato intero scritto). Il riallineamento eBay e
// l'import delle vendite lo aspettano: con dati vecchi del dispositivo manderebbero a eBay quantità sbagliate.
let allineato = false;
let segnaAllineato: () => void = () => undefined;
const primoAllineamento = new Promise<void>((r) => {
  segnaAllineato = () => {
    allineato = true;
    r();
  };
});
/** Si risolve dopo la prima lettura riuscita dal server (o la prima scrittura dello stato intero). Il timeout di avvio non conta. */
export const syncPronto = (): Promise<void> => primoAllineamento;
export const syncAllineato = (): boolean => allineato;

// Avviso per l'utente quando la sincronizzazione si ferma (archivio di versione diversa, accesso perso).
// Dopo l'avviso non si riprova da soli: niente cicli di richieste.
export type AvvisoSync = { titolo: string; testo: string; ricarica?: boolean };
let avviso: AvvisoSync | null = null;
let fermata = false;
let inUscita = false; // uscita in corso (blocco per inattività, "Esci"): chi esce porta già all'accesso

// Il server ha rifiutato una scrittura con 402 (abbonamento non pagato). Finché resta così non si scrive: le letture
// continuano, le modifiche si aggiungono alla coda in sospeso con `pagamento: true` (non scade dopo 24 ore) e partono
// quando una lettura dice che l'azienda non è più bloccata.
// Non si azzera al cambio di azienda perché la pagina non cambia mai azienda senza ricaricarsi (fissaAzienda, Hydrator).
let attesaPagamento = false;
/** Le modifiche di questo dispositivo aspettano il pagamento dell'abbonamento (le legge il riquadro di pagamento). */
export const inAttesaDiPagamento = (): boolean => attesaPagamento;
const ascoltatoriAvviso = new Set<() => void>();
function mostraAvviso(titolo: string, testo: string, ricarica = false) {
  avviso = { titolo, testo, ...(ricarica ? { ricarica } : {}) };
  ascoltatoriAvviso.forEach((f) => f());
}
function fermaConAvviso(testo: string, titolo = "Archivio con versione diversa.", ricarica = false) {
  fermata = true;
  clearTimeout(timer);
  mostraAvviso(titolo, testo, ricarica);
}
export const useSyncAvviso = (): AvvisoSync | null =>
  useSyncExternalStore(
    (f) => (ascoltatoriAvviso.add(f), () => void ascoltatoriAvviso.delete(f)),
    () => avviso,
    () => null,
  );

class ErroreApi extends Error {
  constructor(
    readonly stato: number,
    readonly motivo?: string,
  ) {
    super(`demo-state ${stato}`);
  }
}

// La sessione è passata a un'altra azienda (altra scheda): questa scheda smette subito di leggere e scrivere.
// Le modifiche non ancora inviate restano nella coda in sospeso di QUESTA azienda (la chiave dello store è la sua) e
// partono al prossimo ingresso in questa azienda; il salvataggio nel browser si spegne, così la copia locale di questa
// azienda non viene riscritta mentre un'altra scheda lavora su un'altra.
function fermaPerAziendaCambiata() {
  if (fermata && avviso?.ricarica) return;
  const giaFermata = fermata;
  fermata = true;
  clearTimeout(timer);
  if (allineato && !giaFermata) {
    const d = differenze(useStore.getState());
    if (d) salvaInSospeso(d);
  }
  abilitaSalvataggioLocale(false);
  mostraAvviso(
    "Azienda cambiata.",
    "In un'altra scheda di questo browser è stata aperta un'altra azienda: questa pagina non legge e non salva più nulla. Ricarica per continuare.",
    true,
  );
}
suAziendaCambiata(fermaPerAziendaCambiata);

// 401: la sessione non vale più, si torna all'accesso (tranne sulle pagine pubbliche). 403/409: ci si ferma con un avviso.
// 402: abbonamento non pagato, le modifiche aspettano il pagamento nella coda in sospeso.
function gestisciRifiuto(e: unknown): boolean {
  if (!(e instanceof ErroreApi)) return false;
  if (e.stato === 402 && e.motivo === "abbonamento") {
    attesaPagamento = true;
    // Solo dopo il primo allineamento: prima non si sa cosa è davvero nuovo
    if (allineato) {
      const d = differenze(useStore.getState());
      if (d) salvaInSospeso(d, { pagamento: true });
    }
    return true;
  }
  if (e.stato === 409 && e.motivo === MOTIVO_AZIENDA_CAMBIATA) {
    segnalaAziendaCambiata(); // già segnalato da fetchAzienda: qui per sicurezza
    return true;
  }
  if (e.stato === 401) {
    fermata = true;
    // Sessione finita (per esempio scaduta sul server prima del blocco sullo schermo): le modifiche non inviate
    // restano per il prossimo accesso. Solo dopo il primo allineamento: prima non si sa cosa è davvero nuovo.
    if (allineato && !inUscita) {
      const d = differenze(useStore.getState());
      if (d) salvaInSospeso(d);
    }
    if (typeof window !== "undefined" && !inUscita && !percorsoPubblico(window.location.pathname)) {
      window.location.assign(`/accesso?da=${encodeURIComponent(window.location.pathname + window.location.search)}`);
    }
    return true;
  }
  if (e.stato === 409) {
    fermaConAvviso("L'archivio dell'azienda ha una versione diversa da quella di questo dispositivo: i dati non vengono più sincronizzati. Contatta l'assistenza.");
    return true;
  }
  if (e.stato === 403 && e.motivo === "ruolo") return true; // operazione non permessa a questo ruolo: nulla è stato scritto
  if (e.stato === 403) {
    fermaConAvviso("Non hai più accesso a questa azienda: i dati non vengono più sincronizzati. Accedi di nuovo.", "Accesso cambiato.");
    return true;
  }
  return false;
}

const pick = (s: S) => Object.fromEntries(SHARED.map((k) => [k, s[k]])) as Partial<S>;

// Dal server si accettano solo i campi condivisi, e solo se hanno la forma attesa:
// ruolo, veicolo attivo e funzioni dello store non possono essere sovrascritti da fuori.
function sanitize(raw: unknown): Partial<S> | null {
  if (!raw || typeof raw !== "object") return null;
  const r = raw as Record<string, unknown>;
  const out: Record<string, unknown> = {};
  for (const k of [...LISTS, ...WHOLE]) {
    if (!(k in r)) continue;
    if (!Array.isArray(r[k]) || !(r[k] as unknown[]).every((x) => x && typeof x === "object")) return null;
    out[k] = r[k];
  }
  if ("counters" in r) {
    const c = r.counters;
    if (!c || typeof c !== "object" || Array.isArray(c)) return null;
    out.counters = c;
  }
  return out as Partial<S>;
}
const keyOf = (r: Rec) => r.id ?? r.typeId ?? "";

async function api(method: "GET" | "PUT", body?: unknown) {
  const r = await fetchAzienda("/api/demo-state", {
    method,
    cache: "no-store",
    // Le letture partono da sole ogni 2,5 s: non sono attività della persona (le scritture sì)
    headers: body ? { "Content-Type": "application/json" } : method === "GET" ? intestazioniPassive() : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) {
    const j = (await r.json().catch(() => ({}))) as { motivo?: string };
    throw new ErroreApi(r.status, j.motivo);
  }
  return r.json();
}

// Scrive lo stato intero. Intanto `pushing` ferma le letture (un pull in corso non riapplica lo stato vecchio)
// e una scrittura a pezzi in attesa si annulla: lo stato intero la comprende già.
async function pushAll() {
  if (fermata || !demoAzienda || attesaPagamento) return; // lo stato intero si manda solo per l'azienda demo
  pushing++;
  clearTimeout(timer);
  try {
    const s = useStore.getState();
    const res = await api("PUT", { schema: STORE_SCHEMA, replace: true, state: pick(s) });
    version = res.version;
    synced = pick(s);
    segnaAllineato();
  } catch (e) {
    // Archivio demo da aggiornare (vuoto o di una versione vecchia): lo può sostituire solo il responsabile.
    // Riprovare ogni 2,5 secondi non serve: ci si ferma finché un responsabile non apre il gestionale.
    if (e instanceof ErroreApi && e.stato === 403 && e.motivo === "ruolo") {
      fermaConAvviso("Serve il responsabile per aggiornare l'archivio demo: finché non lo apre, questo dispositivo non sincronizza i dati.", "Archivio demo da aggiornare.", true);
      return;
    }
    if (!gestisciRifiuto(e)) throw e;
  } finally {
    pushing--;
  }
}

// Cosa è cambiato in questo dispositivo rispetto all'ultimo stato condiviso noto (null: niente).
function differenze(s: S) {
  const changes: Record<string, Rec[]> = {};
  for (const k of LISTS) {
    const before = new Map(((synced[k] as Rec[] | undefined) ?? []).map((r) => [keyOf(r), r]));
    const changed = (s[k] as Rec[]).filter((r) => before.get(keyOf(r)) !== r);
    if (changed.length) changes[k] = changed;
  }
  // Regole, listini, magazzini e soggetti si mandano interi: solo dopo il primo allineamento con il server, mai
  // valori locali (copia vecchia o archivio vuoto di partenza) prima di aver letto quelli dell'azienda.
  const whole = allineato ? Object.fromEntries(WHOLE.filter((k) => s[k] !== synced[k]).map((k) => [k, s[k]])) : {};
  const vuote = Object.keys(changes).length === 0 && Object.keys(whole).length === 0 && s.counters === synced.counters;
  return vuote ? null : { schema: STORE_SCHEMA, changes, whole, counters: s.counters };
}

async function pushChanges() {
  if (pushing || fermata) return;
  if (attesaPagamento) {
    // In attesa del pagamento non si scrive: quello che è cambiato si aggiunge alla coda, così non va perso
    dirty = false;
    const d = allineato ? differenze(useStore.getState()) : null;
    if (d) salvaInSospeso(d, { pagamento: true });
    return;
  }
  pushing++;
  dirty = false;
  try {
    const s = useStore.getState();
    const res = await api("PUT", differenze(s) ?? { schema: STORE_SCHEMA, changes: {}, whole: {}, counters: s.counters });
    synced = pick(s);
    // Se nel frattempo altri hanno scritto, al prossimo giro si scarica la versione fusa
    if (res.version === version + 1) version = res.version;
  } catch (e) {
    // Rifiutato (401/403/409): non si riprova. Altrimenti rete assente: riprova al prossimo giro
    dirty = !gestisciRifiuto(e);
  } finally {
    pushing--;
  }
}

async function pull() {
  if (dirty || pushing || fermata) return;
  try {
    const res = await api("GET");
    // Risposta di un'altra azienda (la sessione è cambiata): mai applicarla a questa scheda
    if (typeof res.aziendaId === "string" && aziendaFissata() && res.aziendaId !== aziendaFissata()) return segnalaAziendaCambiata();
    demoAzienda = res.demo === true;
    if (attesaPagamento && riprendeDopoPagamento(res.abbonamento)) {
      // Pagato: partono le modifiche rimaste in attesa, poi il giro normale manda quelle ancora da inviare.
      // Se l'invio non riesce (rete, di nuovo 402) attesaPagamento torna vero e il giro normale non parte.
      // La risposta di adesso non contiene le modifiche appena inviate: la prossima lettura scarica l'archivio unito.
      attesaPagamento = false;
      pushing++;
      try {
        await inviaSalvateInSospeso();
      } finally {
        pushing--;
      }
      if (!attesaPagamento && differenze(useStore.getState())) dirty = true;
      return;
    }
    if (devePubblicareStatoLocale({ state: res.state, schema: res.schema, demo: demoAzienda }, STORE_SCHEMA)) return await pushAll();
    if (!res.state || res.schema !== STORE_SCHEMA) {
      // Azienda vera con archivio vuoto o di un'altra versione: il browser non lo riempie e non lo sovrascrive.
      if (res.state) fermaConAvviso("L'archivio dell'azienda ha una versione diversa da quella di questo dispositivo: i dati non vengono più sincronizzati. Contatta l'assistenza.");
      return segnaAllineato();
    }
    if (dirty || pushing) return; // cambiato qualcosa durante la lettura: si riprova al prossimo giro
    if (res.version > version) {
      const clean = sanitize(res.state);
      if (!clean) return; // archivio non valido: si resta sui dati locali
      applying = true;
      useStore.setState(clean);
      applying = false;
      version = res.version;
      synced = pick(useStore.getState());
    } else if (res.abbonamento != null) {
      // Aziende registrate: i moduli li decide l'abbonamento, che cambia senza una versione nuova dell'archivio
      // (modulo aggiunto o tolto da Abbonamento, scadenza): si allineano anche a versione invariata.
      const moduli = sanitize({ moduli: res.state.moduli })?.moduli;
      if (moduli && JSON.stringify(moduli) !== JSON.stringify(useStore.getState().moduli)) {
        applying = true;
        useStore.setState({ moduli });
        applying = false;
        synced = { ...synced, moduli: useStore.getState().moduli };
      }
    }
    segnaAllineato();
  } catch (e) {
    gestisciRifiuto(e); // altrimenti server non raggiungibile: si continua in locale
  }
}

// Modifiche rimaste da inviare all'uscita: si salvano accanto alla copia locale della stessa azienda
// (la chiave dello store contiene l'id dell'azienda) e partono al prossimo accesso su questo dispositivo.
const chiaveInSospeso = () => `${useStore.persist.getOptions().name}:in-sospeso`;

function salvaInSospeso(diff: { changes: Record<string, Rec[]>; counters?: unknown }, opzioni?: { pagamento?: boolean }) {
  try {
    const prima = JSON.parse(localStorage.getItem(chiaveInSospeso()) ?? "null") as unknown;
    // Solo record con id e contatori: gli interi (regole, listini, ...) non si rimandano più tardi
    const coda = aggiungiInSospeso(prima, STORE_SCHEMA, diff.changes, diff.counters, Date.now(), LISTS, opzioni);
    localStorage.setItem(chiaveInSospeso(), JSON.stringify(coda));
  } catch {
    // memoria piena o non disponibile: resta solo la copia locale
  }
}

function togliInSospeso() {
  try {
    localStorage.removeItem(chiaveInSospeso());
  } catch {}
}

async function inviaSalvateInSospeso() {
  let raw: unknown = null;
  try {
    raw = JSON.parse(localStorage.getItem(chiaveInSospeso()) ?? "null");
  } catch {
    raw = null;
  }
  if (raw === null) return;
  // Ricostruito campo per campo: mai l'oggetto salvato così com'è, mai whole né replace, niente più vecchio di 24 ore
  // (tranne se la coda aspetta il pagamento)
  const corpo = corpoDaRiprendere(raw, STORE_SCHEMA, Date.now(), LISTS);
  if (!corpo) return togliInSospeso();
  try {
    await api("PUT", corpo);
    togliInSospeso();
  } catch (e) {
    if (!(e instanceof ErroreApi) || e.stato === 401) {
      // Rete assente o accesso perso: restano per la prossima volta. Una coda che aspettava il pagamento (senza
      // scadenza) va consegnata prima di ogni altra scrittura: altrimenti resterebbe nel browser dopo che il giro
      // normale ha già mandato copie più nuove, e al prossimo avvio le sovrascriverebbe. Si resta in attesa: la
      // prossima lettura riuscita la rimanda (vedi pull).
      if ((raw as { pagamento?: unknown }).pagamento === true) attesaPagamento = true;
      return;
    }
    // Abbonamento non pagato: la coda resta dov'è e da adesso non scade più; parte dopo il pagamento
    if (e.stato === 402 && e.motivo === "abbonamento") {
      attesaPagamento = true;
      return salvaInSospeso({ changes: {} }, { pagamento: true });
    }
    // Sessione passata a un'altra azienda: le modifiche restano in coda per la prossima volta in questa azienda
    if (e.stato === 409 && e.motivo === MOTIVO_AZIENDA_CAMBIATA) return void gestisciRifiuto(e);
    // Rifiutate dal server: riprovarle non serve, ma chi lavora deve saperlo
    togliInSospeso();
    if (e.stato === 403 || e.stato === 409) {
      gestisciRifiuto(e);
      mostraAvviso(
        "Modifiche non accettate.",
        e.stato === 409
          ? "Alcune modifiche fatte su questo dispositivo prima dell'ultima uscita non sono entrate nell'archivio dell'azienda (versione diversa). Contatta l'assistenza."
          : "Alcune modifiche fatte su questo dispositivo prima dell'ultima uscita non sono state accettate dal server per questo accesso. Controllale e rifalle se servono.",
      );
    }
  }
}

/**
 * Prova a inviare subito le modifiche in sospeso di questo dispositivo, una volta.
 * true: niente da inviare o inviate. false: non inviate; restano nella copia locale dell'azienda e partono al
 * prossimo accesso su questo dispositivo. Chi la chiama sta uscendo: un 401 non riporta all'accesso da qui.
 */
export async function inviaInSospeso(): Promise<boolean> {
  inUscita = true;
  clearTimeout(timer);
  // Una scrittura già in corso: la si aspetta (al massimo 5 secondi)
  for (let i = 0; pushing > 0 && i < 50; i++) await new Promise((r) => setTimeout(r, 100));
  if (!started) return true;
  const s = useStore.getState();
  const diff = differenze(s);
  if (!diff) {
    dirty = false;
    return true;
  }
  if (!fermata && !attesaPagamento) {
    pushing++;
    try {
      const res = await api("PUT", diff);
      synced = pick(s);
      dirty = false;
      if (res.version === version + 1) version = res.version;
      return true;
    } catch (e) {
      // si salva sotto; un 402 la segna in attesa di pagamento (non scade)
      if (e instanceof ErroreApi && e.stato === 402 && e.motivo === "abbonamento") attesaPagamento = true;
    } finally {
      pushing--;
    }
  }
  salvaInSospeso(diff, { pagamento: attesaPagamento });
  return false;
}

let started = false;
/** La sincronizzazione con l'archivio è partita su questa pagina: lo stato dello store non va più sostituito con altri dati. */
export const syncAvviata = (): boolean => started;

/**
 * Azienda vera senza copia locale: si parte da un archivio vuoto. Solo prima che la sincronizzazione parta, e come
 * stato già "noto": regole, listini, magazzini e soggetti vuoti di partenza non si mandano mai al server.
 */
export function avviaVuotoPrimaDelSync(registrata = false): boolean {
  if (started) return false;
  applying = true;
  useStore.getState().avviaVuoto(registrata);
  applying = false;
  synced = pick(useStore.getState());
  return true;
}

// Avvia la sincronizzazione; la promessa si risolve dopo il primo allineamento (o dopo un timeout)
export function startSync(): Promise<void> {
  if (started) return Promise.resolve();
  started = true;
  useStore.subscribe((s, prev) => {
    if (applying) return;
    if (!SHARED.some((k) => s[k] !== prev[k])) return;
    dirty = true;
    clearTimeout(timer);
    timer = setTimeout(pushChanges, 300);
  });
  setInterval(() => (dirty ? pushChanges() : pull()), 2500);
  const onFocus = () => !dirty && pull();
  window.addEventListener("focus", onFocus);
  document.addEventListener("visibilitychange", () => document.visibilityState === "visible" && onFocus());
  // Prima le modifiche rimaste dall'ultima uscita, poi la lettura: così il server le ha già unite
  const primo = (async () => {
    pushing++;
    try {
      await inviaSalvateInSospeso();
    } finally {
      pushing--;
    }
    await pull();
  })();
  return Promise.race([primo, new Promise<void>((r) => setTimeout(r, 2000))]);
}

// Ripristino dei dati demo: vale per tutti i dispositivi
// pushAll segna `pushing` e annulla la scrittura a pezzi messa in coda dal reset: un pull in corso non riapplica lo stato vecchio
export async function resetShared() {
  if (!demoAzienda) return; // il ripristino dei dati demo non esiste per le aziende vere
  useStore.getState().reset();
  clearTimeout(timer);
  dirty = false;
  await pushAll().catch(() => undefined);
}
