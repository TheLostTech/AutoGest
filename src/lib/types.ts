export type Role =
  | "accettazione"
  | "smontatore"
  | "magazziniere"
  | "responsabile"
  | "vendite";

export type VehicleWork = "accettato" | "in smontaggio" | "smontato";
export type Verification = "verificato" | "da verificare";
export type DossierStatus = "da registrare" | "in corso" | "completata";

export interface Vehicle {
  id: string; // ID interno V-000000
  plate: string;
  vin: string;
  make: string;
  model: string;
  version: string;
  platform: string; // chiave compatibilità (demo)
  year: number;
  fuel: string;
  km?: number;
  color?: string;
  intakeAt: string;
  dossier: {
    number: string; // numero ufficiale pratica / certificato
    kind: string;
    status: DossierStatus;
  };
  verification: Verification;
  work: VehicleWork;
  photo?: string;
  notes?: string;
  createdBy: string;
  weightKg?: number; // peso in ingresso (bilancia o stima)
  bonifica?: Bonifica;
  // Pratica: conferimento → documenti → visura → presa in carico → radiazione
  conferente?: { tipo: ConferenteTipo; nome: string };
  documenti?: string[]; // chiavi dei documenti ricevuti (vedi pratica.ts)
  visura?: { at: string; fermo: boolean; intestatario: string };
  presaInCarico?: { at: string; by: string };
  radiazione?: { stato: "da richiedere" | "richiesta" | "completata"; richiestaAt?: string; completataAt?: string; estremi?: string };
}

export type ConferenteTipo = "privato" | "concessionaria" | "assicurazione" | "ente";

// ——— Ambiente: bonifica, registro di carico e scarico, formulari ———

export interface BonificaItem {
  key: string; // voce del modello di bonifica (vedi ambiente.ts)
  qty: number; // nella sua unità (l, kg, pz)
  done: boolean;
}

export interface Bonifica {
  at: string;
  by: string;
  items: BonificaItem[];
  residualKg: number; // carcassa bonificata che resta in piazzale
}

export interface WasteMove {
  id: string; // M-000001: numero progressivo del registro
  at: string;
  kind: "carico" | "scarico";
  eer: string; // codice rifiuto
  kg: number;
  origin: string; // veicolo o formulario che ha generato il movimento
  note?: string;
  rentri: "da trasmettere" | "trasmesso";
  rentriAt?: string;
}

export type FirStatus = "da firmare" | "firmato" | "trasmesso" | "accettato";

export interface Fir {
  id: string; // formulario di identificazione rifiuto
  at: string;
  eer: string;
  kg: number;
  destinatario: string;
  trasportatore: string;
  status: FirStatus;
  history: { at: string; status: FirStatus; by: string }[];
}

export type PartStatus =
  | "bozza"
  | "disponibile"
  | "riservato"
  | "venduto"
  | "invendibile"
  | "scartato";

export type Condition = "A" | "B" | "C" | "D";

export type ListingStatus = "non pubblicato" | "pubblicato" | "ritirato";

export interface Location {
  mag: string; // magazzino
  corsia: string; // T01…
  scaffale: string; // 101…
  ripiano: string; // A…
  contenitore?: string; // 1…
}

export interface Compatibility {
  platforms: string[]; // piattaforme su cui il pezzo è montabile
  source: string; // provenienza del dato
  verified: boolean; // confermato dall'operatore confrontando il codice sul pezzo
  checkedAt?: string;
}

export interface Part {
  id: string; // R-000000
  vehicleId: string;
  typeId: string;
  description: string;
  condition: Condition;
  status: PartStatus;
  side?: string;
  oem?: string;
  oemVerified: boolean;
  manufacturer?: string; // costruttore / fornitore primo impianto
  compat?: Compatibility;
  legacyCode?: string; // codice del gestionale precedente (magazzino migrato)
  km?: number;
  defects?: string;
  notes?: string;
  price?: number;
  location?: Location;
  photos: string[];
  aiSuggested?: { typeId: string; confidence: number; accepted: boolean };
  labelPrints: number;
  listing: ListingStatus;
  createdAt: string;
  createdBy: string;
}

export type Channel = "banco" | "negozio" | "marketplace";
export type OrderStatus =
  | "in attesa di pagamento"
  | "pagato"
  | "pagamento fallito"
  | "annullato"
  | "spedito"
  | "consegnato"
  | "reso";

export interface Order {
  id: string; // O-000000
  channel: Channel;
  partIds: string[];
  amount: number;
  status: OrderStatus;
  customer: string;
  paymentRef?: string;
  createdAt: string;
  history: { at: string; status: OrderStatus; note?: string }[];
}

export interface AuditEvent {
  id: string;
  at: string;
  user: string;
  role: Role | "sistema" | "cliente";
  device: string;
  entity: "veicolo" | "ricambio" | "ordine" | "regola" | "sistema";
  entityId: string;
  action: string;
  detail?: string;
}

export interface StockRule {
  typeId: string;
  min: number;
  max: number;
}

export interface PartType {
  id: string;
  name: string;
  category: string;
  sided: boolean;
  shippable: boolean;
  basePrice: number;
  render?: string;
  value: number; // peso commerciale 1-5 per ordinare i suggerimenti
}

// ——— Documenti di vendita ———

export type DocType = "preventivo" | "documento commerciale" | "fattura" | "nota di credito";

export interface SalesDoc {
  id: string; // numero del documento, es. FT-2026-0007
  type: DocType;
  at: string;
  customer: { name: string; taxId?: string }; // partita IVA o codice fiscale per la fattura
  lines: { partId?: string; description: string; price: number }[]; // prezzi IVA inclusa
  total: number;
  orderId?: string;
  refDocId?: string; // es. nota di credito → fattura
  listino?: string;
  status: "emesso" | "aperto" | "convertito" | "inviata allo SdI";
}
