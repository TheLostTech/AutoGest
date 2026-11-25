// Ambiente: codici rifiuto, modello di bonifica, limiti dell'autorizzazione e giacenze.
// Limiti, destinatari e quantità tipiche sono DIMOSTRATIVI: vanno configurati per impianto e validati con il
// consulente ambientale prima dell'uso reale.
// Codici e campi verificati il 25/11/2026 su: elenco europeo dei rifiuti (Decisione 2000/532/CE), MUD 2026
// (DPCM 30/01/2026, Allegato 3, Scheda AUT), specifiche API RENTRI dati-registri e formulari, DD MASE 251/2023.
// Le classi di pericolo (HP) le attribuisce il produttore del rifiuto: quelle qui sotto sono PROPOSTE da far
// confermare alla consulente. Nel formulario sono obbligatorie per ogni codice pericoloso (con l'asterisco).
import type { BonificaItem, Provenienza, StatoFisico, Vehicle, WasteMove } from "./types";
import { monthKey, monthStock } from "./periodo";
import { stimaComponenti, type Voce } from "./stime";

export interface Eer {
  code: string;
  label: string;
  short: string; // nome breve per liste e grafici
  limitKg: number; // stoccaggio massimo da autorizzazione (demo)
  destinatario: string; // destinatario abituale
  stato: StatoFisico; // stato fisico per il registro
  hp: string[]; // classi di pericolo proposte (da confermare con la consulente); vuote se non note
  dal?: string; // codice valido da questa data (AAAA-MM-GG)
  al?: string; // codice valido fino a questa data compresa
}

// Dal 9/12/2026 cambia il sottocapitolo 16 06 delle batterie (Decisione delegata UE 2025/934, rettifica del
// 19/08/2025): nasce 16 06 07* per le batterie al litio e sparisce 16 06 05. RENTRI aggiorna i codici il 3/12/2026.
export const NUOVI_CODICI_BATTERIE = "2026-12-09";

