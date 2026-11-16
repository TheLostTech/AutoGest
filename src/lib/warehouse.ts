import type { Location, Part } from "./types";

// Struttura fisica del magazzino (demo). Formato come il gestionale attuale del cliente:
// Mag/Corsia 3/T03 · Scaffale 104 · Ripiano B · Contenitore 1
export interface Warehouse {
  id: string;
  name: string;
  desc: string;
  categories: string[];
  corsie: number;
  scaffali: number; // per corsia, numerati 101, 102…
  ripiani: string; // lettere dal basso
  contenitori: number; // 0 = ripiano libero (pezzi voluminosi)
  perSlot: number; // capienza indicativa per contenitore/ripiano
}

export const WAREHOUSES: Warehouse[] = [
  { id: "1", name: "Magazzino 1", desc: "Elettrico, elettronica, interni", categories: ["Elettrico", "Interni", "Climatizzazione"], corsie: 6, scaffali: 8, ripiani: "ABCDE", contenitori: 4, perSlot: 2 },
  { id: "2", name: "Magazzino 2", desc: "Ottiche e specchietti", categories: ["Ottica", "Carrozzeria"], corsie: 5, scaffali: 8, ripiani: "ABCD", contenitori: 3, perSlot: 1 },
  { id: "3", name: "Magazzino 3", desc: "Meccanica: freni, sospensioni, ruote, raffreddamento", categories: ["Freni", "Sospensioni", "Ruote", "Raffreddamento"], corsie: 8, scaffali: 10, ripiani: "ABCDE", contenitori: 3, perSlot: 2 },
  { id: "4", name: "Magazzino 4", desc: "Motori e cambi su pallet", categories: ["Motore", "Trasmissione"], corsie: 3, scaffali: 6, ripiani: "AB", contenitori: 0, perSlot: 1 },
  { id: "P", name: "Piazzale coperto", desc: "Lamierati: porte, cofani, paraurti", categories: ["Lamierati"], corsie: 4, scaffali: 10, ripiani: "AB", contenitori: 0, perSlot: 3 },
];

export const corsiaId = (n: number) => `T${String(n).padStart(2, "0")}`;
export const scaffaleId = (n: number) => String(100 + n);

export function warehouseFor(category: string, shippable: boolean): Warehouse {
  if (category === "Carrozzeria" && !shippable) return WAREHOUSES[4];
  return WAREHOUSES.find((w) => w.categories.includes(category)) ?? WAREHOUSES[2];
}

export const whById = (id: string) => WAREHOUSES.find((w) => w.id === id);

export function locToString(l?: Location) {
  if (!l) return "—";
  return `${l.mag}/${l.corsia}-${l.scaffale}-${l.ripiano}${l.contenitore ? `-${l.contenitore}` : ""}`;
}

export function locLong(l?: Location) {
  if (!l) return "Posizione da assegnare";
  return `Mag/Corsia ${l.mag}/${l.corsia} · Scaffale ${l.scaffale} · Ripiano ${l.ripiano}${l.contenitore ? ` · Contenitore ${l.contenitore}` : ""}`;
}

export const sameShelf = (l: Location | undefined, mag: string, corsia: string, scaffale: string) =>
  !!l && l.mag === mag && l.corsia === corsia && l.scaffale === scaffale;

export function slotCapacity(w: Warehouse) {
  return w.ripiani.length * Math.max(w.contenitori, 1) * w.perSlot;
}

// Prima posizione con spazio nel magazzino indicato (le parti fisiche presenti occupano spazio).
export function firstFreeSlot(w: Warehouse, parts: Part[]): Location | undefined {
  const occupied = new Map<string, number>();
  for (const p of parts) {
    if (!p.location || p.status === "venduto" || p.status === "scartato") continue;
    const k = locToString(p.location);
    occupied.set(k, (occupied.get(k) ?? 0) + 1);
  }
  for (let c = 1; c <= w.corsie; c++)
    for (let s = 1; s <= w.scaffali; s++)
      for (const r of w.ripiani)
        for (let b = 1; b <= Math.max(w.contenitori, 1); b++) {
          const loc: Location = { mag: w.id, corsia: corsiaId(c), scaffale: scaffaleId(s), ripiano: r, contenitore: w.contenitori ? String(b) : undefined };
          if ((occupied.get(locToString(loc)) ?? 0) < w.perSlot) return loc;
        }
  return undefined;
}
