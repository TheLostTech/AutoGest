export type Role =
  | "accettazione"
  | "smontatore"
  | "magazziniere"
  | "responsabile"
  | "vendite"
  | "consulente"; // consulente ambientale esterna: solo registro rifiuti e formulari

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
  weightKg?: number; // peso alla pesa all'ingresso (obbligatoria: All. I p. 2.1 f-bis D.Lgs. 209/2003)
  massaLibretto?: number; // massa in ordine di marcia da libretto (campo G), dai dati della targa
  bonifica?: Bonifica;
  // Pratica: conferimento → documenti → visura → presa in carico → radiazione
  conferente?: { tipo: ConferenteTipo; nome: string; cf?: string; documento?: string }; // cf = codice fiscale o partita IVA
  documenti?: string[]; // chiavi dei documenti ricevuti (vedi pratica.ts)
  // Esito della visura: con Openapi lo registra l'ufficio leggendo il PDF (pdf = indirizzo del file sul server)
  visura?: { at: string; fermo: boolean; intestatario: string; pdf?: string; fonte?: "simulata" | "openapi" };
  // Visura chiesta a Openapi e non ancora registrata: il PDF arriva entro 24 ore lavorative
  visuraRichiesta?: { id: string; at: string; stato: string; modo: string; pdf?: string };
  presaInCarico?: { at: string; by: string };
  radiazione?: {
    stato: "da richiedere" | "richiesta" | "da integrare" | "completata";
    codice?: "C05332" | "C05333";
    canale?: "rvfu" | "agenzia";
    fascicolo?: string[]; // voci del fascicolo digitale inviate (vedi FASCICOLO in pratica.ts)
    richiestaAt?: string;
    integrazione?: { at: string; nota: string }; // il PRA chiede di integrare (preavviso di ricusazione)
    completataAt?: string; // data della radiazione, dalla ricevuta del PRA
    estremi?: string; // numero della ricevuta di avvenuta radiazione
    ricevuta?: string; // indirizzo del PDF della ricevuta sul server
  };
  // Distruzione di targhe e documenti, da annotare nel RVFU (non prima di 120 giorni dal CRD)
  distruzione?: { at: string; by: string; cosa: string[] };
}

export type ConferenteTipo = "privato" | "concessionaria" | "assicurazione" | "ente";

// ——— Ambiente: bonifica, registro di carico e scarico, formulari ———

export interface BonificaItem {
  key: string; // voce del modello di bonifica (vedi ambiente.ts)
  qty: number; // nella sua unità (l, kg, pz)
  done: boolean;
  kgPerUnit?: number; // stima per modello fissata al momento della bonifica
}

export interface Bonifica {
  at: string;
  by: string;
  items: BonificaItem[];
  residualKg: number; // carcassa bonificata che resta in piazzale
  semplice?: boolean; // segnata come fatta senza il modulo Ambiente: nessun materiale, nessun movimento nel registro
}

// Causali del registro per un impianto (manuale RENTRI §3.3): *T carico ricevuto da terzi, NP carico nuovo
// produttore (rifiuti nati dal trattamento), I scarico interno, aT scarico a terzi. RETT e ANN sono le
// registrazioni di rettifica e annullamento: una registrazione numerata non si modifica mai.
export type Causale = "*T" | "NP" | "I" | "aT" | "RETT" | "ANN" | "DIFF"; // DIFF: differenza tra giacenza stimata e pesata all'uscita
export type StatoFisico = "S" | "SP" | "L" | "FP" | "VS";

