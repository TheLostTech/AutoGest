"use client";

// Sincronizzazione della demo tra dispositivi (telefono, computer) tramite /api/demo-state.
// Ruolo e veicolo attivo restano propri di ogni dispositivo; tutto il resto è condiviso.
import { useSyncExternalStore } from "react";
import { STORE_SCHEMA, useStore } from "./store";
import { devePubblicareStatoLocale } from "./sync-regole";
import { percorsoPubblico } from "./accesso/percorsi";

const PREPEND = ["vehicles", "parts", "annunci", "orders", "docs", "firs"] as const;
const APPEND = ["audit", "wasteMoves", "inventory"] as const;
const LISTS = [...PREPEND, ...APPEND] as const;
const WHOLE = ["rules", "listini", "warehouses", "soggetti"] as const;
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
let avviso: string | null = null;
let fermata = false;
const ascoltatoriAvviso = new Set<() => void>();
function fermaConAvviso(testo: string) {
  fermata = true;
  clearTimeout(timer);
  avviso = testo;
  ascoltatoriAvviso.forEach((f) => f());
}
export const useSyncAvviso = (): string | null =>
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

// 401: la sessione non vale più, si torna all'accesso (tranne sulle pagine pubbliche). 403/409: ci si ferma con un avviso.
function gestisciRifiuto(e: unknown): boolean {
  if (!(e instanceof ErroreApi)) return false;
  if (e.stato === 401) {
    fermata = true;
    if (typeof window !== "undefined" && !percorsoPubblico(window.location.pathname)) {
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
    fermaConAvviso("Non hai più accesso a questa azienda: i dati non vengono più sincronizzati. Accedi di nuovo.");
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
  const r = await fetch("/api/demo-state", {
    method,
    cache: "no-store",
    headers: body ? { "Content-Type": "application/json" } : undefined,
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
  if (fermata || !demoAzienda) return; // lo stato intero si manda solo per l'azienda demo
  pushing++;
  clearTimeout(timer);
  try {
    const s = useStore.getState();
    const res = await api("PUT", { schema: STORE_SCHEMA, replace: true, state: pick(s) });
    version = res.version;
    synced = pick(s);
    segnaAllineato();
  } catch (e) {
    if (!gestisciRifiuto(e)) throw e;
  } finally {
    pushing--;
  }
}

async function pushChanges() {
  if (pushing || fermata) return;
  pushing++;
  dirty = false;
  try {
    const s = useStore.getState();
    const changes: Record<string, Rec[]> = {};
    for (const k of LISTS) {
      const before = new Map(((synced[k] as Rec[] | undefined) ?? []).map((r) => [keyOf(r), r]));
      const changed = (s[k] as Rec[]).filter((r) => before.get(keyOf(r)) !== r);
      if (changed.length) changes[k] = changed;
    }
    const whole = Object.fromEntries(WHOLE.filter((k) => s[k] !== synced[k]).map((k) => [k, s[k]]));
    const res = await api("PUT", { schema: STORE_SCHEMA, changes, whole, counters: s.counters });
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
    demoAzienda = res.demo === true;
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
    }
    segnaAllineato();
  } catch (e) {
    gestisciRifiuto(e); // altrimenti server non raggiungibile: si continua in locale
  }
}

let started = false;

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
  return Promise.race([pull(), new Promise<void>((r) => setTimeout(r, 2000))]);
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
