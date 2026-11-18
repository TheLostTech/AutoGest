"use client";

// Esecutore lato browser: manda a eBay (tramite il ponte sul server) gli annunci da riallineare, uno alla volta,
// e importa le vendite. Le funzioni pure stanno in ebay/sync-puro.ts.
import { useEffect } from "react";
import { useStore } from "./store";
import { nextToSync } from "./ebay/sync-puro";
import { richiestaPer } from "./ebay/richiesta";
import type { EsitoAllinea, RichiestaAllinea, StatoPonte, VenditaEbay } from "./ebay/contratto";
import { nextToShip, partsOf, quantityOf } from "./annunci";
import { EBAY_CATEGORY_QUERY, compatVehicles } from "./annuncio-testo";
import { PLATFORMS, typeById } from "./catalog";
import { onlinePrice } from "./pricing";
import type { Annuncio } from "./types";

type Store = ReturnType<typeof useStore.getState>;
const OGNI_MS = 60_000;
const VENDITE_OGNI_MS = 5 * 60_000;
const ULTIMO_CONTROLLO = "ebay-vendite-ultimo-controllo";

// Una sola sincronizzazione alla volta per scheda. Altre schede o dispositivi possono mandare lo stesso annuncio: il ponte è idempotente.
let inCorso = false;
// Ultima richiesta andata in errore per annuncio: non si rimanda uguale finché non cambia o scatta il giro dei 60 secondi
const ultimoErrore = new Map<string, string>();

function richiestaDi(a: Annuncio, st: Store): RichiestaAllinea {
  const mine = partsOf(a, st.parts);
  const prossimo = nextToShip(a, st.parts)[0];
  const recente = [...mine].sort((x, y) => (y.createdAt ?? "").localeCompare(x.createdAt ?? ""))[0];
  return richiestaPer(
    a,
    {
      quantita: quantityOf(a, st.parts),
      foto: (prossimo ?? recente)?.photos ?? [],
      compatibilita: compatVehicles(mine, st.vehicles, PLATFORMS),
      categoriaQuery: EBAY_CATEGORY_QUERY[a.typeId] ?? typeById(a.typeId).name,
      typeShippable: typeById(a.typeId).shippable,
    },
    (base) => onlinePrice(base) ?? base,
  );
}

async function manda(r: RichiestaAllinea): Promise<EsitoAllinea | undefined> {
  try {
    const res = await fetch("/api/ebay/allinea", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(r) });
    if (res.ok) return (await res.json()) as EsitoAllinea;
    if (res.status === 400) return { stato: "errore", avvisi: [], errore: "La richiesta per eBay non è valida: controlla titolo, prezzo e foto" };
    return undefined; // server in difficoltà: si riprova al giro dopo
  } catch {
    return undefined; // niente rete: si riprova al giro dopo
  }
}

export async function riallinea(force = false): Promise<void> {
  if (inCorso) return;
  inCorso = true;
  try {
    const tentati = new Set<string>();
    for (;;) {
      const st = useStore.getState();
      const a = nextToSync(st.annunci.filter((x) => !tentati.has(x.id)));
      if (!a) break;
      tentati.add(a.id);
      const r = richiestaDi(a, st);
      const chiave = JSON.stringify(r);
      if (!force && a.ebay?.errore && ultimoErrore.get(a.id) === chiave) continue;
      const esito = await manda(r);
      if (!esito) break;
      if (esito.stato === "errore") ultimoErrore.set(a.id, chiave);
      else ultimoErrore.delete(a.id);
      st.setEbayResult(a.id, esito, { quantita: r.quantita, prezzo: r.prezzo, attivo: r.attivo, titolo: r.titolo });
    }
  } finally {
    inCorso = false;
  }
}

export async function statoPonte(): Promise<StatoPonte | undefined> {
  try {
    const res = await fetch("/api/ebay/stato", { cache: "no-store" });
    return res.ok ? ((await res.json()) as StatoPonte) : undefined;
  } catch {
    return undefined;
  }
}

function leggiUltimo(): string {
  try {
    const v = localStorage.getItem(ULTIMO_CONTROLLO);
    if (v) return v;
  } catch {}
  return new Date(Date.now() - 7 * 24 * 3600_000).toISOString();
}

/** Chiede a eBay le vendite dall'ultimo controllo e le importa. Restituisce quante vendite nuove ha creato. */
export async function controllaVendite(): Promise<{ ok: boolean; nuove: number; errore?: string }> {
  const prima = new Date().toISOString();
  try {
    const res = await fetch(`/api/ebay/vendite?da=${encodeURIComponent(leggiUltimo())}`, { cache: "no-store" });
    if (!res.ok) return { ok: false, nuove: 0, errore: "eBay non risponde" };
    const { vendite } = (await res.json()) as { vendite: VenditaEbay[] };
    const st = useStore.getState();
    let nuove = 0;
    for (const v of vendite) {
      const gia = useStore.getState().orders.some((o) => o.ebayOrderId === v.orderId);
      const r = st.importEbaySale(v);
      if (r.ok && !gia) nuove++;
    }
    try {
      localStorage.setItem(ULTIMO_CONTROLLO, prima);
    } catch {}
    return { ok: true, nuove };
  } catch {
    return { ok: false, nuove: 0, errore: "eBay non risponde" };
  }
}

/** Una vendita di prova, come se arrivasse da eBay: serve per vedere cosa succede senza un conto vero. */
export function simulateEbaySale(annuncioId: string, quantita: number): { ok: true; value: string } | { ok: false; error: string } {
  const st = useStore.getState();
  const a = st.annunci.find((x) => x.id === annuncioId);
  if (!a) return { ok: false, error: "Annuncio non trovato" };
  if (!Number.isInteger(quantita) || quantita < 1) return { ok: false, error: "Scrivi quanti pezzi" };
  const at = new Date().toISOString();
  return st.importEbaySale({
    orderId: `SIM-ORD-${Date.now().toString(36).toUpperCase()}`,
    sku: annuncioId,
    quantita,
    prezzoUnitario: onlinePrice(a.price) ?? a.price,
    acquirente: "Acquirente eBay (prova)",
    at,
  });
}

/** Da montare una volta sola nella gestione: riallinea subito quando serve, all'avvio e ogni 60 secondi; controlla le vendite ogni 5 minuti. */
export function useEbaySync(): void {
  useEffect(() => {
    let attivo = true;
    let t: ReturnType<typeof setTimeout> | undefined;
    const presto = () => {
      clearTimeout(t);
      t = setTimeout(() => attivo && void riallinea(false), 400);
    };
    void riallinea(true);
    const unsub = useStore.subscribe((s, prev) => {
      if (s.annunci !== prev.annunci) presto();
    });
    const giro = setInterval(() => void riallinea(true), OGNI_MS);
    const vendite = setInterval(async () => {
      const p = await statoPonte();
      if (attivo && p?.modo === "Sandbox" && p.collegato) void controllaVendite();
    }, VENDITE_OGNI_MS);
    return () => {
      attivo = false;
      clearTimeout(t);
      unsub();
      clearInterval(giro);
      clearInterval(vendite);
    };
  }, []);
}
