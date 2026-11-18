// Ordine e pagamento del negozio online: la logica sta qui, senza "use client", così la usano sia lo store del
// browser (gestionale e banco) sia il server (ordini del negozio pubblico). Stesse regole, stessi eventi nel registro.
import { alignedPrice, membershipAfter, placementFor, refreshAnnuncio, groupKey, shopPicks } from "./annunci.ts";
import { textFor } from "./annuncio-build.ts";
import { typeById } from "./catalog.ts";
import { euro, publishChecks } from "./logic.ts";
import { ordiniScaduti } from "./negozio-regole.ts";
import { onlinePrice } from "./pricing.ts";
import { isShippable } from "./spedizione.ts";
import type { Annuncio, AuditEvent, Order, Part, Vehicle } from "./types";

/** Le chiavi dell'archivio che un ordine o un pagamento leggono e cambiano (le altre di SHARED in sync.ts non si toccano). */
export interface StatoCondiviso {
  vehicles: Vehicle[];
  parts: Part[];
  annunci: Annuncio[];
  orders: Order[];
  audit: AuditEvent[];
  counters: { order: number; event: number };
}
export type Attore = { user: string; role: string; device: string };

const pad = (n: number) => String(n).padStart(6, "0");

// Copia di lavoro: le liste si sostituiscono, mai modificate sul posto; il registro e i contatori sono propri.
function copia<S extends StatoCondiviso>(st: S): S {
  return { ...st, counters: { ...st.counters }, audit: [...st.audit] };
}

type Evento = Omit<AuditEvent, "id" | "at" | "user" | "role" | "device">;

function registra(w: StatoCondiviso, at: string, e: Evento, attore: Attore) {
  w.counters.event += 1;
  w.audit.push({ id: `E-${pad(w.counters.event)}`, at, user: attore.user, role: attore.role as AuditEvent["role"], device: attore.device, ...e });
}

const shipOf = (p: Part) => isShippable(p, typeById(p.typeId).shippable);
const checksPass = (w: StatoCondiviso, p: Part) =>
  publishChecks(p, w.vehicles.find((v) => v.id === p.vehicleId)).every((c) => c.ok || !c.blocking);

// Ricalcolo di un annuncio dopo un cambiamento dei suoi pezzi: stato del negozio, data a zero, eBay da riallineare, testo
function toccaAnnuncio(w: StatoCondiviso, at: string, aid: string, predefinito: Attore) {
  const a = w.annunci.find((x) => x.id === aid);
  if (!a) return;
  const next = refreshAnnuncio(a, w.parts, at, (q) => textFor(a, w.parts, w.vehicles, q));
  const esaurito = !!next.esauritoDa && !a.esauritoDa;
  w.annunci = w.annunci.map((x) => (x.id === aid ? next : x));
  if (esaurito) registra(w, at, { entity: "annuncio", entityId: aid, action: "Annuncio esaurito", detail: "Nessun pezzo disponibile: l'annuncio resta, a zero" }, predefinito);
}

// Un pezzo disponibile, senza annuncio e che passa i controlli entra da solo nell'annuncio uguale con lo stesso prezzo
function collocaPezzo(w: StatoCondiviso, at: string, partId: string, predefinito: Attore) {
  const p = w.parts.find((x) => x.id === partId);
  if (!p || p.status !== "disponibile" || p.annuncioId || !checksPass(w, p)) return;
  const place = placementFor(p, groupKey(p, shipOf(p)), w.annunci);
  if (place.kind !== "unisci") return;
  w.parts = w.parts.map((x) => (x.id === partId ? { ...x, annuncioId: place.annuncioId } : x));
  registra(w, at, { entity: "annuncio", entityId: place.annuncioId, action: "Pezzo aggiunto all'annuncio", detail: partId }, predefinito);
  toccaAnnuncio(w, at, place.annuncioId, predefinito);
}

