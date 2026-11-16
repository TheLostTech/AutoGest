// Ambiente: codici rifiuto, modello di bonifica, limiti dell'autorizzazione e giacenze.
// Codici EER, quantità tipiche e limiti sono DIMOSTRATIVI: vanno configurati per impianto
// e validati con il consulente ambientale prima dell'uso reale.
import type { BonificaItem, FirStatus, Vehicle, WasteMove } from "./types";

export interface Eer {
  code: string;
  label: string;
  short: string; // nome breve per liste e grafici
  limitKg: number; // stoccaggio massimo da autorizzazione (demo)
  destinatario: string; // destinatario abituale
}

export const EER: Eer[] = [
  { code: "16 01 04*", label: "Veicoli fuori uso", short: "Veicoli da bonificare", limitKg: 30000, destinatario: "—" },
  { code: "16 01 06", label: "Veicoli fuori uso privi di liquidi e componenti pericolose", short: "Carcasse bonificate", limitKg: 6000, destinatario: "Frantumazione Demo Srl" },
  { code: "13 07 01*", label: "Olio combustibile e carburante diesel", short: "Gasolio", limitKg: 600, destinatario: "Recupero Oli Demo" },
  { code: "13 07 02*", label: "Benzina", short: "Benzina", limitKg: 600, destinatario: "Recupero Oli Demo" },
  { code: "13 02 08*", label: "Altri oli per motori, ingranaggi e lubrificazione", short: "Oli motore e cambio", limitKg: 1500, destinatario: "Recupero Oli Demo" },
  { code: "16 01 13*", label: "Liquidi per freni", short: "Liquido freni", limitKg: 200, destinatario: "Smaltimenti Speciali Demo" },
  { code: "16 01 14*", label: "Liquidi antigelo contenenti sostanze pericolose", short: "Antigelo", limitKg: 500, destinatario: "Smaltimenti Speciali Demo" },
  { code: "14 06 01*", label: "Clorofluorocarburi, HCFC, HFC", short: "Gas climatizzatore", limitKg: 60, destinatario: "Smaltimenti Speciali Demo" },
  { code: "16 06 01*", label: "Batterie al piombo", short: "Batterie", limitKg: 3000, destinatario: "Raccolta Batterie Demo" },
  { code: "16 01 07*", label: "Filtri dell'olio", short: "Filtri olio", limitKg: 200, destinatario: "Smaltimenti Speciali Demo" },
  { code: "16 01 10*", label: "Componenti esplosivi (es. air bag)", short: "Airbag", limitKg: 150, destinatario: "Smaltimenti Speciali Demo" },
  { code: "16 08 01", label: "Catalizzatori esauriti contenenti metalli preziosi", short: "Catalizzatori", limitKg: 300, destinatario: "Recupero Catalizzatori Demo" },
  { code: "16 01 03", label: "Pneumatici fuori uso", short: "Pneumatici", limitKg: 2000, destinatario: "Recupero Pneumatici Demo" },
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

export const typicalBonifica = (v: Vehicle): BonificaItem[] => BONIFICA.map((b) => ({ key: b.key, qty: b.typical(v), done: true }));

export const itemKg = (it: BonificaItem) => (it.done ? Math.round(it.qty * voiceByKey(it.key).kgPerUnit * 10) / 10 : 0);

export const fmtKg = (kg: number) => `${kg.toLocaleString("it-IT", { maximumFractionDigits: kg < 10 ? 1 : 0 })} kg`;

// Movimenti generati da un evento operativo: è qui che "il registro si scrive da solo"
export function movesForIntake(v: Vehicle, at: string): Omit<WasteMove, "id">[] {
  if (!v.weightKg) return [];
  return [{ at, kind: "carico", eer: "16 01 04*", kg: v.weightKg, origin: v.id, note: `Ingresso ${v.plate}`, rentri: "da trasmettere" }];
}

export function movesForBonifica(v: Vehicle, items: BonificaItem[], at: string): { moves: Omit<WasteMove, "id">[]; residualKg: number } {
  const weight = v.weightKg ?? 0;
  const removed = items.filter((i) => i.done && i.qty > 0);
  const removedKg = removed.reduce((a, i) => a + itemKg(i), 0);
  const residualKg = Math.max(0, Math.round(weight - removedKg));
  const moves: Omit<WasteMove, "id">[] = [
    { at, kind: "scarico", eer: "16 01 04*", kg: weight, origin: v.id, note: "Avviato a bonifica", rentri: "da trasmettere" },
    ...removed.map((i) => ({ at, kind: "carico" as const, eer: voiceByKey(i.key).eer(v), kg: itemKg(i), origin: v.id, note: `Bonifica: ${voiceByKey(i.key).label.toLowerCase()}`, rentri: "da trasmettere" as const })),
    { at, kind: "carico", eer: "16 01 06", kg: residualKg, origin: v.id, note: "Carcassa bonificata", rentri: "da trasmettere" },
  ];
  return { moves, residualKg };
}

export function stockByEer(moves: WasteMove[]) {
  const m = new Map<string, number>();
  for (const x of moves) m.set(x.eer, (m.get(x.eer) ?? 0) + (x.kind === "carico" ? x.kg : -x.kg));
  return EER.map((e) => {
    const kg = Math.max(0, Math.round((m.get(e.code) ?? 0) * 10) / 10);
    return { ...e, kg, pct: kg / e.limitKg };
  });
}

export const FIR_NEXT: Partial<Record<FirStatus, { to: FirStatus; label: string }>> = {
  "da firmare": { to: "firmato", label: "Firma e consegna al trasportatore" },
  firmato: { to: "trasmesso", label: "Trasmetti al RENTRI" },
  trasmesso: { to: "accettato", label: "Registra accettazione del destinatario" },
};
