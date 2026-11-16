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
