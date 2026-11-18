"use client";

// Esecutore lato browser: manda a eBay (tramite il ponte sul server) gli annunci da riallineare, uno alla volta,
// e importa le vendite. Le funzioni pure stanno in ebay/sync-puro.ts.
import { useEffect } from "react";
import { useStore } from "./store";
import { syncAllineato, syncPronto } from "./sync";
import { daPerVendite, esitoDaStato, nextToSync, type Attuale } from "./ebay/sync-puro";
import { fotoPerEbay } from "./ebay/payload";
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
// Un cambiamento arrivato mentre un giro è in corso: a fine giro se ne fa un altro
let ripeti = false;
// Ultima richiesta andata in errore per annuncio: non si rimanda uguale finché non cambia o scatta il giro dei 60 secondi
const ultimoErrore = new Map<string, string>();

const prezzoOnline = (base: number) => onlinePrice(base) ?? base;
/** Quantità e prezzo online di adesso: gli stessi calcoli della richiesta, per accorgersi di una differenza con eBay. */
const attualeDi = (st: Store) => (a: Annuncio): Attuale => ({ quantita: quantityOf(a, st.parts), prezzo: prezzoOnline(a.price) });

/** Richiesta per eBay e avvisi dell'app (es. foto rimaste nel telefono, che non vanno su eBay). */
function richiestaDi(a: Annuncio, st: Store): { r: RichiestaAllinea; avvisi: string[] } {
  const mine = partsOf(a, st.parts);
  const prossimo = nextToShip(a, st.parts)[0];
  const recente = [...mine].sort((x, y) => (y.createdAt ?? "").localeCompare(x.createdAt ?? ""))[0];
  // Solo foto già sul server: quelle rimaste nel telefono (data: URL) gonfierebbero la richiesta oltre il limite
  const foto = fotoPerEbay((prossimo ?? recente)?.photos ?? []);
  const r = richiestaPer(
    a,
    {
      quantita: quantityOf(a, st.parts),
      foto: foto.foto,
      compatibilita: compatVehicles(mine, st.vehicles, PLATFORMS),
      categoriaQuery: EBAY_CATEGORY_QUERY[a.typeId] ?? typeById(a.typeId).name,
      typeShippable: typeById(a.typeId).shippable,
    },
    prezzoOnline,
  );
  return { r, avvisi: foto.avviso ? [foto.avviso] : [] };
}

async function manda(r: RichiestaAllinea): Promise<EsitoAllinea | "salta" | "fermati"> {
  let res: Response;
  try {
    res = await fetch("/api/ebay/allinea", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(r) });
  } catch {
    return "fermati"; // niente rete: si riprova al giro dopo
  }
  if (!res.ok) return esitoDaStato(res.status);
  try {
    return (await res.json()) as EsitoAllinea;
  } catch {
    return "salta"; // risposta rovinata: questo annuncio riparte al giro dopo
  }
}

export async function riallinea(force = false): Promise<void> {
  // Prima dell'allineamento con gli altri dispositivi i dati di questo potrebbero essere vecchi
  if (!syncAllineato()) return;
  if (inCorso) {
    ripeti = true;
    return;
  }
  inCorso = true;
  try {
    const tentati = new Set<string>();
    for (;;) {
      const st = useStore.getState();
      const a = nextToSync(st.annunci.filter((x) => !tentati.has(x.id)), attualeDi(st));
      if (!a) break;
      tentati.add(a.id);
      const { r, avvisi } = richiestaDi(a, st);
      const chiave = JSON.stringify(r);
      if (!force && a.ebay?.errore && ultimoErrore.get(a.id) === chiave) continue;
      const esito = await manda(r);
      if (esito === "fermati") break;
      // Server in difficoltà su questo annuncio: si passa agli altri, questo riparte al giro dei 60 secondi
      if (esito === "salta") continue;
      if (esito.stato === "errore") ultimoErrore.set(a.id, chiave);
      else ultimoErrore.delete(a.id);
      st.setEbayResult(a.id, { ...esito, avvisi: [...avvisi, ...(esito.avvisi ?? [])] }, { quantita: r.quantita, prezzo: r.prezzo, attivo: r.attivo, titolo: r.titolo });
    }
  } finally {
    inCorso = false;
  }
  if (ripeti) {
    ripeti = false;
    await riallinea(false);
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

/** Da quando chiedere: ultimo controllo di questo dispositivo meno un'ora (il server non guarda comunque prima dell'ultimo controllo di chiunque). */
function leggiDa(): string {
  let v: string | null = null;
  try {
    v = localStorage.getItem(ULTIMO_CONTROLLO);
  } catch {}
  return daPerVendite(v, Date.now());
}

/** Chiede a eBay le vendite dall'ultimo controllo e le importa. Restituisce quante vendite nuove ha creato. */
export async function controllaVendite(): Promise<{ ok: boolean; nuove: number; errore?: string }> {
  // Con dati vecchi la vendita finirebbe su pezzi già venduti altrove, e la lettura dopo la cancellerebbe
  if (!syncAllineato()) return { ok: false, nuove: 0, errore: "Dati non ancora allineati con gli altri dispositivi: riprova tra poco" };
  const prima = new Date().toISOString();
  try {
    const res = await fetch("/api/ebay/vendite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ da: leggiDa() }),
      cache: "no-store",
    });
    if (!res.ok) return { ok: false, nuove: 0, errore: "eBay non risponde" };
    const { vendite } = (await res.json()) as { vendite: VenditaEbay[] };
    const st = useStore.getState();
    let nuove = 0;
    let fallite = 0;
    for (const v of vendite) {
      const gia = useStore.getState().orders.some((o) => o.ebayOrderId === v.orderId);
      const r = st.importEbaySale(v);
      if (!r.ok) fallite++;
      else if (!gia) nuove++;
    }
    // Se una vendita non si è importata, la data non avanza: al prossimo controllo si riprova (le già importate si ignorano)
    if (fallite > 0) return { ok: false, nuove, errore: `${fallite} ${fallite === 1 ? "vendita" : "vendite"} eBay non importate` };
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

/**
 * Da montare una volta sola nella gestione: riallinea subito quando serve, all'avvio e ogni 60 secondi; controlla le vendite ogni 5 minuti.
 * Tutto parte solo dopo il primo allineamento vero con gli altri dispositivi (non basta il timeout di avvio):
 * un dispositivo tornato dopo giorni manderebbe a eBay quantità vecchie.
 */
export function useEbaySync(): void {
  useEffect(() => {
    let attivo = true;
    let t: ReturnType<typeof setTimeout> | undefined;
    let unsub: (() => void) | undefined;
    let giro: ReturnType<typeof setInterval> | undefined;
    let vendite: ReturnType<typeof setInterval> | undefined;
    const presto = () => {
      clearTimeout(t);
      t = setTimeout(() => attivo && void riallinea(false), 400);
    };
    const controlloAutomatico = async () => {
      const p = await statoPonte();
      if (attivo && p?.modo === "Sandbox" && p.collegato) void controllaVendite();
    };
    void syncPronto().then(() => {
      if (!attivo) return;
      void riallinea(true);
      unsub = useStore.subscribe((s, prev) => {
        if (s.annunci !== prev.annunci || s.parts !== prev.parts) presto();
      });
      giro = setInterval(() => void riallinea(true), OGNI_MS);
      void controlloAutomatico();
      vendite = setInterval(() => void controlloAutomatico(), VENDITE_OGNI_MS);
    });
    return () => {
      attivo = false;
      clearTimeout(t);
      unsub?.();
      clearInterval(giro);
      clearInterval(vendite);
    };
  }, []);
}
