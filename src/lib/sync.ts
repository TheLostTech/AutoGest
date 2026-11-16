"use client";

// Sincronizzazione della demo tra dispositivi (telefono, computer) tramite /api/demo-state.
// Ruolo e veicolo attivo restano propri di ogni dispositivo; tutto il resto è condiviso.
import { STORE_SCHEMA, useStore } from "./store";

const PREPEND = ["vehicles", "parts", "orders", "docs", "firs"] as const;
const APPEND = ["audit", "wasteMoves"] as const;
const LISTS = [...PREPEND, ...APPEND] as const;
const WHOLE = ["rules", "listini"] as const;
const SHARED = [...LISTS, ...WHOLE, "counters"] as const;

type S = ReturnType<typeof useStore.getState>;
type Rec = { id?: string; typeId?: string };

let version = 0;
let applying = false;
let dirty = false;
let pushing = false;
let timer: ReturnType<typeof setTimeout> | undefined;
let synced: Partial<S> = {}; // ultimo stato condiviso noto (riferimenti), per calcolare cosa è cambiato

const pick = (s: S) => Object.fromEntries(SHARED.map((k) => [k, s[k]])) as Partial<S>;
const keyOf = (r: Rec) => r.id ?? r.typeId ?? "";

async function api(method: "GET" | "PUT", body?: unknown) {
  const r = await fetch("/api/demo-state", {
    method,
    cache: "no-store",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(`demo-state ${r.status}`);
  return r.json();
}

async function pushAll() {
  const s = useStore.getState();
  const res = await api("PUT", { schema: STORE_SCHEMA, replace: true, state: pick(s) });
  version = res.version;
  synced = pick(s);
}

async function pushChanges() {
  if (pushing) return;
  pushing = true;
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
  } catch {
    dirty = true; // rete assente: riprova al prossimo giro
  } finally {
    pushing = false;
  }
}

async function pull() {
  if (dirty || pushing) return;
  try {
    const res = await api("GET");
    if (!res.state || res.schema !== STORE_SCHEMA) return pushAll();
    if (res.version > version && !dirty && !pushing) {
      applying = true;
      useStore.setState(res.state);
      applying = false;
      version = res.version;
      synced = pick(useStore.getState());
    }
  } catch {
    /* server non raggiungibile: si continua in locale */
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
export async function resetShared() {
  useStore.getState().reset();
  dirty = false;
  await pushAll().catch(() => undefined);
}