export interface WasteMove {
  id: string; // M-000001: identificativo interno
  at: string; // data dell'operazione (ingresso, bonifica, ritiro)
  kind: "carico" | "scarico";
  eer: string; // codice rifiuto
  kg: number;
  origin: string; // veicolo o formulario che ha generato il movimento
  note?: string;
  rentri: "da trasmettere" | "trasmesso";
  rentriAt?: string;
  rentriRicevuta?: string;
  // Registrazione: senza numero è una bozza (manca un dato obbligatorio); col numero non si modifica più
  numero?: number; // progressivo nell'anno
  registeredAt?: string;
  by?: string;
  causale?: Causale;
  statoFisico?: StatoFisico;
  hp?: string[]; // classi di pericolo
  operazione?: string; // attività a destinazione, es. R13
  vfu?: boolean; // veicolo fuori uso (impianti del D.Lgs. 209/2003)
  certificato?: { numero: string; data: string }; // certificato di rottamazione (RVFU)
  produttore?: { nome: string; cf?: string };
  pesoPesa?: boolean; // peso rilevato con la pesa dell'impianto
  kgLibretto?: number; // massa da libretto, per confronto con la pesa
  stimato?: boolean; // peso stimato per modello (bonifica): il vero arriva con la pesata all'uscita
  verificato?: { at: string; by: string }; // avviso controllato dalla consulente (non cambia i dati registrati)
  caricoRif?: string; // scarico interno: id del carico a cui si riferisce
  fir?: string; // id del formulario
  rettificaDi?: string;
  annullaDi?: string;
  motivo?: string;
}

export type RuoloSoggetto = "impianto" | "destinatario" | "trasportatore" | "intermediario";

// Anagrafica dei soggetti dei formulari: si compila una volta
export interface Soggetto {
  id: string;
  ruolo: RuoloSoggetto;
  nome: string;
  cf: string;
  sede?: string;
  autorizzazione?: string;
  albo?: string; // iscrizione all'Albo gestori ambientali
  operazione?: string; // per i destinatari, es. R13
}

export type FirStatus = "da firmare" | "firmato" | "accettato"; // la trasmissione al RENTRI la fa chi emette il formulario

// Formulario ricevuto: lo emette e lo vidima la ditta che ritira, l'impianto lo firma
export interface Fir {
  id: string;
  at: string;
  eer: string;
  kg: number;
  destinatario?: string;
  trasportatore?: string;
  status: FirStatus;
  history: { at: string; status: FirStatus; by: string }[];
  numero?: string; // es. "JNMPC 00262 JC"
  emessoAt?: string;
  destinatarioId?: string;
  trasportatoreId?: string;
  intermediarioId?: string;
  targa?: string;
  conducente?: string;
  inizioTrasportoAt?: string;
  rinfusa?: boolean;
  svuota?: boolean; // il carico è tutta la giacenza di quel codice: la pesata corregge le stime
  foto?: string[]; // foto della copia del formulario lasciata da chi ritira
  annotazioni?: string;
  esito?: "accettato" | "parziale" | "respinto";
  kgAccettati?: number;
  arrivoAt?: string;
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

// Annunci: una pagina in vendita può raggruppare più pezzi identici
export type StatoNegozio = "online" | "esaurito" | "ritirato";
export type StatoEbay =
  | "non pubblicato"
  | "in pubblicazione"
  | "online"
  | "esaurito"
  | "chiuso da eBay"
  | "ritirato"
  | "errore";
export interface VeicoloCompat {
  marca: string;
  modello: string;
  anno?: number;
  anni?: string;
  motore?: string;
}
export interface Produttore {
  ragioneSociale: string;
  indirizzo: string;
  citta: string;
  cap: string;
  paese: string;
  email?: string;
  sito?: string;
}
export type Gpsr =
  | { tipo: "esente" }
  | { tipo: "produttore"; produttore: Produttore }
  | { tipo: "da confermare" };
export interface AnnuncioEbay {
  stato: StatoEbay;
  daRiallineare: boolean;
  listingId?: string;
  url?: string;
  /** Categoria eBay: scelta da eBay alla prima pubblicazione, oppure scritta dall'operatore (manuale) */
  categoria?: { id: string; nome?: string; manuale?: boolean };
  quantitaInviata?: number;
  prezzoInviato?: number;
  errore?: string;
  avvisi?: string[];
  aggiornatoAt?: string;
}
export interface Annuncio {
  id: string; // A-000001
  chiave?: string;
  typeId: string;
  side?: string;
  condition: Condition;
  oem?: string;
  spedibile: boolean;
  price: number; // prezzo base dell'autodemolizione
  titolo: string;
  descrizione: string;
  testoModificato: boolean;
  caratteristiche: Record<string, string>;
  gpsr: Gpsr;
  /** GPSR confermato a mano dall'operatore: non si ricalcola quando cambiano marca o anno del veicolo */
  gpsrManuale?: boolean;
  negozio?: { stato: StatoNegozio };
  ebay?: AnnuncioEbay;
  createdAt: string;
  esauritoDa?: string;
}

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
  vehicleId: string; // "" per i pezzi trovati in inventario senza veicolo d'origine documentato
  origin?: "smontaggio" | "inventario";
  // Provenienza da una pratica di demolizione passata (es. dal vecchio Excel), quando il veicolo non è nel gestionale
  pastDossier?: { number: string; plate?: string; vin?: string; model?: string };
  missingSince?: string; // non trovato al suo posto durante l'ultima conta
  typeId: string;
  misura?: string; // per i tipi con misure (es. "M8 × 1,25 × 30 mm", "205/55 R16")
  description: string;
  condition: Condition;
  status: PartStatus;
  side?: string;
  oem?: string;
  oemVerified: boolean;
  spedibile?: boolean; // solo per i tipi non spedibili di serie: scelto alla creazione
  manufacturer?: string; // costruttore / fornitore primo impianto
  compat?: Compatibility;
  legacyCode?: string; // codice del gestionale precedente (magazzino migrato)
  km?: number;
  defects?: string;
  notes?: string;
  price?: number;
  location?: Location;
  // Scartato: tolto dallo scaffale e messo nell'area rottami, in attesa del ritiro a peso
  scrap?: ScrapInfo;
  photos: string[];
  aiSuggested?: { typeId: string; confidence: number; accepted: boolean };
  labelPrints: number;
  annuncioId?: string; // annuncio a cui appartiene il pezzo (A-000001)
  createdAt: string;
  createdBy: string;
}

