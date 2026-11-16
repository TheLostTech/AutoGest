// Servizi esterni SIMULATI. In produzione: OCR targhe, banca dati veicoli/VIN, IA riconoscimento.
// Ogni risposta va confermata dall'operatore.

export interface VehicleLookup {
  make: string;
  model: string;
  version: string;
  platform: string;
  year: number;
  fuel: string;
  vin: string;
  color: string;
}

const DB: Record<string, VehicleLookup> = {
  GB512XR: { make: "Fiat", model: "Panda", version: "1.2 69 CV Easy", platform: "fiat-panda-319", year: 2015, fuel: "Benzina", vin: "ZFA31200003G51284", color: "Grigio" },
  FK208MS: { make: "Volkswagen", model: "Golf VI", version: "1.4 TSI 122 CV", platform: "vw-golf-6", year: 2012, fuel: "Benzina", vin: "WVWZZZ1KZCW208519", color: "Bianco" },
  EZ913AL: { make: "Lancia", model: "Ypsilon", version: "1.3 Multijet 95 CV", platform: "lancia-ypsilon-846", year: 2013, fuel: "Diesel", vin: "ZLA84600001E91377", color: "Nero" },
  DY640CB: { make: "Ford", model: "Fiesta", version: "1.4 TDCi 70 CV", platform: "ford-fiesta-7", year: 2010, fuel: "Diesel", vin: "WF0DXXGAKDAY64021", color: "Rosso" },
  FA377TP: { make: "Alfa Romeo", model: "Giulietta", version: "1.4 T-Jet 120 CV", platform: "alfa-giulietta-940", year: 2014, fuel: "Benzina", vin: "ZAR94000007F37744", color: "Bianco" },
};

export const OCR_SAMPLES = Object.keys(DB);

export interface OcrResult {
  plate: string;
  confidence: number;
  uncertain: number[]; // indici dei caratteri incerti
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function simulateOcr(seed: number): Promise<OcrResult> {
  await sleep(1400);
  const plate = OCR_SAMPLES[seed % OCR_SAMPLES.length];
  // un carattere ambiguo per mostrare la verifica manuale
  const uncertain = seed % 2 === 0 ? [3] : [2, 6];
  return { plate, confidence: seed % 2 === 0 ? 0.91 : 0.74, uncertain };
}

export async function lookupPlate(plate: string, fail: boolean): Promise<VehicleLookup | null> {
  await sleep(900);
  if (fail) throw new Error("Banca dati veicoli non raggiungibile (timeout). Prosegui a mano: il veicolo resterà «da verificare».");
  return DB[plate.toUpperCase()] ?? null;
}

// Suggerimento IA del componente da foto: SIMULATO, restituisce una proposta con confidenza.
export async function suggestComponent(hintTypeId: string | undefined, candidates: string[]): Promise<{ typeId: string; confidence: number }> {
  await sleep(1100);
  if (hintTypeId) return { typeId: hintTypeId, confidence: 0.82 };
  const pick = candidates[Math.floor(Math.random() * candidates.length)];
  return { typeId: pick, confidence: 0.58 };
}

export const PLATE_RE = /^[A-Z]{2}\d{3}[A-Z]{2}$/;
export const VIN_RE = /^[A-HJ-NPR-Z0-9]{17}$/;

export async function compressImage(file: File, max = 1000): Promise<string> {
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise<HTMLImageElement>((res, rej) => {
      const i = new Image();
      i.onload = () => res(i);
      i.onerror = rej;
      i.src = url;
    });
    const scale = Math.min(1, max / Math.max(img.width, img.height));
    const c = document.createElement("canvas");
    c.width = Math.round(img.width * scale);
    c.height = Math.round(img.height * scale);
    c.getContext("2d")!.drawImage(img, 0, 0, c.width, c.height);
    return c.toDataURL("image/jpeg", 0.72);
  } finally {
    URL.revokeObjectURL(url);
  }
}
