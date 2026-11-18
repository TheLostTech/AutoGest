// Annunci con più pezzi: raggruppamento, quantità, stato. Modulo puro.
import type { Annuncio, Gpsr, ListingStatus, Part, StatoNegozio, Vehicle } from "./types";

/** Codice originale in forma confrontabile: maiuscolo, senza spazi, punti e trattini. */
export function normalizeOem(oem: string): string {
  return oem.toUpperCase().replace(/[\s.\-]+/g, "");
}

/** Chiave di raggruppamento; senza codice verificato non c'è chiave. */
export function groupKey(p: Part, shippable: boolean): string | undefined {
  if (!p.oemVerified || !p.oem) return undefined;
  const oem = normalizeOem(p.oem);
  if (!oem) return undefined;
  return `${p.typeId}|${oem}|${p.side ?? "-"}|${p.condition}|${shippable ? "S" : "R"}`;
}

export function partsOf(a: Annuncio, parts: Part[]): Part[] {
  return parts.filter((p) => p.annuncioId === a.id);
}

export function quantityOf(a: Annuncio, parts: Part[]): number {
  return partsOf(a, parts).filter((p) => p.status === "disponibile").length;
}

/** I pezzi che partono per primi: i disponibili entrati prima. */
export function nextToShip(a: Annuncio, parts: Part[], n = 1): Part[] {
  return partsOf(a, parts)
    .filter((p) => p.status === "disponibile")
    .sort((x, y) => x.createdAt.localeCompare(y.createdAt) || x.id.localeCompare(y.id))
    .slice(0, n);
}

/** Ritirato: esiste almeno un canale (negozio e/o eBay) e ogni canale esistente è ritirato. */
export function isWithdrawn(a: Annuncio): boolean {
  const stati: string[] = [];
  if (a.negozio) stati.push(a.negozio.stato);
  if (a.ebay) stati.push(a.ebay.stato);
  return stati.length > 0 && stati.every((s) => s === "ritirato");
}

export function negozioStato(a: Annuncio, qty: number): StatoNegozio | undefined {
  if (!a.negozio) return undefined;
  if (a.negozio.stato === "ritirato") return "ritirato";
  return qty > 0 ? "online" : "esaurito";
}

export type Placement =
  | { kind: "nuovo" }
  | { kind: "unisci"; annuncioId: string }
  | { kind: "prezzo diverso"; annuncioId: string; prezzoAnnuncio: number }
  | { kind: "annuncio ritirato"; annuncioId: string };

export function placementFor(p: Part, key: string | undefined, annunci: Annuncio[]): Placement {
  if (!key || p.price === undefined) return { kind: "nuovo" };
  const found = annunci.filter((a) => a.chiave === key);
  if (found.length === 0) return { kind: "nuovo" };
  const a = found.find((x) => !isWithdrawn(x)) ?? found[0];
  if (isWithdrawn(a)) return { kind: "annuncio ritirato", annuncioId: a.id };
  if (a.price !== p.price) {
    return { kind: "prezzo diverso", annuncioId: a.id, prezzoAnnuncio: a.price };
  }
  return { kind: "unisci", annuncioId: a.id };
}

/** Vendita eBay: i pezzi entrati per primi, quanti ce ne sono; `mancano` quelli comprati ma non più disponibili. */
export function pickForSale(a: Annuncio, parts: Part[], quantita: number): { partIds: string[]; mancano: number } {
  const n = Math.max(0, Math.floor(quantita));
  const partIds = nextToShip(a, parts, n).map((p) => p.id);
  return { partIds, mancano: n - partIds.length };
}

/** Nota "da gestire" di un ordine eBay a cui mancano pezzi. */
export function missingNote(mancano: number): string | undefined {
  if (mancano <= 0) return undefined;
  return mancano === 1 ? "manca 1 pezzo" : `mancano ${mancano} pezzi`;
}

/**
 * Annuncio a cui il pezzo resta legato dopo un cambio di stato o di dati.
 * Scartato o invendibile: esce subito. Disponibile: resta solo se passa i controlli di pubblicazione.
 * Negli altri stati (bozza di un reso, riservato, venduto) tiene il suo annuncio.
 */
export function membershipAfter(p: Part, checksPass: boolean): string | undefined {
  if (!p.annuncioId) return undefined;
  if (p.status === "scartato" || p.status === "invendibile") return undefined;
  if (p.status === "disponibile" && !checksPass) return undefined;
  return p.annuncioId;
}

