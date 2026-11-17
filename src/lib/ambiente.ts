// Ambiente: codici rifiuto, modello di bonifica, limiti dell'autorizzazione e giacenze.
// Codici EER, quantità tipiche e limiti sono DIMOSTRATIVI: vanno configurati per impianto
// e validati con il consulente ambientale prima dell'uso reale.
import type { BonificaItem, StatoFisico, Vehicle, WasteMove } from "./types";
import { monthKey, monthStock } from "./periodo";
import { stimaComponenti, type Voce } from "./stime";

export interface Eer {
  code: string;
  label: string;
  short: string; // nome breve per liste e grafici
  limitKg: number; // stoccaggio massimo da autorizzazione (demo)
  destinatario: string; // destinatario abituale
  stato: StatoFisico; // stato fisico per il registro
  hp: string[]; // classi di pericolo (dimostrative tranne 16 01 04*: da confermare con la consulente)
}

export const EER: Eer[] = [
  { code: "16 01 04*", label: "Veicoli fuori uso", short: "Veicoli da bonificare", limitKg: 30000, destinatario: "—", stato: "S", hp: ["HP14"] },
  { code: "16 01 06", label: "Veicoli fuori uso privi di liquidi e componenti pericolose", short: "Carcasse bonificate", limitKg: 6000, destinatario: "Frantumazione Demo Srl" , stato: "S", hp: [] },
  { code: "13 07 01*", label: "Olio combustibile e carburante diesel", short: "Gasolio", limitKg: 600, destinatario: "Recupero Oli Demo" , stato: "L", hp: [] },
  { code: "13 07 02*", label: "Benzina", short: "Benzina", limitKg: 600, destinatario: "Recupero Oli Demo" , stato: "L", hp: [] },
  { code: "13 02 08*", label: "Altri oli per motori, ingranaggi e lubrificazione", short: "Oli motore e cambio", limitKg: 1500, destinatario: "Recupero Oli Demo" , stato: "L", hp: [] },
  { code: "16 01 13*", label: "Liquidi per freni", short: "Liquido freni", limitKg: 200, destinatario: "Smaltimenti Speciali Demo" , stato: "L", hp: [] },
  { code: "16 01 14*", label: "Liquidi antigelo contenenti sostanze pericolose", short: "Antigelo", limitKg: 500, destinatario: "Smaltimenti Speciali Demo" , stato: "L", hp: [] },
  { code: "14 06 01*", label: "Clorofluorocarburi, HCFC, HFC", short: "Gas climatizzatore", limitKg: 60, destinatario: "Smaltimenti Speciali Demo" , stato: "L", hp: [] },
  { code: "16 06 01*", label: "Batterie al piombo", short: "Batterie", limitKg: 3000, destinatario: "Raccolta Batterie Demo" , stato: "S", hp: [] },
  { code: "16 01 07*", label: "Filtri dell'olio", short: "Filtri olio", limitKg: 200, destinatario: "Smaltimenti Speciali Demo" , stato: "S", hp: [] },
  { code: "16 01 10*", label: "Componenti esplosivi (es. air bag)", short: "Airbag", limitKg: 150, destinatario: "Smaltimenti Speciali Demo" , stato: "S", hp: [] },
  { code: "16 08 01", label: "Catalizzatori esauriti contenenti metalli preziosi", short: "Catalizzatori", limitKg: 300, destinatario: "Recupero Catalizzatori Demo" , stato: "S", hp: [] },
  { code: "16 01 03", label: "Pneumatici fuori uso", short: "Pneumatici", limitKg: 2000, destinatario: "Recupero Pneumatici Demo" , stato: "S", hp: [] },
];

export const eerByCode = (code: string) => EER.find((e) => e.code === code);

export const TRASPORTATORI = ["Trasporti Demo Snc", "Autotrasporti Esempio Srl", "Mezzo proprio dell'impianto"];
export const DESTINATARI = [...new Set(EER.map((e) => e.destinatario).filter((d) => d !== "—"))];

export interface BonificaVoice {
  key: string;
  label: string;
  unit: "l" | "kg" | "pz";
  kgPerUnit: number; // per riportare tutto in kg nel registro
  eer: (v: Vehicle) => string;
  typical: (v: Vehicle) => number;
}

// Modello di bonifica: l'ordine è quello in cui si lavora sul ponte
export const BONIFICA: BonificaVoice[] = [
  { key: "batteria", label: "Batteria", unit: "pz", kgPerUnit: 14, eer: () => "16 06 01*", typical: () => 1 },
  { key: "carburante", label: "Carburante", unit: "l", kgPerUnit: 0.8, eer: (v) => (v.fuel === "Diesel" ? "13 07 01*" : "13 07 02*"), typical: () => 6 },
  { key: "oli", label: "Oli motore e cambio", unit: "l", kgPerUnit: 0.9, eer: () => "13 02 08*", typical: () => 5 },
  { key: "freni", label: "Liquido freni", unit: "l", kgPerUnit: 1, eer: () => "16 01 13*", typical: () => 0.5 },
  { key: "antigelo", label: "Antigelo", unit: "l", kgPerUnit: 1.05, eer: () => "16 01 14*", typical: () => 5 },
  { key: "gas", label: "Gas del climatizzatore", unit: "kg", kgPerUnit: 1, eer: () => "14 06 01*", typical: () => 0.5 },
  { key: "filtro", label: "Filtro dell'olio", unit: "pz", kgPerUnit: 0.4, eer: () => "16 01 07*", typical: () => 1 },
  { key: "airbag", label: "Airbag", unit: "pz", kgPerUnit: 1, eer: () => "16 01 10*", typical: (v) => (v.year >= 2008 ? 4 : 2) },
  { key: "catalizzatore", label: "Catalizzatore", unit: "pz", kgPerUnit: 5, eer: () => "16 08 01", typical: () => 1 },
  { key: "pneumatici", label: "Pneumatici", unit: "pz", kgPerUnit: 8, eer: () => "16 01 03", typical: () => 4 },
];

