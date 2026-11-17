import type { Condition, PartType } from "./types";

// Tassonomia demo. In produzione: categorie concordate col cliente.
export const PART_TYPES: PartType[] = [
  { id: "motore", name: "Motore completo", category: "Motore", sided: false, shippable: false, basePrice: 650, value: 5 },
  { id: "cambio", name: "Cambio manuale", category: "Trasmissione", sided: false, shippable: false, basePrice: 320, value: 5 },
  { id: "alternatore", name: "Alternatore", category: "Elettrico", sided: false, shippable: true, basePrice: 85, render: "/renders/alternatore.png", value: 4 },
  { id: "motorino", name: "Motorino avviamento", category: "Elettrico", sided: false, shippable: true, basePrice: 70, value: 4 },
  { id: "centralina", name: "Centralina motore", category: "Elettrico", sided: false, shippable: true, basePrice: 140, value: 4 },
  { id: "batteria", name: "Batteria", category: "Elettrico", sided: false, shippable: false, basePrice: 45, render: "/renders/batteria.png", value: 2 },
  { id: "faro", name: "Faro anteriore", category: "Ottica", sided: true, shippable: true, basePrice: 95, render: "/renders/faro.png", value: 4 },
  { id: "fanale", name: "Fanale posteriore", category: "Ottica", sided: true, shippable: true, basePrice: 45, value: 3 },
  { id: "specchietto", name: "Specchietto retrovisore", category: "Carrozzeria", sided: true, shippable: true, basePrice: 40, value: 3 },
  { id: "porta", name: "Porta", category: "Carrozzeria", sided: true, shippable: false, basePrice: 120, value: 3 },
  { id: "cofano", name: "Cofano anteriore", category: "Carrozzeria", sided: false, shippable: false, basePrice: 110, value: 2 },
  { id: "paraurti", name: "Paraurti anteriore", category: "Carrozzeria", sided: false, shippable: false, basePrice: 90, value: 2 },
  { id: "cerchio", name: "Cerchio in lega", category: "Ruote", sided: false, shippable: true, basePrice: 60, render: "/renders/cerchio.png", value: 3 },
  { id: "disco", name: "Disco freno anteriore", category: "Freni", sided: true, shippable: true, basePrice: 25, render: "/renders/disco-freno.png", value: 2 },
  { id: "ammortizzatore", name: "Ammortizzatore anteriore", category: "Sospensioni", sided: true, shippable: true, basePrice: 35, render: "/renders/ammortizzatore.png", value: 2 },
  { id: "radiatore", name: "Radiatore", category: "Raffreddamento", sided: false, shippable: true, basePrice: 55, value: 3 },
  { id: "compressore", name: "Compressore A/C", category: "Climatizzazione", sided: false, shippable: true, basePrice: 130, value: 4 },
  { id: "quadro", name: "Quadro strumenti", category: "Interni", sided: false, shippable: true, basePrice: 75, value: 3 },
];

export const typeById = (id: string) =>
  PART_TYPES.find((t) => t.id === id) ?? PART_TYPES[0];

export const CONDITIONS: Record<Condition, { label: string; hint: string }> = {
  A: { label: "Come nuovo", hint: "Nessun segno, perfettamente funzionante" },
  B: { label: "Buono", hint: "Segni d'uso lievi, funzionante" },
  C: { label: "Usurato", hint: "Usura visibile o piccoli difetti" },
  D: { label: "Da revisionare", hint: "Per ricambio o rigenerazione" },
};

export const SIDES = ["Anteriore sx", "Anteriore dx", "Posteriore sx", "Posteriore dx", "Sinistro", "Destro"];

// Lati sensati per tipo: solo le porte hanno anteriore e posteriore; un faro anteriore è sinistro o destro
export const sidesFor = (typeId: string) => (typeId === "porta" ? ["Anteriore sx", "Anteriore dx", "Posteriore sx", "Posteriore dx"] : ["Sinistro", "Destro"]);

export interface Platform {
  id: string;
  make: string;
  model: string;
  label: string;
  years: string;
}

// Piattaforme demo: in produzione la compatibilità arriva da codici OEM / cataloghi licenziati.
export const PLATFORMS: Platform[] = [
  { id: "fiat-panda-319", make: "Fiat", model: "Panda", label: "Fiat Panda (319)", years: "2012–" },
  { id: "fiat-punto-199", make: "Fiat", model: "Punto Evo", label: "Fiat Punto Evo (199)", years: "2009–2012" },
  { id: "lancia-ypsilon-846", make: "Lancia", model: "Ypsilon", label: "Lancia Ypsilon (846)", years: "2011–" },
  { id: "vw-golf-6", make: "Volkswagen", model: "Golf VI", label: "Volkswagen Golf VI", years: "2008–2012" },
  { id: "ford-fiesta-7", make: "Ford", model: "Fiesta", label: "Ford Fiesta Mk7", years: "2008–2017" },
  { id: "renault-clio-3", make: "Renault", model: "Clio III", label: "Renault Clio III", years: "2005–2012" },
  { id: "opel-corsa-d", make: "Opel", model: "Corsa D", label: "Opel Corsa D", years: "2006–2014" },
  { id: "toyota-yaris-2", make: "Toyota", model: "Yaris", label: "Toyota Yaris II", years: "2005–2011" },
  { id: "alfa-giulietta-940", make: "Alfa Romeo", model: "Giulietta", label: "Alfa Romeo Giulietta (940)", years: "2010–2020" },
  { id: "peugeot-208", make: "Peugeot", model: "208", label: "Peugeot 208", years: "2012–2019" },
  // piattaforme senza veicoli in demo, servono per le compatibilità
  { id: "fiat-500-312", make: "Fiat", model: "500", label: "Fiat 500 (312)", years: "2007–" },
  { id: "ford-ka-2", make: "Ford", model: "Ka", label: "Ford Ka (RU8)", years: "2008–2016" },
  { id: "fiat-grande-punto-199", make: "Fiat", model: "Grande Punto", label: "Fiat Grande Punto (199)", years: "2005–2009" },
  { id: "alfa-mito-955", make: "Alfa Romeo", model: "MiTo", label: "Alfa Romeo MiTo (955)", years: "2008–2018" },
  { id: "fiat-bravo-198", make: "Fiat", model: "Bravo", label: "Fiat Bravo (198)", years: "2007–2014" },
  { id: "audi-a3-8p", make: "Audi", model: "A3", label: "Audi A3 (8P)", years: "2003–2012" },
  { id: "skoda-octavia-1z", make: "Skoda", model: "Octavia", label: "Skoda Octavia II (1Z)", years: "2004–2013" },
  { id: "seat-leon-1p", make: "Seat", model: "Leon", label: "Seat Leon (1P)", years: "2005–2012" },
  { id: "mazda-2-de", make: "Mazda", model: "2", label: "Mazda 2 (DE)", years: "2007–2014" },
  { id: "citroen-c3-2", make: "Citroën", model: "C3", label: "Citroën C3 II", years: "2009–2016" },
  { id: "renault-modus", make: "Renault", model: "Modus", label: "Renault Modus", years: "2004–2012" },
  { id: "opel-adam", make: "Opel", model: "Adam", label: "Opel Adam", years: "2012–2019" },
];

export const platformById = (id: string) => PLATFORMS.find((p) => p.id === id);