// Dopo una vendita o un pagamento fallito: i pezzi restano o escono dall'annuncio, il prezzo si riallinea, gli annunci si ricalcolano
function assesta(w: StatoCondiviso, at: string, ids: string[], predefinito: Attore) {
  const toccati = new Set<string>();
  for (const id of ids) {
    const p = w.parts.find((x) => x.id === id);
    if (!p?.annuncioId) continue;
    toccati.add(p.annuncioId);
    if (membershipAfter(p, checksPass(w, p)) === p.annuncioId) {
      const a = w.annunci.find((x) => x.id === p.annuncioId);
      const price = alignedPrice(p, a);
      if (price !== undefined) {
        w.parts = w.parts.map((x) => (x.id === id ? { ...x, price } : x));
        registra(w, at, { entity: "ricambio", entityId: id, action: `Prezzo allineato all'annuncio ${p.annuncioId}: ${euro(p.price)} → ${euro(price)}` }, predefinito);
      }
      continue;
    }
    w.parts = w.parts.map((x) => (x.id === id ? { ...x, annuncioId: undefined } : x));
    registra(
      w,
      at,
      {
        entity: "annuncio",
        entityId: p.annuncioId,
        action: "Pezzo uscito dall'annuncio",
        detail: `${id} · ${p.status === "disponibile" ? "controlli di pubblicazione non superati: torna in coda" : p.status}`,
      },
      predefinito,
    );
  }
  toccati.forEach((aid) => toccaAnnuncio(w, at, aid, predefinito));
  ids.forEach((id) => collocaPezzo(w, at, id, predefinito));
}

// Le stesse operazioni sullo stato intero (copia di lavoro dentro): le usa lo store del browser al posto di copie proprie
type Pred = Attore;
export function ricalcolaAnnuncio<S extends StatoCondiviso>(st: S, aid: string, at: string, predefinito: Pred): S {
  const w = copia(st);
  toccaAnnuncio(w, at, aid, predefinito);
  return w;
}
export function collocaPezzoInAnnuncio<S extends StatoCondiviso>(st: S, partId: string, at: string, predefinito: Pred): S {
  const w = copia(st);
  collocaPezzo(w, at, partId, predefinito);
  return w;
}
export function assestaPezzi<S extends StatoCondiviso>(st: S, ids: string[], at: string, predefinito: Pred): S {
  const w = copia(st);
  assesta(w, at, ids, predefinito);
  return w;
}

export type EsitoOrdine<S extends StatoCondiviso> =
  | { ok: true; st: S; ordineId: string }
  // Anche un rifiuto lascia una riga nel registro ("Riserva rifiutata"): st è lo stato con quella riga
  | { ok: false; error: string; conflicts?: string[]; st: S };

/**
 * Ordine del negozio per annunci: il pezzo che parte per primo si sceglie nello stesso aggiornamento che controlla
 * la disponibilità, così lo stesso pezzo non si vende due volte.
 * attore: chi ha fatto l'ordine (il cliente); predefinito: firma delle righe di registro "di sistema" (annuncio esaurito, ...), se diversa.
 */
export function ordineNegozio<S extends StatoCondiviso>(
  st: S,
  i: { annuncioIds: string[]; cliente: string; consegna?: "corriere" | "ritiro"; attore?: Attore; predefinito?: Attore },
  at: string,
): EsitoOrdine<S> {
  if (!i.annuncioIds.length) return { ok: false, error: "Il carrello è vuoto", st };
  const attore = i.attore;
  const predefinito = i.predefinito ?? attore ?? { user: "Negozio online", role: "cliente", device: "Negozio online" };
  const w = copia(st);
  const r = shopPicks(i.annuncioIds, w.annunci, w.parts);
  if (r.conflicts.length || !r.picks.length) {
    registra(w, at, { entity: "ordine", entityId: "—", action: "Riserva rifiutata", detail: `${r.conflicts.join(", ")} non disponibile (negozio)` }, attore ?? predefinito);
    return { ok: false, error: "Ricambio non più disponibile", conflicts: r.conflicts, st: w };
  }
  const partIds = r.picks.map((x) => x.partId);
  const prices = Object.fromEntries(r.picks.map((x) => [x.partId, onlinePrice(x.price) ?? 0]));
  const amount = Math.round(Object.values(prices).reduce((t, x) => t + x, 0) * 100) / 100;
  const pickupOnly = w.parts.some((p) => partIds.includes(p.id) && !shipOf(p));
  const n = w.counters.order + 1;
  const id = `O-${pad(n)}`;
  const annunciOrdine = [...new Set(r.picks.map((x) => x.annuncioId))];
  w.parts = w.parts.map((x) => (partIds.includes(x.id) ? { ...x, status: "riservato" as const } : x));
  w.orders = [
    { id, channel: "negozio", delivery: pickupOnly ? "ritiro" : i.consegna, partIds, amount, prices, status: "in attesa di pagamento", customer: i.cliente, createdAt: at, history: [{ at, status: "in attesa di pagamento" }] },
    ...w.orders,
  ];
  w.counters.order = n;
  const chi = attore ?? predefinito;
  registra(w, at, { entity: "ordine", entityId: id, action: "Ordine creato", detail: `negozio · ${annunciOrdine.join(", ")} · ${partIds.join(", ")}` }, chi);
  for (const pid of partIds) registra(w, at, { entity: "ricambio", entityId: pid, action: "Stato: disponibile → riservato", detail: id }, chi);
  annunciOrdine.forEach((aid) => toccaAnnuncio(w, at, aid, predefinito));
  return { ok: true, st: w, ordineId: id };
}

