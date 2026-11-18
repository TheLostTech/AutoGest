// Testo dell'annuncio scritto in automatico. Modulo puro: solo import type.
import type { Gpsr, Part, Produttore, Vehicle, VeicoloCompat } from "./types";

const MAX_TITOLO = 80;

// Tabella marca -> produttore per il GPSR. Le voci devono venire solo dai siti
// ufficiali delle case (ragione sociale e indirizzo legale nell'UE): mai
// inventate. Finché non è verificata, le marche danno "da confermare".
export const PRODUTTORI: Record<string, Produttore> = {};

// Parole per cercare la categoria eBay di ogni tipo di pezzo.
export const EBAY_CATEGORY_QUERY: Record<string, string> = {
  motore: "motore completo auto",
  cambio: "cambio manuale auto",
  alternatore: "alternatore auto",
  motorino: "motorino avviamento auto",
  centralina: "centralina motore auto",
  batteria: "batteria auto",
  faro: "faro anteriore auto",
  fanale: "fanale posteriore auto",
  specchietto: "specchietto retrovisore auto",
  porta: "porta auto",
  cofano: "cofano anteriore auto",
  paraurti: "paraurti anteriore auto",
  cerchio: "cerchio in lega auto",
  disco: "disco freno anteriore auto",
  ammortizzatore: "ammortizzatore anteriore auto",
  radiatore: "radiatore auto",
  compressore: "compressore aria condizionata auto",
  quadro: "quadro strumenti auto",
};

interface TitleInput {
  tipo: string;
  lato?: string;
  marca?: string;
  modello?: string;
  versione?: string;
  anni?: string;
  oem?: string;
}

function join(parts: (string | undefined)[]): string {
  return parts.filter((p) => p && p.trim()).join(" ");
}

function compose(t: TitleInput): string {
  return join([t.tipo, t.lato, t.marca, t.modello, t.versione, t.anni, t.oem ? `OE ${t.oem}` : "", "usato"]);
}

// Tronca a parola intera, entro `max` caratteri; "" se non entra nemmeno una parola.
function cutWords(s: string, max: number): string {
  if (s.length <= max) return s;
  const cut = s.slice(0, Math.max(0, max));
  const i = cut.lastIndexOf(" ");
  return i > 0 ? cut.slice(0, i) : "";
}

export function buildTitle(t: TitleInput): string {
  let cur: TitleInput = { ...t };
  let s = compose(cur);
  if (s.length <= MAX_TITOLO) return s;
  cur = { ...cur, versione: undefined };
  s = compose(cur);
  if (s.length <= MAX_TITOLO) return s;
  cur = { ...cur, anni: undefined };
  s = compose(cur);
  if (s.length <= MAX_TITOLO) return s;
  if (cur.modello) {
    const spazio = MAX_TITOLO - compose({ ...cur, modello: undefined }).length - 1;
    cur = { ...cur, modello: cutWords(cur.modello, spazio) };
    s = compose(cur);
    if (s.length <= MAX_TITOLO) return s;
  }
  // Ultima risorsa: accorcia il tipo di pezzo, tenendo codice e "usato".
  const coda = join([cur.oem ? `OE ${cur.oem}` : "", "usato"]);
  const testa = join([cur.tipo, cur.lato, cur.marca]);
  const ok = cutWords(testa, MAX_TITOLO - coda.length - 1);
  return join([ok, coda]).slice(0, MAX_TITOLO);
}

function migliaia(n: number): string {
  return Math.round(n)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

export function buildDescription(d: {
  condizione: string;
  spiegazione: string;
  difetti?: string;
  km?: number;
  veicolo?: string;
  oem?: string;
  spedibile: boolean;
  quanti: number;
}): string {
  const multi = d.quanti > 1;
  const righe: string[] = [];
  righe.push(`Condizione: ${d.condizione}. ${d.spiegazione}`.trim());
  if (!multi) {
    if (d.difetti && d.difetti.trim()) righe.push(`Difetti: ${d.difetti.trim()}`);
    if (d.km !== undefined) righe.push(`Chilometri del veicolo d'origine: ${migliaia(d.km)} km`);
  }
  if (d.veicolo) righe.push(`Veicolo d'origine: ${d.veicolo}`);
  if (d.oem) righe.push(`Codice originale: ${d.oem}`);
  righe.push("Pezzo controllato e catalogato con codice univoco");
  if (multi) righe.push(`Disponibili ${d.quanti} pezzi uguali: le foto mostrano il pezzo che riceverai`);
  righe.push(d.spedibile ? "Spedizione con corriere" : "Solo ritiro in sede");
  return righe.join("\n");
}

export function compatVehicles(
  parts: Part[],
  vehicles: Vehicle[],
  platforms: { id: string; make: string; model: string; years: string }[],
): VeicoloCompat[] {
  const out: VeicoloCompat[] = [];
  const seen = new Set<string>();
  const add = (v: VeicoloCompat) => {
    const k = JSON.stringify([v.marca, v.modello, v.anno ?? null, v.anni ?? null, v.motore ?? null]);
    if (seen.has(k)) return;
    seen.add(k);
    out.push(v);
  };
  for (const p of parts) {
    const veh = vehicles.find((v) => v.id === p.vehicleId);
    if (veh) add({ marca: veh.make, modello: veh.model, anno: veh.year, motore: veh.version });
  }
  for (const p of parts) {
    if (!p.compat?.verified) continue;
    for (const id of p.compat.platforms) {
      const pl = platforms.find((x) => x.id === id);
      if (pl) add({ marca: pl.make, modello: pl.model, anni: pl.years });
    }
  }
  return out;
}

export function aspectsFor(d: {
  marca?: string;
  oem?: string;
  lato?: string;
  tipo: string;
}): Record<string, string> {
  const r: Record<string, string> = { Tipo: d.tipo };
  if (d.marca) r["Marca"] = d.marca;
  if (d.oem) r["Numero ricambio produttore"] = d.oem;
  if (d.lato) r["Posizionamento sul veicolo"] = d.lato;
  return r;
}

export function gpsrFor(anno: number | undefined, marca: string | undefined): Gpsr {
  if (anno === undefined || anno === 2024) return { tipo: "da confermare" };
  if (anno < 2024) return { tipo: "esente" };
  const produttore = marca ? PRODUTTORI[marca] : undefined;
  return produttore ? { tipo: "produttore", produttore } : { tipo: "da confermare" };
}

export function generateText(input: {
  tipo: string;
  lato?: string;
  marca?: string;
  modello?: string;
  versione?: string;
  anno?: number;
  oem?: string;
  condizione: string;
  spiegazione: string;
  difetti?: string;
  km?: number;
  spedibile: boolean;
  quanti: number;
}): { titolo: string; descrizione: string } {
  const titolo = buildTitle({
    tipo: input.tipo,
    lato: input.lato,
    marca: input.marca,
    modello: input.modello,
    versione: input.versione,
    anni: input.anno !== undefined ? String(input.anno) : undefined,
    oem: input.oem,
  });
  const veicolo = join([input.marca, input.modello, input.versione, input.anno !== undefined ? String(input.anno) : ""]);
  const descrizione = buildDescription({
    condizione: input.condizione,
    spiegazione: input.spiegazione,
    difetti: input.difetti,
    km: input.km,
    veicolo: veicolo || undefined,
    oem: input.oem,
    spedibile: input.spedibile,
    quanti: input.quanti,
  });
  return { titolo, descrizione };
}
