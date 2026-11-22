import { defaultRule, NON_DA_RECUPERARE, PART_TYPES, typeById } from "./catalog";
import { isShippable } from "./spedizione";
import type { Order, Part, PartStatus, StockRule, Vehicle } from "./types";

export type StockLevel = "manca" | "sotto soglia" | "sufficiente" | "eccesso";

export interface RecoveryRow {
  typeId: string;
  name: string;
  category: string;
  disponibili: number;
  riservati: number;
  bozze: number;
  invendibili: number;
  fisici: number;
  min: number;
  max: number;
  level: StockLevel;
  daQuestoVeicolo: number;
  daAltriModelli: number;
  score: number;
}

const LEVEL_RANK: Record<StockLevel, number> = { manca: 0, "sotto soglia": 1, sufficiente: 2, eccesso: 3 };

// Confronta i ricambi recuperabili dal veicolo con le scorte reali compatibili.
// Prima versione: soglie min/max per tipologia.
// Un pezzo copre un veicolo se viene dalla stessa piattaforma oppure se la sua compatibilità
// verificata (catalogo + codice sul pezzo) include quella piattaforma.
export function fits(p: Part, originPlatform: string | undefined, platform: string) {
  // Un veicolo senza modello riconosciuto non è "compatibile" con gli altri veicoli sconosciuti
  if (!platform || platform === "sconosciuta") return false;
  return originPlatform === platform || (!!p.compat?.verified && p.compat.platforms.includes(platform));
}

export function recoveryList(vehicle: Vehicle, parts: Part[], vehicles: Vehicle[], rules: StockRule[]): RecoveryRow[] {
  const platformOf = new Map(vehicles.map((v) => [v.id, v.platform]));
  return PART_TYPES.filter((t) => !NON_DA_RECUPERARE.has(t.category)).map((t) => {
    const same = parts.filter((p) => p.typeId === t.id && fits(p, platformOf.get(p.vehicleId), vehicle.platform) && p.status !== "scartato" && p.status !== "venduto");
    const count = (s: PartStatus) => same.filter((p) => p.status === s).length;
    const rule = rules.find((r) => r.typeId === t.id) ?? defaultRule(t);
    const disponibili = count("disponibile");
    const bozze = count("bozza");
    const usable = disponibili + bozze;
    const level: StockLevel = usable === 0 && rule.min > 0 ? "manca" : usable < rule.min ? "sotto soglia" : usable >= rule.max ? "eccesso" : "sufficiente";
    const daQuestoVeicolo = parts.filter((p) => p.vehicleId === vehicle.id && p.typeId === t.id).length;
    return {
      typeId: t.id,
      name: t.name,
      category: t.category,
      disponibili,
      riservati: count("riservato"),
      bozze,
      invendibili: count("invendibile"),
      fisici: same.length,
      min: rule.min,
      max: rule.max,
      level,
      daQuestoVeicolo,
      score: LEVEL_RANK[level] * 10 - t.value,
      daAltriModelli: same.filter((p) => platformOf.get(p.vehicleId) !== vehicle.platform).length,
    };
  }).sort((a, b) => a.score - b.score);
}

export interface Check {
  label: string;
  ok: boolean;
  blocking: boolean;
  hint?: string;
}

// Un ricambio si pubblica solo quando i dati commerciali minimi sono completi e certi.
export function publishChecks(p: Part, v?: Vehicle): Check[] {
  const t = typeById(p.typeId);
  return [
    { label: "Almeno una fotografia", ok: p.photos.length > 0, blocking: true },
    { label: "Prezzo impostato", ok: typeof p.price === "number" && p.price > 0, blocking: true },
    { label: "Descrizione completa", ok: p.description.trim().length >= 12, blocking: true },
    { label: "Condizioni registrate", ok: !!p.condition, blocking: true },
    { label: "Ricambio disponibile in magazzino", ok: p.status === "disponibile", blocking: true, hint: `Stato attuale: ${p.status}` },
    { label: "Posizione di magazzino assegnata", ok: !!p.location, blocking: true },
    !p.vehicleId && p.pastDossier
      ? { label: `Provenienza: pratica di demolizione ${p.pastDossier.number}`, ok: true, blocking: false }
      : p.origin === "inventario" && !p.vehicleId
        ? { label: "Provenienza non documentata (magazzino preesistente)", ok: false, blocking: false, hint: "Indica la pratica di demolizione passata se è nel vecchio archivio" }
        : { label: "Provenienza veicolo verificata", ok: v?.verification === "verificato", blocking: true, hint: "Veicolo in stato «da verificare»" },
    { label: isShippable(p, t.shippable) ? "Spedibile con corriere" : "Solo ritiro in sede", ok: true, blocking: false },
    { label: p.compat?.verified ? `Compatibilità verificata su ${p.compat.platforms.length} modelli` : p.oem ? "Codice OEM non verificato: compatibilità non dichiarata" : "Nessun codice OEM: compatibilità non dichiarata", ok: !!p.compat?.verified, blocking: false },
  ];
}

export const euro = (n?: number) =>
  typeof n === "number"
    ? n.toLocaleString("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: Number.isInteger(n) ? 0 : 2, minimumFractionDigits: Number.isInteger(n) ? 0 : 2 })
    : "—";

export const dateIt = (iso: string, withTime = false) =>
  new Date(iso).toLocaleString("it-IT", withTime ? { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" } : { day: "2-digit", month: "short", year: "numeric" });

export const relDays = (iso: string) => {
  const d = Math.round((Date.now() - new Date(iso).getTime()) / 864e5);
  return d <= 0 ? "oggi" : d === 1 ? "ieri" : `${d} giorni fa`;
};

// Ordine ancora aperto che contiene il pezzo (da incassare o pagato, non ancora consegnato/spedito)
export const openOrderFor = (partId: string, orders: Order[]) =>
  orders.find((o) => o.partIds.includes(partId) && (o.status === "in attesa di pagamento" || o.status === "pagato"));
