import type { Condition, PartType } from "./types";

// Tassonomia demo. In produzione: categorie concordate col cliente.
export const PART_TYPES: PartType[] = [
  { id: "motore", name: "Motore completo", category: "Motore", sided: false, shippable: false, basePrice: 650, render: "/renders/motore.png", value: 5 },
  { id: "cambio", name: "Cambio manuale", category: "Trasmissione", sided: false, shippable: false, basePrice: 320, render: "/renders/cambio.png", value: 5 },
  { id: "alternatore", name: "Alternatore", category: "Elettrico", sided: false, shippable: true, basePrice: 85, render: "/renders/alternatore.png", value: 4 },
  { id: "motorino", name: "Motorino avviamento", category: "Elettrico", sided: false, shippable: true, basePrice: 70, render: "/renders/motorino.png", value: 4 },
  { id: "centralina", name: "Centralina motore", category: "Elettrico", sided: false, shippable: true, basePrice: 140, render: "/renders/centralina.png", value: 4 },
  { id: "batteria", name: "Batteria", category: "Elettrico", sided: false, shippable: false, basePrice: 45, render: "/renders/batteria.png", value: 2 },
  { id: "faro", name: "Faro anteriore", category: "Ottica", sided: true, shippable: true, basePrice: 95, render: "/renders/faro.png", value: 4 },
  { id: "fanale", name: "Fanale posteriore", category: "Ottica", sided: true, shippable: true, basePrice: 45, render: "/renders/fanale.png", value: 3 },
  { id: "specchietto", name: "Specchietto retrovisore", category: "Carrozzeria", sided: true, shippable: true, basePrice: 40, render: "/renders/specchietto.png", value: 3 },
  { id: "porta", name: "Porta", category: "Carrozzeria", sided: true, shippable: false, basePrice: 120, render: "/renders/porta.png", value: 3 },
  { id: "cofano", name: "Cofano anteriore", category: "Carrozzeria", sided: false, shippable: false, basePrice: 110, render: "/renders/cofano.png", value: 2 },
  { id: "paraurti", name: "Paraurti anteriore", category: "Carrozzeria", sided: false, shippable: false, basePrice: 90, render: "/renders/paraurti.png", value: 2 },
  { id: "cerchio", name: "Cerchio in lega", category: "Ruote", sided: false, shippable: true, basePrice: 60, render: "/renders/cerchio.png", value: 3 },
  { id: "disco", name: "Disco freno anteriore", category: "Freni", sided: true, shippable: true, basePrice: 25, render: "/renders/disco-freno.png", value: 2 },
  { id: "ammortizzatore", name: "Ammortizzatore anteriore", category: "Sospensioni", sided: true, shippable: true, basePrice: 35, render: "/renders/ammortizzatore.png", value: 2 },
  { id: "radiatore", name: "Radiatore", category: "Raffreddamento", sided: false, shippable: true, basePrice: 55, render: "/renders/radiatore.png", value: 3 },
  { id: "compressore", name: "Compressore A/C", category: "Climatizzazione", sided: false, shippable: true, basePrice: 130, render: "/renders/compressore.png", value: 4 },
  { id: "quadro", name: "Quadro strumenti", category: "Interni", sided: false, shippable: true, basePrice: 75, render: "/renders/quadro.png", value: 3 },
  // Motore
  { id: "testata", name: "Testata", category: "Motore", sided: false, shippable: true, basePrice: 250, render: "/renders/testata.png", value: 4 },
  { id: "turbina", name: "Turbocompressore", category: "Motore", sided: false, shippable: true, basePrice: 220, render: "/renders/turbina.png", value: 5 },
  { id: "iniettore", name: "Iniettore", category: "Motore", sided: false, shippable: true, basePrice: 60, render: "/renders/iniettore.png", value: 4 },
  { id: "corpo-farfallato", name: "Corpo farfallato", category: "Motore", sided: false, shippable: true, basePrice: 70, render: "/renders/corpo-farfallato.png", value: 3 },
  { id: "debimetro", name: "Debimetro", category: "Motore", sided: false, shippable: true, basePrice: 50, render: "/renders/debimetro.png", value: 3 },
  { id: "egr", name: "Valvola EGR", category: "Motore", sided: false, shippable: true, basePrice: 60, render: "/renders/egr.png", value: 3 },
  { id: "pompa-acqua", name: "Pompa acqua", category: "Motore", sided: false, shippable: true, basePrice: 35, render: "/renders/pompa-acqua.png", value: 2 },
  { id: "bobina", name: "Bobina accensione", category: "Motore", sided: false, shippable: true, basePrice: 30, render: "/renders/bobina.png", value: 3 },
  { id: "collettore", name: "Collettore aspirazione", category: "Motore", sided: false, shippable: true, basePrice: 70, render: "/renders/collettore.png", value: 2 },
  // Trasmissione
  { id: "semiasse", name: "Semiasse", category: "Trasmissione", sided: true, shippable: true, basePrice: 70, render: "/renders/semiasse.png", value: 3 },
  { id: "volano", name: "Volano", category: "Trasmissione", sided: false, shippable: true, basePrice: 70, render: "/renders/volano.png", value: 3 },
  // Sterzo
  { id: "scatola-guida", name: "Scatola guida", category: "Sterzo", sided: false, shippable: true, basePrice: 120, render: "/renders/scatola-guida.png", value: 4 },
  { id: "piantone", name: "Piantone sterzo", category: "Sterzo", sided: false, shippable: true, basePrice: 80, render: "/renders/piantone.png", value: 3 },
  { id: "volante", name: "Volante", category: "Sterzo", sided: false, shippable: true, basePrice: 60, render: "/renders/volante.png", value: 3 },
  { id: "pompa-servo", name: "Pompa servosterzo", category: "Sterzo", sided: false, shippable: true, basePrice: 90, render: "/renders/pompa-servo.png", value: 3 },
  { id: "devioluci", name: "Devioluci", category: "Sterzo", sided: false, shippable: true, basePrice: 45, render: "/renders/devioluci.png", value: 3 },
  // Freni
  { id: "pinza", name: "Pinza freno anteriore", category: "Freni", sided: true, shippable: true, basePrice: 40, render: "/renders/pinza.png", value: 3 },
  { id: "abs", name: "Gruppo ABS", category: "Freni", sided: false, shippable: true, basePrice: 150, render: "/renders/abs.png", value: 5 },
  { id: "pompa-freno", name: "Pompa freno con servofreno", category: "Freni", sided: false, shippable: true, basePrice: 70, render: "/renders/pompa-freno.png", value: 3 },
  // Sospensioni
  { id: "braccio", name: "Braccio oscillante", category: "Sospensioni", sided: true, shippable: true, basePrice: 35, render: "/renders/braccio.png", value: 2 },
  { id: "fusello", name: "Fusello con mozzo", category: "Sospensioni", sided: true, shippable: true, basePrice: 60, render: "/renders/fusello.png", value: 3 },
  { id: "molla", name: "Molla elicoidale", category: "Sospensioni", sided: true, shippable: true, basePrice: 20, render: "/renders/molla.png", value: 1 },
  // Raffreddamento e clima
  { id: "elettroventola", name: "Elettroventola", category: "Raffreddamento", sided: false, shippable: true, basePrice: 60, render: "/renders/elettroventola.png", value: 3 },
  { id: "vaschetta", name: "Vaschetta espansione", category: "Raffreddamento", sided: false, shippable: true, basePrice: 15, render: "/renders/vaschetta.png", value: 1 },
  { id: "condensatore", name: "Condensatore A/C", category: "Climatizzazione", sided: false, shippable: true, basePrice: 50, render: "/renders/condensatore.png", value: 2 },
  // Scarico e alimentazione
  { id: "catalizzatore", name: "Catalizzatore", category: "Scarico", sided: false, shippable: true, basePrice: 180, render: "/renders/catalizzatore.png", value: 5 },
  { id: "marmitta", name: "Silenziatore posteriore", category: "Scarico", sided: false, shippable: false, basePrice: 40, render: "/renders/marmitta.png", value: 1 },
  { id: "pompa-carburante", name: "Pompa carburante", category: "Alimentazione", sided: false, shippable: true, basePrice: 50, render: "/renders/pompa-carburante.png", value: 3 },
  { id: "serbatoio", name: "Serbatoio carburante", category: "Alimentazione", sided: false, shippable: false, basePrice: 70, render: "/renders/serbatoio.png", value: 2 },
  // Elettrico
  { id: "motorino-tergi", name: "Motorino tergicristallo", category: "Elettrico", sided: false, shippable: true, basePrice: 40, render: "/renders/motorino-tergi.png", value: 3 },
  { id: "alzacristallo", name: "Alzacristallo elettrico", category: "Elettrico", sided: true, shippable: true, basePrice: 45, render: "/renders/alzacristallo.png", value: 3 },
  { id: "body-computer", name: "Body computer", category: "Elettrico", sided: false, shippable: true, basePrice: 90, render: "/renders/body-computer.png", value: 4 },
  { id: "blocchetto", name: "Blocchetto accensione con chiave", category: "Elettrico", sided: false, shippable: true, basePrice: 50, render: "/renders/blocchetto.png", value: 3 },
  // Ottica
  { id: "fendinebbia", name: "Fendinebbia", category: "Ottica", sided: true, shippable: true, basePrice: 25, render: "/renders/fendinebbia.png", value: 2 },
  // Carrozzeria
  { id: "portellone", name: "Portellone posteriore", category: "Carrozzeria", sided: false, shippable: false, basePrice: 150, render: "/renders/portellone.png", value: 3 },
  { id: "parafango", name: "Parafango anteriore", category: "Carrozzeria", sided: true, shippable: false, basePrice: 70, render: "/renders/parafango.png", value: 2 },
  { id: "calandra", name: "Calandra", category: "Carrozzeria", sided: false, shippable: true, basePrice: 50, render: "/renders/calandra.png", value: 2 },
  { id: "maniglia", name: "Maniglia esterna", category: "Carrozzeria", sided: true, shippable: true, basePrice: 20, render: "/renders/maniglia.png", value: 2 },
  { id: "serratura", name: "Serratura porta", category: "Carrozzeria", sided: true, shippable: true, basePrice: 35, render: "/renders/serratura.png", value: 3 },
  { id: "cristallo", name: "Cristallo porta", category: "Carrozzeria", sided: true, shippable: false, basePrice: 45, render: "/renders/cristallo.png", value: 2 },
  // Interni
  { id: "sedile", name: "Sedile anteriore", category: "Interni", sided: true, shippable: false, basePrice: 120, render: "/renders/sedile.png", value: 3 },
  { id: "divanetto", name: "Sedile posteriore", category: "Interni", sided: false, shippable: false, basePrice: 90, render: "/renders/divanetto.png", value: 2 },
  { id: "cintura", name: "Cintura di sicurezza", category: "Interni", sided: true, shippable: true, basePrice: 30, render: "/renders/cintura.png", value: 2 },
  { id: "pannello-porta", name: "Pannello porta", category: "Interni", sided: true, shippable: false, basePrice: 40, render: "/renders/pannello-porta.png", value: 2 },
  { id: "plancia", name: "Plancia cruscotto", category: "Interni", sided: false, shippable: false, basePrice: 150, render: "/renders/plancia.png", value: 3 },
  { id: "autoradio", name: "Autoradio", category: "Interni", sided: false, shippable: true, basePrice: 60, render: "/renders/autoradio.png", value: 3 },
  { id: "comandi-clima", name: "Comandi clima", category: "Interni", sided: false, shippable: true, basePrice: 45, render: "/renders/comandi-clima.png", value: 3 },
  { id: "leva-cambio", name: "Leva cambio", category: "Interni", sided: false, shippable: true, basePrice: 35, render: "/renders/leva-cambio.png", value: 2 },
  { id: "freno-mano", name: "Leva freno a mano", category: "Interni", sided: false, shippable: true, basePrice: 25, render: "/renders/freno-mano.png", value: 2 },
  { id: "cassetto", name: "Cassetto portaoggetti", category: "Interni", sided: false, shippable: true, basePrice: 30, render: "/renders/cassetto.png", value: 2 },
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

// Lati sensati per tipo: le porte e ciò che sta su una porta hanno anteriore e posteriore; un faro anteriore è sinistro o destro
const PER_PORTA = new Set(["porta", "pannello-porta", "cristallo", "alzacristallo", "maniglia", "serratura", "cintura"]);
export const sidesFor = (typeId: string) => (PER_PORTA.has(typeId) ? ["Anteriore sx", "Anteriore dx", "Posteriore sx", "Posteriore dx"] : ["Sinistro", "Destro"]);

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