/**
 * Prezzo da dare a un pezzo che resta o rientra disponibile nel suo annuncio: quello dell'annuncio,
 * se è diverso (es. vendita annullata o reso approvato dopo un cambio di prezzo). Un prezzo solo per annuncio.
 */
export function alignedPrice(p: Part, a: Annuncio | undefined): number | undefined {
  if (!a || p.annuncioId !== a.id || p.status !== "disponibile") return undefined;
  return p.price === a.price ? undefined : a.price;
}

/** Quali dati degli annunci cambiano con il veicolo d'origine: il testo (marca, modello, versione, anno, km) e il GPSR (marca, anno). */
export function listingFieldsChanged(
  prev: Pick<Vehicle, "make" | "model" | "version" | "year" | "km">,
  next: Pick<Vehicle, "make" | "model" | "version" | "year" | "km">,
): { text: boolean; gpsr: boolean } {
  const gpsr = prev.make !== next.make || prev.year !== next.year;
  const text = gpsr || prev.model !== next.model || prev.version !== next.version || prev.km !== next.km;
  return { text, gpsr };
}

/**
 * GPSR dopo un cambio di marca o anno del veicolo: quello ricalcolato, salvo che l'operatore l'abbia confermato a mano
 * (resta il suo finché non lo cambia lui). undefined = resta quello di prima.
 */
export function gpsrAfterVehicleChange(a: Pick<Annuncio, "gpsrManuale">, ricalcolato: Gpsr | undefined): Gpsr | undefined {
  return a.gpsrManuale ? undefined : ricalcolato;
}

/** Numero della categoria eBay scritto dall'operatore: solo cifre. "" = nessuna (la sceglie eBay); undefined = non valido. */
export function categoriaEbayDa(testo: string): string | "" | undefined {
  const t = testo.trim();
  if (!t) return "";
  return /^\d{1,12}$/.test(t) ? t : undefined;
}

/**
 * Pezzi da riservare per un ordine del negozio: uno per ogni volta che l'annuncio compare.
 * Si compra solo un annuncio online sul negozio, con abbastanza pezzi disponibili e un prezzo.
 */
export function shopPicks(
  annuncioIds: string[],
  annunci: Annuncio[],
  parts: Part[],
): { picks: { annuncioId: string; partId: string; price: number }[]; conflicts: string[] } {
  const counts = new Map<string, number>();
  for (const id of annuncioIds) counts.set(id, (counts.get(id) ?? 0) + 1);
  const picks: { annuncioId: string; partId: string; price: number }[] = [];
  const conflicts: string[] = [];
  for (const [id, n] of counts) {
    const a = annunci.find((x) => x.id === id);
    const ps = a ? nextToShip(a, parts, n) : [];
    if (!a || a.negozio?.stato !== "online" || !(a.price > 0) || ps.length < n) {
      conflicts.push(id);
      continue;
    }
    for (const p of ps) picks.push({ annuncioId: id, partId: p.id, price: a.price });
  }
  return { picks, conflicts };
}

/**
 * Annuncio ricalcolato dopo un cambiamento dei suoi pezzi: stato del negozio dalla quantità,
 * data dell'ultima volta a zero, eBay da riallineare (se non ritirato), testo riscritto se non modificato.
 */
export function refreshAnnuncio(
  a: Annuncio,
  parts: Part[],
  at: string,
  regen?: (quanti: number) => { titolo: string; descrizione: string } | undefined,
): Annuncio {
  const qty = quantityOf(a, parts);
  const stato = negozioStato(a, qty);
  const next: Annuncio = {
    ...a,
    negozio: stato ? { stato } : a.negozio,
    esauritoDa: qty === 0 ? (a.esauritoDa ?? at) : undefined,
    ebay: a.ebay && a.ebay.stato !== "ritirato" ? { ...a.ebay, daRiallineare: true } : a.ebay,
  };
  if (!a.testoModificato && regen) {
    const t = regen(qty);
    if (t) return { ...next, titolo: t.titolo, descrizione: t.descrizione };
  }
  return next;
}

export function listingOf(p: Part, annunci: Annuncio[]): ListingStatus {
  if (!p.annuncioId) return "non pubblicato";
  const a = annunci.find((x) => x.id === p.annuncioId);
  const live = !!a && !isWithdrawn(a);
  if (live && (p.status === "disponibile" || p.status === "riservato")) return "pubblicato";
  return "ritirato";
}

export const GPSR_ERRORE = "Conferma i dati GPSR prima di pubblicare su eBay";

/** eBay non si attiva finché il GPSR è "da confermare". */
export function gpsrBlocksEbay(gpsr: Gpsr): boolean {
  return gpsr.tipo === "da confermare";
}
