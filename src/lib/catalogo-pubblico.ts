// Catalogo del negozio pubblico: la parte dell'archivio che un visitatore senza accesso può vedere. Modulo puro.
// Si costruiscono oggetti nuovi con i soli campi che il negozio e la pagina eBay simulato leggono: mai uno spread di un record intero,
// così un campo interno aggiunto domani (prezzi d'acquisto, note, dati di chi ha portato il veicolo) non esce per errore.
import type { Annuncio, Part, Vehicle } from "./types";

export type AnnuncioPubblico = Pick<Annuncio, "id" | "typeId" | "side" | "condition" | "oem" | "spedibile" | "price" | "titolo" | "descrizione" | "negozio" | "createdAt" | "esauritoDa"> & {
  ebay?: { stato: NonNullable<Annuncio["ebay"]>["stato"]; quantitaInviata?: number; prezzoInviato?: number };
};
export type PezzoPubblico = Pick<Part, "id" | "vehicleId" | "typeId" | "condition" | "status" | "side" | "oem" | "oemVerified" | "manufacturer" | "compat" | "km" | "defects" | "photos" | "annuncioId" | "createdAt"> & {
  pastDossier?: { model?: string };
};
export type VeicoloPubblico = Pick<Vehicle, "id" | "make" | "model" | "version" | "platform" | "year">;
export interface CatalogoPubblico {
  annunci: AnnuncioPubblico[];
  parts: PezzoPubblico[];
  vehicles: VeicoloPubblico[];
}
type Origine = { annunci?: Annuncio[]; parts?: Part[]; vehicles?: Vehicle[] };

const inCatalogo = (a: Annuncio) => a.negozio?.stato === "online" || a.negozio?.stato === "esaurito" || !!a.ebay;

function annuncioPubblico(a: Annuncio): AnnuncioPubblico {
  return {
    id: a.id,
    typeId: a.typeId,
    side: a.side,
    condition: a.condition,
    oem: a.oem,
    spedibile: a.spedibile,
    price: a.price,
    titolo: a.titolo,
    descrizione: a.descrizione,
    negozio: a.negozio ? { stato: a.negozio.stato } : undefined,
    ebay: a.ebay ? { stato: a.ebay.stato, quantitaInviata: a.ebay.quantitaInviata, prezzoInviato: a.ebay.prezzoInviato } : undefined,
    createdAt: a.createdAt,
    esauritoDa: a.esauritoDa,
  };
}

function pezzoPubblico(p: Part): PezzoPubblico {
  return {
    id: p.id,
    vehicleId: p.vehicleId,
    typeId: p.typeId,
    condition: p.condition,
    status: p.status,
    side: p.side,
    oem: p.oem,
    oemVerified: p.oemVerified,
    manufacturer: p.manufacturer,
    compat: p.compat ? { platforms: [...p.compat.platforms], source: p.compat.source, verified: p.compat.verified } : undefined,
    km: p.km,
    defects: p.defects,
    photos: [...p.photos],
    annuncioId: p.annuncioId,
    createdAt: p.createdAt,
    // Solo il modello della pratica passata: né numero, né targa, né telaio
    pastDossier: p.pastDossier?.model ? { model: p.pastDossier.model } : undefined,
  };
}

function veicoloPubblico(v: Vehicle): VeicoloPubblico {
  return { id: v.id, make: v.make, model: v.model, version: v.version, platform: v.platform, year: v.year };
}

export function catalogoPubblico(st: Origine): CatalogoPubblico {
  const annunci = (st.annunci ?? []).filter(inCatalogo);
  const ids = new Set(annunci.map((a) => a.id));
  const parts = (st.parts ?? []).filter((p) => p.annuncioId && ids.has(p.annuncioId));
  const veicoli = new Set(parts.map((p) => p.vehicleId));
  return {
    annunci: annunci.map(annuncioPubblico),
    parts: parts.map(pezzoPubblico),
    vehicles: (st.vehicles ?? []).filter((v) => veicoli.has(v.id)).map(veicoloPubblico),
  };
}

/** Vera se il file è tra le foto di un pezzo che `catalogoPubblico` restituisce (le foto sono indirizzi /api/foto/<nome>). */
export function fotoPubblica(st: Origine, nomeFile: string): boolean {
  if (!nomeFile || nomeFile.includes("/") || nomeFile.includes("\\")) return false;
  return catalogoPubblico(st).parts.some((p) => p.photos.some((src) => src === `/api/foto/${nomeFile}`));
}