export const voiceByKey = (k: string) => BONIFICA.find((b) => b.key === k)!;

// Quantità e pesi stimati per questo modello (massa da libretto, alimentazione, anno): nessuno li scrive a mano
export const profiloOf = (v: Vehicle) => ({ massaKg: v.massaLibretto ?? v.weightKg ?? 1000, fuel: v.fuel, year: v.year });
export const typicalBonifica = (v: Vehicle): BonificaItem[] => {
  const st = stimaComponenti(profiloOf(v));
  return BONIFICA.map((b) => {
    const e = st[b.key as Voce];
    return { key: b.key, qty: e?.qty ?? b.typical(v), done: true, kgPerUnit: e?.kgPerUnit ?? b.kgPerUnit };
  });
};

export const itemKg = (it: BonificaItem) => (it.done ? Math.round(it.qty * (it.kgPerUnit ?? voiceByKey(it.key).kgPerUnit) * 10) / 10 : 0);

export const fmtKg = (kg: number) => `${kg.toLocaleString("it-IT", { maximumFractionDigits: kg < 10 ? 1 : 0 })} kg`;

// Registrazioni generate da un evento operativo: è qui che "il registro si scrive da solo".
// Causali RENTRI per un impianto: *T ricevuto da terzi, NP nuovo produttore, I scarico interno.
const fromEer = (eer: string) => {
  const e = eerByCode(eer);
  return { statoFisico: e?.stato ?? ("S" as const), hp: e?.hp ?? [] };
};

// Ingresso del veicolo: carico "ricevuto da terzi" con spunta veicoli fuori uso e certificato di rottamazione.
// Il peso va confermato con la pesa: finché manca (o manca il codice fiscale o il certificato) resta in bozza.
// Il peso è quello della pesa; finché manca si propone la massa del libretto e la registrazione resta in bozza
export function movesForIntake(v: Vehicle, at: string): Omit<WasteMove, "id">[] {
  return [
    {
      at,
      kind: "carico",
      eer: "16 01 04*",
      kg: v.weightKg ?? v.massaLibretto ?? 0,
      origin: v.id,
      note: `Ingresso ${v.plate}`,
      rentri: "da trasmettere",
      causale: "*T",
      vfu: true,
      operazione: "R13",
      ...fromEer("16 01 04*"),
      produttore: v.conferente ? { nome: v.conferente.nome, cf: v.conferente.cf } : undefined,
      certificato: v.dossier.number && v.presaInCarico ? { numero: v.dossier.number, data: v.presaInCarico.at } : undefined,
      pesoPesa: !!v.weightKg,
      kgLibretto: v.massaLibretto,
    },
  ];
}

// Bonifica: il veicolo esce dal carico (scarico interno che richiama il carico d'ingresso) e nascono i rifiuti
// tolti e la carcassa bonificata (carichi "nuovo produttore")
export function movesForBonifica(v: Vehicle, items: BonificaItem[], at: string, caricoRif?: string): { moves: Omit<WasteMove, "id">[]; residualKg: number } {
  const weight = v.weightKg ?? 0;
  const removed = items.filter((i) => i.done && i.qty > 0);
  const removedKg = removed.reduce((a, i) => a + itemKg(i), 0);
  const residualKg = Math.max(0, Math.round(weight - removedKg));
  // Pesi stimati per modello: la pesata del contenitore all'uscita li riporta al vero
  const np = (eer: string, kg: number, note: string): Omit<WasteMove, "id"> => ({ at, kind: "carico", eer, kg, origin: v.id, note, rentri: "da trasmettere", causale: "NP", operazione: "R13", stimato: true, ...fromEer(eer) });
  const moves: Omit<WasteMove, "id">[] = [
    { at, kind: "scarico", eer: "16 01 04*", kg: weight, origin: v.id, note: "Avviato a bonifica", rentri: "da trasmettere", causale: "I", caricoRif, ...fromEer("16 01 04*") },
    ...removed.map((i) => np(voiceByKey(i.key).eer(v), itemKg(i), `Bonifica: ${voiceByKey(i.key).label.toLowerCase()}`)),
    np("16 01 06", residualKg, "Carcassa bonificata"),
  ];
  return { moves, residualKg };
}

// Giacenza attuale per codice: solo registrazioni numerate, con rettifiche e annullamenti applicati
export function stockByEer(moves: WasteMove[]) {
  const rows = monthStock(moves, monthKey(new Date().toISOString()), EER.map((e) => ({ code: e.code, limitKg: e.limitKg })));
  return EER.map((e, i) => ({ ...e, kg: Math.max(0, rows[i].giacenza), pct: Math.max(0, rows[i].giacenza) / e.limitKg }));
}

