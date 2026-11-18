// Pezzi gemelli dei dati demo: garantiscono un annuncio con più pezzi uguali. Modulo puro: solo import type.
import type { Part } from "./types";

export interface TwinCatalog {
  oem: string;
  manufacturer: string;
  platforms: string[];
  source: string;
}

/**
 * Pezzo da cui nascono i gemelli: pubblicato, disponibile, con prezzo e con un codice di catalogo.
 * Prima un cerchio (un'auto ne ha quattro uguali), poi un qualsiasi tipo spedibile. Sempre il primo nell'ordine dato.
 */
export function twinSource(
  published: Part[],
  catalogOf: (p: Part) => TwinCatalog | null | undefined,
  shippableType: (typeId: string) => boolean,
): Part | undefined {
  const ok = (p: Part) => p.status === "disponibile" && typeof p.price === "number" && p.price > 0 && !!catalogOf(p);
  return published.find((p) => p.typeId === "cerchio" && ok(p)) ?? published.find((p) => shippableType(p.typeId) && ok(p));
}

/**
 * Il pezzo con il codice verificato dal catalogo (se non lo era già) e i suoi gemelli, entrati un'ora dopo l'altro:
 * stesso tipo, codice, lato, condizione, spedizione e prezzo, quindi stessa chiave di raggruppamento.
 */
export function withTwins(src: Part, cat: TwinCatalog, ids: string[]): { source: Part; twins: Part[] } {
  const source: Part =
    src.oemVerified && src.oem
      ? src
      : { ...src, oem: cat.oem, oemVerified: true, manufacturer: cat.manufacturer, compat: { platforms: [...cat.platforms], source: cat.source, verified: true } };
  const twins = ids.map((id, i) => ({
    ...source,
    id,
    annuncioId: undefined,
    createdAt: new Date(new Date(source.createdAt).getTime() + (i + 1) * 36e5).toISOString(),
    photos: [...source.photos],
    location: source.location && { ...source.location },
    compat: source.compat && { ...source.compat, platforms: [...source.compat.platforms] },
  }));
  return { source, twins };
}
