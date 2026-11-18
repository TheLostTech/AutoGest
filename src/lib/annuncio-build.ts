// Costruzione di un annuncio a partire dai suoi pezzi: usata dallo store e dai dati demo.
import { CONDITIONS, typeById } from "./catalog";
import { groupKey, negozioStato } from "./annunci";
import { aspectsFor, generateText, gpsrFor } from "./annuncio-testo";
import { isShippable } from "./spedizione";
import type { Annuncio, Part, Vehicle } from "./types";

/** Annuncio sul negozio per i pezzi dati: prezzo, testo, caratteristiche e GPSR vengono dal primo pezzo. */
export function buildAnnuncio(seed: Part[], vehicles: Vehicle[], id: string, at: string): Annuncio {
  const p = seed[0];
  const t = typeById(p.typeId);
  const v = vehicles.find((x) => x.id === p.vehicleId);
  const spedibile = isShippable(p, t.shippable);
  const quanti = seed.filter((x) => x.status === "disponibile").length;
  const { titolo, descrizione } = generateText({
    tipo: t.name,
    lato: p.side,
    marca: v?.make,
    modello: v?.model,
    versione: v?.version,
    anno: v?.year,
    oem: p.oem,
    condizione: CONDITIONS[p.condition].label,
    spiegazione: CONDITIONS[p.condition].hint,
    difetti: p.defects,
    km: p.km ?? v?.km,
    spedibile,
    quanti: Math.max(1, quanti),
  });
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
  return { ...a, negozio: { stato: negozioStato(a, quanti) ?? "online" } };
}
