import type { Location, Part } from "./types";

// Struttura fisica del magazzino (demo). Formato come il gestionale attuale del cliente:
// Mag/Corsia 3/T03 · Scaffale 104 · Ripiano B · Contenitore 1
export interface Warehouse {
  id: string;
  name: string;
  desc: string;
  categories: string[];
  corsie: number;
  scaffali: number; // per corsia, numerati da primoScaffale (0 = struttura libera: la mappa nasce dalle ubicazioni scritte)
  primoScaffale?: number; // numero del primo scaffale; 101 se assente (formato del gestionale attuale)
  ripiani: string; // lettere dal basso
  contenitori: number; // 0 = ripiano libero (pezzi voluminosi)
  perSlot: number; // capienza indicativa per contenitore/ripiano
}

export const WAREHOUSES: Warehouse[] = [
  { id: "1", name: "Magazzino 1", desc: "Elettrico, elettronica, interni", categories: ["Elettrico", "Interni", "Climatizzazione"], corsie: 6, scaffali: 8, ripiani: "ABCDE", contenitori: 4, perSlot: 2 },
  { id: "2", name: "Magazzino 2", desc: "Ottiche e specchietti", categories: ["Ottica", "Carrozzeria"], corsie: 5, scaffali: 8, ripiani: "ABCD", contenitori: 3, perSlot: 1 },
  { id: "3", name: "Magazzino 3", desc: "Meccanica: freni, sospensioni, sterzo, ruote, raffreddamento, scarico", categories: ["Freni", "Sospensioni", "Sterzo", "Ruote", "Raffreddamento", "Scarico", "Alimentazione"], corsie: 8, scaffali: 10, ripiani: "ABCDE", contenitori: 3, perSlot: 2 },
  { id: "4", name: "Magazzino 4", desc: "Motori e cambi su pallet", categories: ["Motore", "Trasmissione"], corsie: 3, scaffali: 6, ripiani: "AB", contenitori: 0, perSlot: 1 },
  { id: "P", name: "Piazzale coperto", desc: "Lamierati: porte, cofani, paraurti", categories: ["Lamierati"], corsie: 4, scaffali: 10, ripiani: "AB", contenitori: 0, perSlot: 3 },
];

export const corsiaId = (n: number) => `T${String(n).padStart(2, "0")}`;
export const scaffaleId = (n: number, w?: Pick<Warehouse, "primoScaffale">) => String((w?.primoScaffale ?? 101) + n - 1);

// Ordine naturale: "4" prima di "101", "T2" prima di "T10"
export const natural = (a: string, b: string) => a.localeCompare(b, "it", { numeric: true, sensitivity: "base" });
const union = (declared: string[], used: (string | undefined)[]) =>
  [...new Set([...declared, ...used.filter((x): x is string => !!x)])].sort(natural);

const present = (p: Part) => !!p.location && p.status !== "venduto" && p.status !== "scartato";

// La mappa è fatta delle posizioni previste dal magazzino PIÙ quelle effettivamente scritte sui ricambi:
// nessun pezzo resta fuori dalla mappa perché la sua ubicazione non segue la numerazione prevista.
export function layoutOf(w: Warehouse, parts: Part[]) {
  const inside = parts.filter((p) => present(p) && p.location!.mag === w.id);
  return {
    inside,
    corsie: union(Array.from({ length: w.corsie }, (_, i) => corsiaId(i + 1)), inside.map((p) => p.location!.corsia)),
    scaffali: union(Array.from({ length: w.scaffali }, (_, i) => scaffaleId(i + 1, w)), inside.map((p) => p.location!.scaffale)),
    ripiani: (onShelf: Part[]) => union(w.ripiani.split(""), onShelf.map((p) => p.location!.ripiano)),
    contenitori: (onShelf: Part[]) =>
      union(Array.from({ length: w.contenitori }, (_, i) => String(i + 1)), onShelf.map((p) => p.location!.contenitore)),
  };
}

// I magazzini sono dati (creabili dall'Inventario): le funzioni ricevono l'elenco attuale
export function warehouseFor(category: string, shippable: boolean, list: Warehouse[] = WAREHOUSES): Warehouse {
  if (category === "Carrozzeria" && !shippable) return list.find((w) => w.id === "P") ?? list[0];
  return list.find((w) => w.categories.includes(category)) ?? list.find((w) => w.id === "3") ?? list[0];
}

