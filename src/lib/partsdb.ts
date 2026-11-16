import { platformById, typeById } from "./catalog";

// CATALOGO RICAMBI SIMULATO.
// In produzione: banca dati/catalogo licenziato (codici OE, costruttore, intercambiabilità).
// Qui le regole sono finte ma coerenti: pezzi dello stesso gruppo di intercambiabilità
// condividono lo stesso codice OEM e la stessa lista di veicoli compatibili.

export const CATALOG_SOURCE = "Catalogo ricambi (simulato)";

// Gruppi meccanici: stesso motore/gruppo → stesso alternatore, motorino, compressore…
const ENGINE_GROUPS: Record<string, string[]> = {
  "fire-1.2": ["fiat-panda-319", "lancia-ypsilon-846", "fiat-500-312", "ford-ka-2"],
  "mjet-1.3": ["fiat-punto-199", "fiat-grande-punto-199", "alfa-mito-955", "opel-corsa-d"],
  "pq35": ["vw-golf-6", "audi-a3-8p", "skoda-octavia-1z", "seat-leon-1p"],
  "ford-b": ["ford-fiesta-7", "mazda-2-de"],
  "psa-1.4hdi": ["peugeot-208", "citroen-c3-2"],
  "renault-b": ["renault-clio-3", "renault-modus"],
  "jtdm-1.6": ["alfa-giulietta-940", "fiat-bravo-198"],
  "toyota-1kr": ["toyota-yaris-2"],
};

// Carrozzeria: pochi gemelli reali (stessa scocca)
const BODY_GROUPS: string[][] = [
  ["fiat-punto-199", "fiat-grande-punto-199"],
  ["opel-corsa-d", "opel-adam"],
];

const MECH = new Set(["alternatore", "motorino", "compressore", "radiatore", "disco", "ammortizzatore", "batteria", "motore", "cambio", "centralina"]);
const BODY = new Set(["porta", "cofano", "specchietto", "paraurti"]);

const SUPPLIERS: Record<string, string[]> = {
  alternatore: ["Bosch", "Denso", "Valeo", "Magneti Marelli"],
  motorino: ["Bosch", "Denso", "Valeo"],
  centralina: ["Bosch", "Magneti Marelli", "Continental"],
  faro: ["Valeo", "Hella", "Automotive Lighting", "Magneti Marelli"],
  fanale: ["Valeo", "Hella", "Magneti Marelli"],
  compressore: ["Denso", "Sanden", "Delphi"],
  radiatore: ["Valeo", "Behr", "Denso"],
  ammortizzatore: ["Sachs", "Monroe", "KYB"],
  disco: ["Brembo", "ATE", "TRW"],
  quadro: ["Continental", "Magneti Marelli", "Visteon"],
  batteria: ["Varta", "Exide"],
};

function hash(s: string) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return h >>> 0;
}

function groupOf(typeId: string, platform: string): { key: string; platforms: string[] } {
  if (MECH.has(typeId)) {
    const g = Object.entries(ENGINE_GROUPS).find(([, ps]) => ps.includes(platform));
    if (g) return { key: `${typeId}:${g[0]}`, platforms: g[1] };
  }
  if (BODY.has(typeId)) {
    const g = BODY_GROUPS.find((ps) => ps.includes(platform));
    if (g) return { key: `${typeId}:${g.join("+")}`, platforms: g };
  }
  return { key: `${typeId}:${platform}`, platforms: [platform] };
}

function oemFormat(make: string, h: number, side?: string) {
  const d = (n: number) => String(h % 10 ** n).padStart(n, "0");
  const sfx = side?.includes("sx") ? "1" : side?.includes("dx") ? "2" : "";
  switch (make) {
    case "Fiat":
    case "Lancia":
    case "Alfa Romeo":
      return `5${d(7)}${sfx}`;
    case "Volkswagen":
      return `1K0 ${d(3)} ${String((h >>> 7) % 1000).padStart(3, "0")} ${"ABCDEF"[h % 6]}`;
    case "Ford":
      return `AM5T-${d(5)}-${"ABCDEF"[h % 6]}${"ABCDEF"[(h >>> 3) % 6]}`;
    case "Renault":
      return `8200${d(6)}`;
    case "Opel":
      return `13${d(6)}`;
    case "Toyota":
      return `${27000 + (h % 999)}-0D${d(3)}`;
    case "Peugeot":
      return `96${d(6)}80`;
    default:
      return `${d(8)}`;
  }
}

export interface CatalogInfo {
  oem: string;
  manufacturer: string;
  production: string;
  platforms: string[];
  note?: string;
  source: string;
}

export function catalogFor(typeId: string, platformId: string, side?: string): CatalogInfo | null {
  const plat = platformById(platformId);
  if (!plat) return null;
  const g = groupOf(typeId, platformId);
  const h = hash(g.key + (side ?? ""));
  const sup = SUPPLIERS[typeId];
  const t = typeById(typeId);
  const manufacturer = sup ? `${sup[h % sup.length]} (primo impianto ${plat.make})` : `${plat.make} originale`;
  return {
    oem: oemFormat(plat.make, h, side),
    manufacturer,
    production: plat.years.replace("–", " > "),
    platforms: g.platforms,
    note: g.platforms.length > 1 ? `${t.name} intercambiabile su ${g.platforms.length} modelli` : "Specifico del modello",
    source: CATALOG_SOURCE,
  };
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function lookupCatalog(typeId: string, platformId: string, side?: string) {
  await sleep(800);
  return catalogFor(typeId, platformId, side);
}

export const platformLabel = (id: string) => platformById(id)?.label ?? id;