export interface ScrapInfo {
  at: string;
  reason: string;
  from?: string; // ubicazione da cui è stato tolto
  pickup?: ScrapPickup; // ritiro a peso: stesso numero per tutti i pezzi ritirati insieme
}

export interface ScrapPickup {
  id: string; // RT-0001
  at: string;
  buyer: string;
  kg: number; // peso del carico intero (pesa o bolla del ritiro)
  eurPerKg: number;
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
  delivery?: "corriere" | "ritiro"; // per gli ordini online
  prices?: Record<string, number>; // prezzo applicato per pezzo (listino), ripreso dai documenti
  partIds: string[];
  amount: number;
  status: OrderStatus;
  customer: string;
  paymentRef?: string;
  ebayOrderId?: string; // ordine arrivato da eBay (canale "marketplace")
  tokenNegozio?: string; // ordine del negozio pubblico: chi lo ha fatto lo mostra per pagare (16 byte casuali, in esadecimale)
  daGestire?: string; // es. "mancano 2 pezzi": venduti su eBay ma non più disponibili
  createdAt: string;
  history: { at: string; status: OrderStatus; note?: string }[];
}

export interface AuditEvent {
  id: string;
  at: string;
  user: string;
  role: Role | "sistema" | "cliente";
  device: string;
  entity: "veicolo" | "ricambio" | "annuncio" | "ordine" | "regola" | "sistema";
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
  misure?: string[]; // bulloneria, fusibili, gomme…: un solo tipo, la misura si sceglie quando si cataloga
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
  status: "emesso" | "aperto" | "convertito" | "annullato" | "inviata allo SdI";
}

// ——— Inventario: conta di un ripiano ———

export interface InventoryCount {
  id: string; // I-000001
  at: string;
  by: string;
  mag: string;
  corsia: string;
  scaffale: string;
  ripiano: string;
  found: string[]; // ricambi già registrati e trovati al loro posto
  missing: string[]; // registrati qui ma non trovati
  added: string[]; // catalogati durante la conta
}