export const EER: Eer[] = [
  { code: "16 01 04*", label: "Veicoli fuori uso", short: "Veicoli da bonificare", limitKg: 30000, destinatario: "—", stato: "S", hp: ["HP14"] },
  { code: "16 01 06", label: "Veicoli fuori uso privi di liquidi e componenti pericolose", short: "Carcasse bonificate", limitKg: 6000, destinatario: "Frantumazione Demo Srl", stato: "S", hp: [] },
  { code: "13 07 01*", label: "Olio combustibile e carburante diesel", short: "Gasolio", limitKg: 600, destinatario: "Recupero Oli Demo", stato: "L", hp: ["HP03", "HP07", "HP14"] },
  // 13 07 02* non è tra i codici stampati nella Scheda AUT del MUD 2026 (che ha 13 07 01 e 13 07 03): da chiarire con la consulente
  { code: "13 07 02*", label: "Benzina", short: "Benzina", limitKg: 600, destinatario: "Recupero Oli Demo", stato: "L", hp: ["HP03", "HP05", "HP07", "HP11", "HP14"] },
  { code: "13 07 03*", label: "Altri carburanti (comprese le miscele)", short: "Altri carburanti", limitKg: 300, destinatario: "Recupero Oli Demo", stato: "L", hp: [] },
  { code: "13 02 08*", label: "Altri oli per motori, ingranaggi e lubrificazione", short: "Oli motore e cambio", limitKg: 1500, destinatario: "Recupero Oli Demo", stato: "L", hp: ["HP07", "HP14"] },
  { code: "16 01 13*", label: "Liquidi per freni", short: "Liquido freni", limitKg: 200, destinatario: "Smaltimenti Speciali Demo", stato: "L", hp: ["HP06", "HP10"] },
  { code: "16 01 14*", label: "Liquidi antigelo contenenti sostanze pericolose", short: "Antigelo", limitKg: 500, destinatario: "Smaltimenti Speciali Demo", stato: "L", hp: ["HP05", "HP06"] },
  { code: "16 01 15", label: "Liquidi antigelo diversi da quelli di cui alla voce 16 01 14", short: "Antigelo non pericoloso", limitKg: 300, destinatario: "Smaltimenti Speciali Demo", stato: "L", hp: [] },
  { code: "14 06 01*", label: "Clorofluorocarburi, HCFC, HFC", short: "Gas climatizzatore", limitKg: 60, destinatario: "Smaltimenti Speciali Demo", stato: "L", hp: [] },
  { code: "16 06 01*", label: "Batterie al piombo-acido", short: "Batterie", limitKg: 3000, destinatario: "Raccolta Batterie Demo", stato: "S", hp: ["HP08", "HP10", "HP14"] },
  { code: "16 06 05", label: "Altre batterie e accumulatori", short: "Batterie di trazione", limitKg: 2000, destinatario: "Raccolta Batterie Demo", stato: "S", hp: [], al: "2026-12-08" },
  { code: "16 06 07*", label: "Rifiuti di batterie al litio", short: "Batterie al litio", limitKg: 2000, destinatario: "Raccolta Batterie Demo", stato: "S", hp: [], dal: NUOVI_CODICI_BATTERIE },
  { code: "16 01 07*", label: "Filtri dell'olio", short: "Filtri olio", limitKg: 200, destinatario: "Smaltimenti Speciali Demo", stato: "S", hp: ["HP07", "HP14"] },
  { code: "16 01 08*", label: "Componenti contenenti mercurio", short: "Componenti con mercurio", limitKg: 20, destinatario: "Smaltimenti Speciali Demo", stato: "S", hp: [] },
  { code: "16 01 09*", label: "Componenti contenenti PCB", short: "Componenti con PCB", limitKg: 20, destinatario: "Smaltimenti Speciali Demo", stato: "S", hp: [] },
  { code: "16 01 10*", label: "Componenti esplosivi (es. air bag)", short: "Airbag", limitKg: 150, destinatario: "Smaltimenti Speciali Demo", stato: "S", hp: ["HP01"] },
  { code: "16 01 11*", label: "Pastiglie per freni, contenenti amianto", short: "Pastiglie con amianto", limitKg: 50, destinatario: "Smaltimenti Speciali Demo", stato: "S", hp: [] },
  { code: "16 01 12", label: "Pastiglie per freni, diverse da quelle di cui alla voce 16 01 11", short: "Pastiglie freni", limitKg: 300, destinatario: "Recupero Metalli Demo", stato: "S", hp: [] },
  { code: "16 01 16", label: "Serbatoi per gas liquido", short: "Serbatoi del gas", limitKg: 1500, destinatario: "Recupero Metalli Demo", stato: "S", hp: [] },
  { code: "16 01 17", label: "Metalli ferrosi", short: "Ferro", limitKg: 10000, destinatario: "Recupero Metalli Demo", stato: "S", hp: [] },
  { code: "16 01 18", label: "Metalli non ferrosi", short: "Metalli non ferrosi", limitKg: 3000, destinatario: "Recupero Metalli Demo", stato: "S", hp: [] },
  { code: "16 01 19", label: "Plastica", short: "Plastica", limitKg: 3000, destinatario: "Recupero Plastica Demo", stato: "S", hp: [] },
  { code: "16 01 20", label: "Vetro", short: "Vetro", limitKg: 3000, destinatario: "Recupero Vetro Demo", stato: "S", hp: [] },
  { code: "16 01 21*", label: "Componenti pericolosi diversi da quelli di cui alle voci da 16 01 07 a 16 01 11 e 16 01 13 e 16 01 14", short: "Componenti pericolosi", limitKg: 200, destinatario: "Smaltimenti Speciali Demo", stato: "S", hp: [] },
  { code: "16 01 22", label: "Componenti non specificati altrimenti", short: "Altri componenti", limitKg: 2000, destinatario: "Recupero Metalli Demo", stato: "S", hp: [] },
  { code: "16 08 01", label: "Catalizzatori esauriti contenenti oro, argento, renio, rodio, palladio, iridio o platino (tranne 16 08 07)", short: "Catalizzatori", limitKg: 300, destinatario: "Recupero Catalizzatori Demo", stato: "S", hp: [] },
  { code: "16 08 07*", label: "Catalizzatori esauriti contaminati da sostanze pericolose", short: "Catalizzatori contaminati", limitKg: 100, destinatario: "Recupero Catalizzatori Demo", stato: "S", hp: [] },
  { code: "16 01 03", label: "Pneumatici fuori uso", short: "Pneumatici", limitKg: 2000, destinatario: "Recupero Pneumatici Demo", stato: "S", hp: [] },
];

// Rifiuto pericoloso: codice con l'asterisco
export const pericoloso = (code: string) => code.trim().endsWith("*");

// Codice valido alla data (AAAA-MM-GG o ISO)
export const eerValido = (e: Eer, at: string) => {
  const d = at.slice(0, 10);
  return (!e.dal || d >= e.dal) && (!e.al || d <= e.al);
};

// Batteria di trazione (auto elettriche e ibride): prima del 9/12/2026 «altre batterie», dopo «batterie al litio»
export const eerBatteriaTrazione = (at: string) => (at.slice(0, 10) >= NUOVI_CODICI_BATTERIE ? "16 06 07*" : "16 06 05");

export const eerByCode = (code: string) => EER.find((e) => e.code === code);

export const TRASPORTATORI = ["Trasporti Demo Snc", "Autotrasporti Esempio Srl", "Mezzo proprio dell'impianto"];
export const DESTINATARI = [...new Set(EER.map((e) => e.destinatario).filter((d) => d !== "—"))];

export interface BonificaVoice {
  key: string;
  label: string;
  unit: "l" | "kg" | "pz";
  kgPerUnit: number; // per riportare tutto in kg nel registro
  eer: (v: Vehicle, at: string) => string; // il codice può dipendere dalla data (batterie dal 9/12/2026)
  typical: (v: Vehicle) => number;
  applica?: (v: Vehicle) => boolean; // voce solo per alcuni veicoli (es. serbatoio del gas)
}

