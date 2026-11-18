// Annunci con più pezzi: raggruppamento, quantità, stato. Modulo puro.
import type { Annuncio, ListingStatus, Part, StatoNegozio } from "./types";

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

export function listingOf(p: Part, annunci: Annuncio[]): ListingStatus {
  if (!p.annuncioId) return "non pubblicato";
  const a = annunci.find((x) => x.id === p.annuncioId);
  const live = !!a && !isWithdrawn(a);
  if (live && (p.status === "disponibile" || p.status === "riservato")) return "pubblicato";
  return "ritirato";
}
