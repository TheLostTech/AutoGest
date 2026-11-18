// Costruzione di un annuncio a partire dai suoi pezzi: usata dallo store e dai dati demo.
import { CONDITIONS, typeById } from "./catalog";
import { groupKey, negozioStato, nextToShip, partsOf } from "./annunci";
import { aspectsFor, generateText, gpsrFor } from "./annuncio-testo";
import { isShippable } from "./spedizione";
import type { Annuncio, Gpsr, Part, Vehicle } from "./types";

/** Testo dal primo pezzo (tipo, lato, veicolo d'origine, codice); difetti e km da `pick`, il pezzo che parte. */
function textOf(first: Part, pick: Part, vehicles: Vehicle[], spedibile: boolean, quanti: number) {
  const t = typeById(first.typeId);
  const v = vehicles.find((x) => x.id === first.vehicleId);
  const vp = vehicles.find((x) => x.id === pick.vehicleId);
  return generateText({
    tipo: t.name,
    lato: first.side,
    marca: v?.make,
    modello: v?.model,
    versione: v?.version,
    anno: v?.year,
    oem: first.oem,
    condizione: CONDITIONS[first.condition].label,
    spiegazione: CONDITIONS[first.condition].hint,
    difetti: pick.defects,
    km: pick.km ?? vp?.km,
    spedibile,
    quanti: Math.max(1, quanti),
  });
}

/** Annuncio sul negozio per i pezzi dati: prezzo, testo, caratteristiche e GPSR vengono dal primo pezzo. */
export function buildAnnuncio(seed: Part[], vehicles: Vehicle[], id: string, at: string): Annuncio {
  const p = seed[0];
  const t = typeById(p.typeId);
  const v = vehicles.find((x) => x.id === p.vehicleId);
  const spedibile = isShippable(p, t.shippable);
  const quanti = seed.filter((x) => x.status === "disponibile").length;
  const { titolo, descrizione } = textOf(p, p, vehicles, spedibile, quanti);
  const a: Annuncio = {
    id,
    chiave: groupKey(p, spedibile),
    typeId: p.typeId,
    side: p.side,
    condition: p.condition,
    oem: p.oem,
    spedibile,
    price: p.price ?? 0,
    titolo,
    descrizione,
    testoModificato: false,
    caratteristiche: aspectsFor({ marca: v?.make, oem: p.oem, lato: p.side, tipo: t.name }),
    gpsr: gpsrFor(v?.year, v?.make),
    negozio: { stato: "online" },
    createdAt: at,
  };
  return { ...a, negozio: { stato: negozioStato(a, quanti) ?? "online" }, ...(quanti === 0 ? { esauritoDa: at } : {}) };
}

/**
 * Testo riscritto in automatico: dal primo pezzo dell'annuncio (il più vecchio, anche se venduto);
 * difetti e km del pezzo che parte per primo. Senza pezzi resta il testo di prima.
 */
export function textFor(a: Annuncio, parts: Part[], vehicles: Vehicle[], quanti: number) {
  const mine = partsOf(a, parts).sort((x, y) => x.createdAt.localeCompare(y.createdAt) || x.id.localeCompare(y.id));
  const first = mine[0];
  if (!first) return undefined;
  const pick = nextToShip(a, parts)[0] ?? first;
  // I dati comuni (lato, condizione, codice) sono quelli dell'annuncio
  const base: Part = { ...first, typeId: a.typeId, side: a.side, condition: a.condition, oem: a.oem };
  return textOf(base, pick, vehicles, a.spedibile, quanti);
}

/**
 * GPSR ricalcolato dal veicolo d'origine del primo pezzo, quando quel veicolo è `vehicleId`
 * (il GPSR viene dal primo pezzo, come il testo). Altrimenti undefined: resta quello di prima.
 */
export function gpsrOf(a: Annuncio, parts: Part[], vehicles: Vehicle[], vehicleId: string): Gpsr | undefined {
  const first = partsOf(a, parts).sort((x, y) => x.createdAt.localeCompare(y.createdAt) || x.id.localeCompare(y.id))[0];
  if (!first || first.vehicleId !== vehicleId) return undefined;
  const v = vehicles.find((x) => x.id === vehicleId);
  return gpsrFor(v?.year, v?.make);
}

/** Campi dell'annuncio che dipendono dal pezzo, per un annuncio con un pezzo solo che cambia dati. */
export function fieldsFromPart(p: Part, vehicles: Vehicle[]): Pick<Annuncio, "chiave" | "typeId" | "side" | "condition" | "oem" | "spedibile" | "caratteristiche"> {
  const t = typeById(p.typeId);
  const v = vehicles.find((x) => x.id === p.vehicleId);
  const spedibile = isShippable(p, t.shippable);
  return {
    chiave: groupKey(p, spedibile),
    typeId: p.typeId,
    side: p.side,
    condition: p.condition,
    oem: p.oem,
    spedibile,
    caratteristiche: aspectsFor({ marca: v?.make, oem: p.oem, lato: p.side, tipo: t.name }),
  };
}

export interface BozzaAnnuncio {
  titolo: string;
  descrizione: string;
  testoModificato: boolean;
  caratteristiche: Record<string, string>;
  gpsr: Gpsr;
  /** GPSR confermato dall'operatore nell'anteprima */
  gpsrManuale?: boolean;
  /** Numero della categoria eBay scritto dall'operatore; vuoto = la sceglie eBay */
  categoriaEbay?: string;
  canali: { negozio: boolean; ebay: boolean };
}

/** Anteprima di serie per pubblicare un pezzo: testo generato, solo sul negozio. */
export function bozzaFor(p: Part, vehicles: Vehicle[]): BozzaAnnuncio {
  const a = buildAnnuncio([{ ...p, status: "disponibile" }], vehicles, "", "");
  return {
    titolo: a.titolo,
    descrizione: a.descrizione,
    testoModificato: false,
    caratteristiche: a.caratteristiche,
    gpsr: a.gpsr,
    canali: { negozio: true, ebay: false },
  };
}