const aGas = (v: Vehicle) => v.fuel === "GPL" || v.fuel === "Metano";
const aTrazione = (v: Vehicle) => v.fuel === "Elettrica" || v.fuel === "Ibrida";

// Modello di bonifica: l'ordine è quello in cui si lavora sul ponte. Messa in sicurezza dell'Allegato I, punto 5,
// del D.Lgs. 209/2003: accumulatori, serbatoi di gas, airbag, carburante, oli, antigelo, liquido freni, gas del
// climatizzatore, filtro dell'olio (più catalizzatore e pneumatici del punto 7).
export const BONIFICA: BonificaVoice[] = [
  { key: "batteria", label: "Batteria", unit: "pz", kgPerUnit: 14, eer: () => "16 06 01*", typical: () => 1 },
  // Ibride con batteria al nichel-metallo idruro: dal 9/12/2026 il codice è 16 06 08*, da scegliere con la consulente
  { key: "trazione", label: "Batteria di trazione", unit: "kg", kgPerUnit: 1, eer: (_v, at) => eerBatteriaTrazione(at), typical: (v) => (v.fuel === "Elettrica" ? 300 : 40), applica: aTrazione },
  // Serbatoio del GPL o del metano: 16 01 16 «serbatoi per gas liquido», da confermare per il metano compresso
  { key: "serbatoio-gas", label: "Serbatoio del gas", unit: "pz", kgPerUnit: 30, eer: () => "16 01 16", typical: () => 1, applica: aGas },
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

// Voci della bonifica che valgono per questo veicolo
export const vociBonifica = (v: Vehicle) => BONIFICA.filter((b) => !b.applica || b.applica(v));

// Quantità e pesi stimati per questo modello (massa da libretto, alimentazione, anno): nessuno li scrive a mano
export const profiloOf = (v: Vehicle) => ({ massaKg: v.massaLibretto ?? v.weightKg ?? 1000, fuel: v.fuel, year: v.year });
export const typicalBonifica = (v: Vehicle): BonificaItem[] => {
  const st = stimaComponenti(profiloOf(v));
  return vociBonifica(v).map((b) => {
    const e = st[b.key as Voce];
    return { key: b.key, qty: e?.qty ?? b.typical(v), done: true, kgPerUnit: e?.kgPerUnit ?? b.kgPerUnit };
  });
};

export const itemKg = (it: BonificaItem) => (it.done ? Math.round(it.qty * (it.kgPerUnit ?? voiceByKey(it.key).kgPerUnit) * 10) / 10 : 0);

export const fmtKg = (kg: number) => `${kg.toLocaleString("it-IT", { maximumFractionDigits: kg < 10 ? 1 : 0 })} kg`;

// Registrazioni generate da un evento operativo: è qui che "il registro si scrive da solo".
// Causali RENTRI per un impianto: T* ricevuto da terzi, NP nuovo produttore, I scarico interno, aT scarico a terzi.
// Dati del rifiuto che si ricavano dal codice. Provenienza: in un impianto di veicoli fuori uso è sempre
// S, rifiuto speciale (DD MASE 251/2023, Tabella 8, punto 15 «i veicoli fuori uso»).
export const PROVENIENZA_IMPIANTO: Provenienza = "S";
export const datiRifiuto = (eer: string) => {
  const e = eerByCode(eer);
  return { statoFisico: e?.stato ?? ("S" as const), hp: e?.hp ?? [], provenienza: PROVENIENZA_IMPIANTO };
};
const fromEer = datiRifiuto;

// Dati del rifiuto di una registrazione, completati con quelli del codice dove mancano (per le rettifiche)
export function datiCompleti(m: Pick<WasteMove, "eer" | "statoFisico" | "hp" | "provenienza">) {
  const d = datiRifiuto(m.eer);
  return { statoFisico: m.statoFisico ?? d.statoFisico, hp: m.hp?.length ? m.hp : d.hp, provenienza: m.provenienza ?? d.provenienza };
}

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
      causale: "T*",
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
    ...removed.map((i) => np(voiceByKey(i.key).eer(v, at), itemKg(i), `Bonifica: ${voiceByKey(i.key).label.toLowerCase()}`)),
    np("16 01 06", residualKg, "Carcassa bonificata"),
  ];
  return { moves, residualKg };
}

// Giacenza attuale per codice: solo registrazioni numerate, con rettifiche e annullamenti applicati
export function stockByEer(moves: WasteMove[]) {
  const rows = monthStock(moves, monthKey(new Date().toISOString()), EER.map((e) => ({ code: e.code, limitKg: e.limitKg })));
  return EER.map((e, i) => ({ ...e, kg: Math.max(0, rows[i].giacenza), pct: Math.max(0, rows[i].giacenza) / e.limitKg }));
}