export const whById = (id: string, list: Warehouse[] = WAREHOUSES) => list.find((w) => w.id === id);

export const sameRipiano = (l: Location | undefined, mag: string, corsia: string, scaffale: string, ripiano: string) =>
  sameShelf(l, mag, corsia, scaffale) && l!.ripiano === ripiano;

export const ripianiCount = (w: Warehouse) => w.corsie * w.scaffali * w.ripiani.length;

// Provenienza leggibile: veicolo nel gestionale, pratica passata (inventario) o non documentata
export const originLabel = (p: Pick<Part, "vehicleId" | "pastDossier">) =>
  p.vehicleId || (p.pastDossier ? `pratica ${p.pastDossier.number}` : "provenienza non documentata");

export function locToString(l?: Location) {
  if (!l) return "—";
  return `${l.mag}/${l.corsia}-${l.scaffale}-${l.ripiano}${l.contenitore ? `-${l.contenitore}` : ""}`;
}

export function locLong(l?: Location) {
  if (!l) return "Posizione da assegnare";
  return `Mag/Corsia ${l.mag}/${l.corsia} · Scaffale ${l.scaffale} · Ripiano ${l.ripiano}${l.contenitore ? ` · Contenitore ${l.contenitore}` : ""}`;
}

// Codice dell'etichetta scaffale: è la stessa scrittura dell'ubicazione (es. 1/T01-103-B, 1/T01-103-B-2).
// Il QR contiene l'indirizzo /u/<codice>: con la fotocamera del telefono apre la mappa su quello scaffale.
export const shelfCode = (l: Location) => locToString(l);
export const shelfPath = (l: Location) => `/u/${l.mag}/${[l.corsia, l.scaffale, l.ripiano, l.contenitore].filter(Boolean).join("-")}`;

// Riconosce un codice scaffale scritto, letto dal codice a barre o dal QR (indirizzo /u/…). Senza "/" non è uno scaffale.
export function splitShelfCode(raw: string): Location | undefined {
  let s = raw.trim().toUpperCase();
  const url = s.match(/\/U\/(.+?)(?:[?#].*)?$/);
  if (url) s = decodeURIComponent(url[1]);
  const slash = s.indexOf("/");
  if (slash < 1) return undefined;
  const mag = s.slice(0, slash).trim();
  const rest = s.slice(slash + 1).split(/[-/\s]+/).filter(Boolean);
  if (rest.length < 3 || rest.length > 4) return undefined;
  return normLoc(mag, rest[0], rest[1], rest[2], rest[3]);
}
export function parseShelf(raw: string, warehouses: Warehouse[]): Location | undefined {
  const l = splitShelfCode(raw);
  return l && warehouses.some((w) => w.id.toUpperCase() === l.mag) ? { ...l, mag: warehouses.find((w) => w.id.toUpperCase() === l.mag)!.id } : undefined;
}

// Il pezzo è su questo scaffale? Un'etichetta di ripiano vale per tutti i contenitori del ripiano.
export const onLabel = (pl: Location | undefined, label: Location) =>
  !!pl && pl.mag === label.mag && pl.corsia === label.corsia && pl.scaffale === label.scaffale && pl.ripiano === label.ripiano && (!label.contenitore || pl.contenitore === label.contenitore);

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
          const loc: Location = { mag: w.id, corsia: corsiaId(c), scaffale: scaffaleId(s, w), ripiano: r, contenitore: w.contenitori ? String(b) : undefined };
          if ((occupied.get(locToString(loc)) ?? 0) < w.perSlot) return loc;
        }
  return undefined;
}

// Ubicazione scritta a mano come la usate (es. corsia "3" o "T03", scaffale "04" o "104", ripiano "b", contenitore "1").
// I numeri perdono gli zeri iniziali, così "04" e "4" sono lo stesso scaffale.
const num0 = (x: string) => (/^\d+$/.test(x) ? String(Number(x)) : x);
export function normLoc(mag: string, corsia: string, scaffale: string, ripiano: string, contenitore?: string): Location {
  const c = corsia.trim().toUpperCase();
  const box = contenitore?.trim().toUpperCase();
  return {
    mag,
    corsia: /^\d+$/.test(c) ? corsiaId(Number(c)) : c,
    scaffale: num0(scaffale.trim().toUpperCase()),
    ripiano: num0(ripiano.trim().toUpperCase()),
    contenitore: box ? num0(box) : undefined,
  };
}