/**
 * Pagamento (simulato) di un ordine in attesa: riuscito, i pezzi sono venduti; rifiutato, tornano disponibili.
 * Un ordine che non c'è o non è in attesa non cambia nulla. predefinito: firma delle righe di sistema, se diversa da attore.
 */
export function pagaOrdine<S extends StatoCondiviso>(st: S, ordineId: string, riuscito: boolean, attore: Attore, at: string, predefinito?: Attore, scaduta = false): S {
  const o = st.orders.find((x) => x.id === ordineId);
  if (!o || o.status !== "in attesa di pagamento") return st;
  const w = copia(st);
  const status = riuscito ? "pagato" : "pagamento fallito";
  w.orders = w.orders.map((x) =>
    x.id === ordineId ? { ...x, status, paymentRef: riuscito ? `PAY-DEMO-${ordineId.slice(2)}` : undefined, history: [...x.history, { at, status, note: scaduta ? "Riserva scaduta: nessun pagamento entro 30 minuti" : riuscito ? "Conferma dal provider (simulata)" : "Rifiuto dal provider (simulato)" }] } : x,
  );
  // Venduto: esce dal negozio; pagamento fallito: torna disponibile
  w.parts = w.parts.map((x) => (o.partIds.includes(x.id) ? { ...x, status: riuscito ? "venduto" : "disponibile" } : x));
  registra(w, at, { entity: "ordine", entityId: ordineId, action: scaduta ? "Riserva scaduta" : riuscito ? "Pagamento confermato" : "Pagamento fallito", detail: riuscito ? "Webhook provider (simulato)" : "Disponibilità ripristinata" }, attore);
  for (const pid of o.partIds) {
    registra(w, at, { entity: "ricambio", entityId: pid, action: riuscito ? "Stato: riservato → venduto" : "Stato: riservato → disponibile", detail: ordineId }, attore);
  }
  assesta(w, at, o.partIds, predefinito ?? attore);
  return w;
}

const SISTEMA: Attore = { user: "Negozio online", role: "sistema", device: "Negozio online" };

/** Rilascia le riserve degli ordini del negozio non pagati da più di 30 minuti: pezzi di nuovo disponibili, come un pagamento fallito, con la riga "Riserva scaduta". */
export function rilasciaScaduti<S extends StatoCondiviso>(st: S, oraMs: number): S {
  const at = new Date(oraMs).toISOString();
  return ordiniScaduti(st.orders, oraMs).reduce((s, id) => pagaOrdine(s, id, false, SISTEMA, at, SISTEMA, true), st);
}

/** L'archivio dell'azienda con le sole chiavi che ordine e pagamento cambiano sostituite: le altre restano com'erano. */
export function nelArchivio(s: Record<string, unknown>, st: StatoCondiviso): Record<string, unknown> {
  return { ...s, parts: st.parts, orders: st.orders, counters: { ...(s.counters as object), ...st.counters }, audit: st.audit, annunci: st.annunci };
}
