import type { Condition, PartType } from "./types";

// ——— Misure ———
// Per bulloneria, fusibili, lampadine, gomme e cerchi il tipo è uno solo e la misura si sceglie quando si cataloga:
// la foto del catalogo è la stessa per tutte le misure.
const FILETTI_GROSSI: [string, number[]][] = [
  ["M5 × 0,8", [10, 12, 16, 20, 25, 30]],
  ["M6 × 1", [10, 12, 16, 20, 25, 30, 35, 40, 50]],
  ["M8 × 1,25", [12, 16, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80]],
  ["M10 × 1,5", [16, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100]],
  ["M12 × 1,75", [20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 120]],
  ["M14 × 2", [30, 35, 40, 50, 60, 70, 80, 90, 100, 120]],
  ["M16 × 2", [40, 50, 60, 70, 80, 90, 100, 120, 140]],
];
// Passo fine, comune su sospensioni, freni e motore
const FILETTI_FINI: [string, number[]][] = [
  ["M8 × 1", [16, 20, 25, 30, 40]],
  ["M10 × 1,25", [20, 25, 30, 35, 40, 50, 60]],
  ["M12 × 1,25", [25, 30, 40, 50, 60, 70, 80]],
  ["M12 × 1,5", [25, 30, 40, 50, 60, 70, 80, 90]],
  ["M14 × 1,5", [40, 50, 60, 70, 80, 100]],
];
const BULLONI = [...FILETTI_GROSSI, ...FILETTI_FINI].flatMap(([f, ls]) => ls.map((l) => `${f} × ${l} mm`));
const FILETTI_DADI = [...FILETTI_GROSSI, ...FILETTI_FINI].map(([f]) => f);
const RONDELLE = ["M5", "M6", "M8", "M10", "M12", "M14", "M16"].map((d) => `per ${d}`);
const PRIGIONIERI = ["M6 × 1", "M8 × 1,25", "M10 × 1,25", "M10 × 1,5", "M12 × 1,5"].flatMap((f) => [25, 30, 40, 50, 60].map((l) => `${f} × ${l} mm`));
const VITI_LAMIERA = [["2,9", [9.5, 13]], ["3,5", [9.5, 13, 16, 19]], ["3,9", [13, 16, 19]], ["4,2", [13, 16, 19, 25]], ["4,8", [16, 19, 25, 32]], ["5,5", [19, 25, 32]], ["6,3", [19, 25, 32]]]
  .flatMap(([d, ls]) => (ls as number[]).map((l) => `ST ${d} × ${String(l).replace(".", ",")} mm`));
const BULLONI_RUOTA = ["M12 × 1,25", "M12 × 1,5", "M14 × 1,5"].flatMap((f) => [22, 26, 28, 30, 35, 40, 45].flatMap((l) => [`${f} × ${l} mm sede conica`, `${f} × ${l} mm sede sferica`]));
const DADI_RUOTA = ["M12 × 1,25", "M12 × 1,5", "M14 × 1,5", "1/2\" UNF"].flatMap((f) => [`${f} chiave 17`, `${f} chiave 19`]);
const FASCETTE = ["8–12", "10–16", "12–20", "16–25", "20–32", "25–40", "32–50", "40–60", "50–70", "60–80", "70–90", "80–100"].map((r) => `${r} mm`);
const CLIP = [5, 6, 7, 8, 9, 10].flatMap((d) => [`rivetto a pressione foro Ø ${d} mm`, `clip pannello foro Ø ${d} mm`]);
const MOLLE_RICHIAMO = ["piccola (fino a 30 mm)", "media (30–60 mm)", "grande (oltre 60 mm)"];
const FUSIBILI = [
  ...["2", "3", "5", "7,5", "10", "15", "20", "25", "30"].map((a) => `Mini ${a} A`),
  ...["2", "3", "5", "7,5", "10", "15", "20", "25", "30", "40"].map((a) => `ATO ${a} A`),
  ...["20", "30", "40", "50", "60", "70", "80"].map((a) => `Maxi ${a} A`),
  ...["40", "50", "60", "80", "100", "125", "150"].map((a) => `Midi ${a} A`),
  ...["20", "25", "30", "40", "50", "60"].map((a) => `J-Case ${a} A`),
];
const LAMPADINE = ["H1", "H3", "H4", "H7", "H8", "H9", "H11", "H13", "H15", "HB3", "HB4", "HIR2", "D1S", "D2S", "D3S", "D4S", "P21W", "P21/5W", "PY21W", "P27W", "P27/7W", "W5W", "W16W", "W21W", "W21/5W", "WY21W", "C5W", "C10W", "R5W", "R10W", "T4W", "H6W", "PSX24W", "PSX26W", "LED"];
const RELE = ["4 poli 12 V 20 A", "4 poli 12 V 30 A", "5 poli 12 V 30 A", "5 poli 12 V 40 A", "micro 4 poli", "micro 5 poli", "lampeggiatore frecce", "relè candelette"];
const PNEUMATICI = [
  "145/70 R13", "155/65 R13", "155/70 R13", "165/70 R13", "155/65 R14", "165/65 R14", "165/70 R14", "175/65 R14", "175/70 R14", "185/65 R14",
  "165/65 R15", "175/65 R15", "185/55 R15", "185/60 R15", "185/65 R15", "195/50 R15", "195/55 R15", "195/60 R15", "195/65 R15", "205/65 R15",
  "185/55 R16", "195/55 R16", "205/50 R16", "205/55 R16", "205/60 R16", "215/55 R16", "215/60 R16", "215/65 R16",
  "205/50 R17", "215/45 R17", "215/50 R17", "215/55 R17", "215/60 R17", "225/45 R17", "225/50 R17", "225/55 R17", "235/55 R17",
  "225/40 R18", "225/45 R18", "235/40 R18", "235/45 R18", "235/50 R18", "235/55 R18", "245/40 R18", "225/40 R19", "235/35 R19", "245/40 R19",
];
const POLLICI_FERRO = ["13\"", "14\"", "15\"", "16\""];
const POLLICI_LEGA = ["14\"", "15\"", "16\"", "17\"", "18\"", "19\""];
const AMPERORA = ["35 Ah", "40 Ah", "44 Ah", "45 Ah", "50 Ah", "53 Ah", "60 Ah", "62 Ah", "70 Ah", "72 Ah", "74 Ah", "80 Ah", "92 Ah", "95 Ah"];

// Tassonomia demo. In produzione: categorie concordate col cliente.
export const PART_TYPES: PartType[] = [
  { id: "motore", name: "Motore completo", category: "Motore", sided: false, shippable: false, basePrice: 650, render: "/renders/motore.png", value: 5 },
  { id: "cambio", name: "Cambio manuale", category: "Trasmissione", sided: false, shippable: false, basePrice: 320, render: "/renders/cambio.png", value: 5 },
  { id: "alternatore", name: "Alternatore", category: "Elettrico", sided: false, shippable: true, basePrice: 85, render: "/renders/alternatore.png", value: 4 },
  { id: "motorino", name: "Motorino avviamento", category: "Elettrico", sided: false, shippable: true, basePrice: 70, render: "/renders/motorino.png", value: 4 },
  { id: "centralina", name: "Centralina motore", category: "Elettrico", sided: false, shippable: true, basePrice: 140, render: "/renders/centralina.png", value: 4 },
  { id: "batteria", name: "Batteria", category: "Elettrico", sided: false, shippable: false, basePrice: 45, render: "/renders/batteria.png", value: 2, misure: AMPERORA },
  { id: "faro", name: "Faro anteriore", category: "Ottica", sided: true, shippable: true, basePrice: 95, render: "/renders/faro.png", value: 4 },
  { id: "fanale", name: "Fanale posteriore", category: "Ottica", sided: true, shippable: true, basePrice: 45, render: "/renders/fanale.png", value: 3 },
  { id: "specchietto", name: "Specchietto retrovisore", category: "Carrozzeria", sided: true, shippable: true, basePrice: 40, render: "/renders/specchietto.png", value: 3 },
  { id: "porta", name: "Porta", category: "Carrozzeria", sided: true, shippable: false, basePrice: 120, render: "/renders/porta.png", value: 3 },
  { id: "cofano", name: "Cofano anteriore", category: "Carrozzeria", sided: false, shippable: false, basePrice: 110, render: "/renders/cofano.png", value: 2 },
  { id: "paraurti", name: "Paraurti anteriore", category: "Carrozzeria", sided: false, shippable: false, basePrice: 90, render: "/renders/paraurti.png", value: 2 },
  { id: "cerchio", name: "Cerchio in lega", category: "Ruote", sided: false, shippable: true, basePrice: 60, render: "/renders/cerchio.png", value: 3, misure: POLLICI_LEGA },
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
  // ——— Motore ———
  { id: "monoblocco", name: "Monoblocco", category: "Motore", sided: false, shippable: false, basePrice: 250, value: 3 },
  { id: "albero-motore", name: "Albero motore", category: "Motore", sided: false, shippable: true, basePrice: 120, value: 3 },
  { id: "albero-camme", name: "Albero a camme", category: "Motore", sided: false, shippable: true, basePrice: 60, value: 3 },
  { id: "pistone", name: "Pistone con biella", category: "Motore", sided: false, shippable: true, basePrice: 40, value: 2 },
  { id: "coppa-olio", name: "Coppa olio", category: "Motore", sided: false, shippable: true, basePrice: 50, value: 2 },
  { id: "coperchio-punterie", name: "Coperchio punterie", category: "Motore", sided: false, shippable: true, basePrice: 45, value: 2 },
  { id: "pompa-olio", name: "Pompa olio", category: "Motore", sided: false, shippable: true, basePrice: 50, value: 2 },
  { id: "supporto-filtro-olio", name: "Supporto filtro olio", category: "Motore", sided: false, shippable: true, basePrice: 35, value: 2 },
  { id: "pompa-alta-pressione", name: "Pompa alta pressione gasolio", category: "Motore", sided: false, shippable: true, basePrice: 220, value: 5 },
  { id: "rail", name: "Rail iniettori", category: "Motore", sided: false, shippable: true, basePrice: 70, value: 3 },
  { id: "candeletta", name: "Candeletta", category: "Motore", sided: false, shippable: true, basePrice: 8, value: 1 },
  { id: "collettore-scarico", name: "Collettore di scarico", category: "Motore", sided: false, shippable: true, basePrice: 60, value: 2 },
  { id: "intercooler", name: "Intercooler", category: "Motore", sided: false, shippable: true, basePrice: 70, value: 3 },
  { id: "scatola-filtro-aria", name: "Scatola filtro aria", category: "Motore", sided: false, shippable: true, basePrice: 30, value: 2 },
  { id: "manicotto-turbo", name: "Manicotto turbo", category: "Motore", sided: false, shippable: true, basePrice: 25, value: 2 },
  { id: "puleggia-albero", name: "Puleggia albero motore", category: "Motore", sided: false, shippable: true, basePrice: 40, value: 2 },
  { id: "tendicinghia", name: "Tendicinghia", category: "Motore", sided: false, shippable: true, basePrice: 30, value: 2 },
  { id: "supporto-motore", name: "Supporto motore", category: "Motore", sided: false, shippable: true, basePrice: 30, value: 2 },
  { id: "sensore-giri", name: "Sensore giri motore", category: "Motore", sided: false, shippable: true, basePrice: 25, value: 2 },
  { id: "sensore-fase", name: "Sensore di fase", category: "Motore", sided: false, shippable: true, basePrice: 25, value: 2 },
  { id: "termostato", name: "Corpo termostato", category: "Motore", sided: false, shippable: true, basePrice: 25, value: 2 },
  { id: "pompa-vuoto", name: "Pompa del vuoto", category: "Motore", sided: false, shippable: true, basePrice: 50, value: 3 },
  { id: "copri-motore", name: "Copri motore", category: "Motore", sided: false, shippable: true, basePrice: 30, value: 2 },
  { id: "carter-distribuzione", name: "Carter distribuzione", category: "Motore", sided: false, shippable: true, basePrice: 25, value: 1 },
  { id: "astina-olio", name: "Astina livello olio", category: "Motore", sided: false, shippable: true, basePrice: 10, value: 1 },
  // ——— Trasmissione ———
  { id: "kit-frizione", name: "Kit frizione", category: "Trasmissione", sided: false, shippable: true, basePrice: 70, value: 3 },
  { id: "pompa-frizione", name: "Pompa frizione", category: "Trasmissione", sided: false, shippable: true, basePrice: 30, value: 2 },
  { id: "cilindro-frizione", name: "Cilindro secondario frizione", category: "Trasmissione", sided: false, shippable: true, basePrice: 30, value: 2 },
  { id: "cambio-automatico", name: "Cambio automatico", category: "Trasmissione", sided: false, shippable: false, basePrice: 600, value: 5 },
  { id: "centralina-cambio", name: "Centralina cambio automatico", category: "Trasmissione", sided: false, shippable: true, basePrice: 150, value: 4 },
  { id: "differenziale", name: "Differenziale posteriore", category: "Trasmissione", sided: false, shippable: false, basePrice: 250, value: 4 },
  { id: "albero-trasmissione", name: "Albero di trasmissione", category: "Trasmissione", sided: false, shippable: false, basePrice: 150, value: 3 },
  { id: "cavi-cambio", name: "Cavi comando cambio", category: "Trasmissione", sided: false, shippable: true, basePrice: 40, value: 2 },
  { id: "supporto-cambio", name: "Supporto cambio", category: "Trasmissione", sided: false, shippable: true, basePrice: 30, value: 2 },
  // ——— Sterzo ———
  { id: "testina-sterzo", name: "Testina sterzo", category: "Sterzo", sided: true, shippable: true, basePrice: 20, value: 2 },
  { id: "tirante-sterzo", name: "Tirante sterzo", category: "Sterzo", sided: true, shippable: true, basePrice: 25, value: 2 },
  // ——— Freni ———
  { id: "disco-posteriore", name: "Disco freno posteriore", category: "Freni", sided: true, shippable: true, basePrice: 20, value: 2 },
  { id: "tamburo", name: "Tamburo freno", category: "Freni", sided: true, shippable: true, basePrice: 30, value: 2 },
  { id: "ganasce", name: "Ganasce freno", category: "Freni", sided: true, shippable: true, basePrice: 20, value: 1 },
  { id: "pastiglie", name: "Pastiglie freno", category: "Freni", sided: false, shippable: true, basePrice: 15, value: 1 },
  { id: "pinza-posteriore", name: "Pinza freno posteriore", category: "Freni", sided: true, shippable: true, basePrice: 40, value: 3 },
  { id: "sensore-abs", name: "Sensore ABS", category: "Freni", sided: true, shippable: true, basePrice: 20, value: 2 },
  { id: "tubo-freno", name: "Tubo freno flessibile", category: "Freni", sided: true, shippable: true, basePrice: 10, value: 1 },
  { id: "cavo-freno-mano", name: "Cavo freno a mano", category: "Freni", sided: true, shippable: true, basePrice: 15, value: 1 },
  { id: "attuatore-epb", name: "Attuatore freno di stazionamento elettrico", category: "Freni", sided: true, shippable: true, basePrice: 80, value: 3 },
  // ——— Sospensioni ———
  { id: "ammortizzatore-post", name: "Ammortizzatore posteriore", category: "Sospensioni", sided: true, shippable: true, basePrice: 30, value: 2 },
  { id: "barra-stabilizzatrice", name: "Barra stabilizzatrice", category: "Sospensioni", sided: false, shippable: true, basePrice: 40, value: 2 },
  { id: "bielletta", name: "Bielletta barra stabilizzatrice", category: "Sospensioni", sided: true, shippable: true, basePrice: 15, value: 1 },
  { id: "assale-posteriore", name: "Assale posteriore", category: "Sospensioni", sided: false, shippable: false, basePrice: 150, value: 3 },
  { id: "culla", name: "Culla motore", category: "Sospensioni", sided: false, shippable: false, basePrice: 120, value: 3 },
  { id: "mozzo-posteriore", name: "Mozzo ruota posteriore", category: "Sospensioni", sided: true, shippable: true, basePrice: 40, value: 2 },
  { id: "cuscinetto-ruota", name: "Cuscinetto ruota", category: "Sospensioni", sided: true, shippable: true, basePrice: 20, value: 2 },
  { id: "supporto-ammortizzatore", name: "Supporto ammortizzatore", category: "Sospensioni", sided: true, shippable: true, basePrice: 20, value: 1 },
  { id: "montante", name: "Montante McPherson completo", category: "Sospensioni", sided: true, shippable: true, basePrice: 90, value: 3 },
  // ——— Ruote ———
  { id: "cerchio-ferro", name: "Cerchio in ferro", category: "Ruote", sided: false, shippable: true, basePrice: 25, value: 2, misure: POLLICI_FERRO },
  { id: "pneumatico", name: "Pneumatico", category: "Ruote", sided: false, shippable: true, basePrice: 30, value: 3, misure: PNEUMATICI },
  { id: "ruotino", name: "Ruotino di scorta", category: "Ruote", sided: false, shippable: true, basePrice: 40, value: 2 },
  { id: "copricerchio", name: "Copricerchio", category: "Ruote", sided: false, shippable: true, basePrice: 8, value: 1, misure: POLLICI_FERRO },
  { id: "sensore-tpms", name: "Sensore pressione pneumatici", category: "Ruote", sided: false, shippable: true, basePrice: 25, value: 2 },
  { id: "cric", name: "Cric", category: "Ruote", sided: false, shippable: true, basePrice: 15, value: 1 },
  { id: "kit-gonfiaggio", name: "Kit di gonfiaggio", category: "Ruote", sided: false, shippable: true, basePrice: 20, value: 1 },
  // ——— Raffreddamento e clima ———
  { id: "manicotto-radiatore", name: "Manicotto radiatore", category: "Raffreddamento", sided: false, shippable: true, basePrice: 15, value: 1 },
  { id: "radiatore-riscaldamento", name: "Radiatore riscaldamento", category: "Raffreddamento", sided: false, shippable: true, basePrice: 35, value: 2 },
  { id: "resistenza-ventola", name: "Resistenza elettroventola", category: "Raffreddamento", sided: false, shippable: true, basePrice: 20, value: 2 },
  { id: "sensore-temperatura", name: "Sensore temperatura acqua", category: "Raffreddamento", sided: false, shippable: true, basePrice: 10, value: 1 },
  { id: "evaporatore", name: "Evaporatore", category: "Climatizzazione", sided: false, shippable: true, basePrice: 50, value: 2 },
  { id: "ventola-abitacolo", name: "Ventola abitacolo", category: "Climatizzazione", sided: false, shippable: true, basePrice: 40, value: 3 },
  { id: "gruppo-clima", name: "Gruppo riscaldamento e clima", category: "Climatizzazione", sided: false, shippable: false, basePrice: 120, value: 3 },
  { id: "tubo-clima", name: "Tubo aria condizionata", category: "Climatizzazione", sided: false, shippable: true, basePrice: 25, value: 1 },
  { id: "valvola-espansione", name: "Valvola di espansione", category: "Climatizzazione", sided: false, shippable: true, basePrice: 25, value: 1 },
  { id: "attuatore-clima", name: "Motorino sportello clima", category: "Climatizzazione", sided: false, shippable: true, basePrice: 25, value: 2 },
  { id: "resistenza-abitacolo", name: "Resistenza ventola abitacolo", category: "Climatizzazione", sided: false, shippable: true, basePrice: 20, value: 2 },
  // ——— Scarico e alimentazione ———
  { id: "fap", name: "Filtro antiparticolato (FAP)", category: "Scarico", sided: false, shippable: true, basePrice: 250, value: 5 },
  { id: "silenziatore-centrale", name: "Silenziatore centrale", category: "Scarico", sided: false, shippable: false, basePrice: 35, value: 1 },
  { id: "sonda-lambda", name: "Sonda lambda", category: "Scarico", sided: false, shippable: true, basePrice: 30, value: 3 },
  { id: "giunto-flessibile", name: "Giunto flessibile scarico", category: "Scarico", sided: false, shippable: true, basePrice: 20, value: 1 },
  { id: "bocchettone", name: "Bocchettone rifornimento", category: "Alimentazione", sided: false, shippable: true, basePrice: 30, value: 2 },
  { id: "canister", name: "Canister carboni attivi", category: "Alimentazione", sided: false, shippable: true, basePrice: 25, value: 1 },
  { id: "serbatoio-gpl", name: "Serbatoio GPL", category: "Alimentazione", sided: false, shippable: false, basePrice: 120, value: 3 },
  { id: "riduttore-gpl", name: "Riduttore GPL", category: "Alimentazione", sided: false, shippable: true, basePrice: 60, value: 3 },
  { id: "rampa-gpl", name: "Rampa iniettori GPL", category: "Alimentazione", sided: false, shippable: true, basePrice: 40, value: 2 },
  { id: "centralina-gpl", name: "Centralina GPL", category: "Alimentazione", sided: false, shippable: true, basePrice: 70, value: 3 },
  // ——— Elettrico ———
  { id: "cablaggio-motore", name: "Cablaggio motore", category: "Elettrico", sided: false, shippable: true, basePrice: 80, value: 3 },
  { id: "cablaggio-abitacolo", name: "Cablaggio abitacolo", category: "Elettrico", sided: false, shippable: false, basePrice: 80, value: 2 },
  { id: "scatola-fusibili", name: "Scatola fusibili vano motore", category: "Elettrico", sided: false, shippable: true, basePrice: 50, value: 3 },
  { id: "clacson", name: "Clacson", category: "Elettrico", sided: false, shippable: true, basePrice: 15, value: 1 },
  { id: "motorino-tergilunotto", name: "Motorino tergilunotto", category: "Elettrico", sided: false, shippable: true, basePrice: 35, value: 2 },
  { id: "pompa-lavavetri", name: "Pompa lavavetri", category: "Elettrico", sided: false, shippable: true, basePrice: 12, value: 1 },
  { id: "vaschetta-lavavetri", name: "Vaschetta lavavetri", category: "Elettrico", sided: false, shippable: true, basePrice: 20, value: 1 },
  { id: "sensore-pioggia", name: "Sensore pioggia", category: "Elettrico", sided: false, shippable: true, basePrice: 30, value: 2 },
  { id: "sensore-parcheggio", name: "Sensore di parcheggio", category: "Elettrico", sided: false, shippable: true, basePrice: 15, value: 2 },
  { id: "centralina-parcheggio", name: "Centralina sensori parcheggio", category: "Elettrico", sided: false, shippable: true, basePrice: 40, value: 2 },
  { id: "telecamera", name: "Telecamera posteriore", category: "Elettrico", sided: false, shippable: true, basePrice: 50, value: 3 },
  { id: "antenna", name: "Antenna", category: "Elettrico", sided: false, shippable: true, basePrice: 15, value: 1 },
  { id: "altoparlante", name: "Altoparlante", category: "Elettrico", sided: false, shippable: true, basePrice: 10, value: 1 },
  { id: "amplificatore", name: "Amplificatore audio", category: "Elettrico", sided: false, shippable: true, basePrice: 50, value: 2 },
  { id: "display", name: "Display multimediale", category: "Elettrico", sided: false, shippable: true, basePrice: 120, value: 4 },
  { id: "pulsantiera-alzacristalli", name: "Pulsantiera alzacristalli", category: "Elettrico", sided: true, shippable: true, basePrice: 25, value: 3 },
  { id: "comando-luci", name: "Comando luci", category: "Elettrico", sided: false, shippable: true, basePrice: 20, value: 2 },
  { id: "pulsante-emergenza", name: "Pulsante quattro frecce", category: "Elettrico", sided: false, shippable: true, basePrice: 10, value: 1 },
  { id: "chiave", name: "Chiave con telecomando", category: "Elettrico", sided: false, shippable: true, basePrice: 40, value: 3 },
  { id: "motorino-fari", name: "Motorino regolazione fari", category: "Elettrico", sided: true, shippable: true, basePrice: 20, value: 1 },
  { id: "centralina-xenon", name: "Centralina fari xeno", category: "Elettrico", sided: true, shippable: true, basePrice: 50, value: 3 },
  { id: "presa-12v", name: "Presa 12V e accendisigari", category: "Elettrico", sided: false, shippable: true, basePrice: 8, value: 1 },
  { id: "rele", name: "Relè", category: "Elettrico", sided: false, shippable: true, basePrice: 5, value: 1, misure: RELE },
  { id: "fusibile", name: "Fusibile", category: "Elettrico", sided: false, shippable: true, basePrice: 1, value: 1, misure: FUSIBILI },
  { id: "lampadina", name: "Lampadina", category: "Elettrico", sided: false, shippable: true, basePrice: 3, value: 1, misure: LAMPADINE },
  // ——— Ottica ———
  { id: "freccia-laterale", name: "Freccia laterale", category: "Ottica", sided: true, shippable: true, basePrice: 10, value: 1 },
  { id: "terzo-stop", name: "Terzo stop", category: "Ottica", sided: false, shippable: true, basePrice: 20, value: 2 },
  { id: "luce-targa", name: "Luce targa", category: "Ottica", sided: false, shippable: true, basePrice: 8, value: 1 },
  { id: "plafoniera", name: "Plafoniera interna", category: "Ottica", sided: false, shippable: true, basePrice: 15, value: 1 },
  { id: "catadiottro", name: "Catadiottro", category: "Ottica", sided: true, shippable: true, basePrice: 8, value: 1 },
  { id: "fanale-portellone", name: "Fanale sul portellone", category: "Ottica", sided: true, shippable: true, basePrice: 35, value: 2 },
  { id: "luce-diurna", name: "Luce diurna DRL", category: "Ottica", sided: true, shippable: true, basePrice: 30, value: 2 },
  { id: "retronebbia", name: "Retronebbia", category: "Ottica", sided: false, shippable: true, basePrice: 15, value: 1 },
  // ——— Carrozzeria ———
  { id: "paraurti-post", name: "Paraurti posteriore", category: "Carrozzeria", sided: false, shippable: false, basePrice: 90, value: 2 },
  { id: "traversa-paraurti", name: "Traversa paraurti", category: "Carrozzeria", sided: false, shippable: false, basePrice: 40, value: 2 },
  { id: "frontale", name: "Frontale (ossatura anteriore)", category: "Carrozzeria", sided: false, shippable: false, basePrice: 90, value: 2 },
  { id: "tetto-apribile", name: "Tetto apribile", category: "Carrozzeria", sided: false, shippable: false, basePrice: 150, value: 3 },
  { id: "parabrezza", name: "Parabrezza", category: "Carrozzeria", sided: false, shippable: false, basePrice: 80, value: 2 },
  { id: "lunotto", name: "Lunotto", category: "Carrozzeria", sided: false, shippable: false, basePrice: 60, value: 2 },
  { id: "cristallo-fisso", name: "Cristallo fisso laterale", category: "Carrozzeria", sided: true, shippable: false, basePrice: 35, value: 1 },
  { id: "vetro-specchietto", name: "Vetro specchietto", category: "Carrozzeria", sided: true, shippable: true, basePrice: 15, value: 2 },
  { id: "calotta-specchietto", name: "Calotta specchietto", category: "Carrozzeria", sided: true, shippable: true, basePrice: 20, value: 2 },
  { id: "passaruota", name: "Passaruota", category: "Carrozzeria", sided: true, shippable: true, basePrice: 15, value: 1 },
  { id: "paramotore", name: "Paramotore sottoscocca", category: "Carrozzeria", sided: false, shippable: true, basePrice: 30, value: 1 },
  { id: "modanatura", name: "Modanatura laterale", category: "Carrozzeria", sided: true, shippable: true, basePrice: 15, value: 1 },
  { id: "spoiler", name: "Spoiler posteriore", category: "Carrozzeria", sided: false, shippable: true, basePrice: 50, value: 2 },
  { id: "minigonna", name: "Minigonna sottoporta", category: "Carrozzeria", sided: true, shippable: false, basePrice: 30, value: 1 },
  { id: "sportellino-carburante", name: "Sportellino carburante", category: "Carrozzeria", sided: false, shippable: true, basePrice: 15, value: 1 },
  { id: "cerniera-porta", name: "Cerniera porta", category: "Carrozzeria", sided: true, shippable: true, basePrice: 15, value: 1 },
  { id: "cerniera-cofano", name: "Cerniera cofano", category: "Carrozzeria", sided: true, shippable: true, basePrice: 10, value: 1 },
  { id: "pistoncino-portellone", name: "Pistoncino portellone", category: "Carrozzeria", sided: true, shippable: true, basePrice: 12, value: 1 },
  { id: "serratura-cofano", name: "Serratura cofano", category: "Carrozzeria", sided: false, shippable: true, basePrice: 20, value: 1 },
  { id: "serratura-portellone", name: "Serratura portellone", category: "Carrozzeria", sided: false, shippable: true, basePrice: 30, value: 2 },
  { id: "barre-tetto", name: "Barre portatutto", category: "Carrozzeria", sided: false, shippable: true, basePrice: 40, value: 2 },
  { id: "gancio-traino", name: "Gancio traino", category: "Carrozzeria", sided: false, shippable: true, basePrice: 80, value: 3 },
  { id: "braccio-tergi", name: "Braccio tergicristallo", category: "Carrozzeria", sided: true, shippable: true, basePrice: 15, value: 1 },
  { id: "griglia-paraurti", name: "Griglia paraurti", category: "Carrozzeria", sided: false, shippable: true, basePrice: 20, value: 1 },
  { id: "cornice-fendinebbia", name: "Cornice fendinebbia", category: "Carrozzeria", sided: true, shippable: true, basePrice: 12, value: 1 },
  // ——— Interni ———
  { id: "consolle", name: "Consolle centrale", category: "Interni", sided: false, shippable: false, basePrice: 60, value: 2 },
  { id: "bracciolo", name: "Bracciolo", category: "Interni", sided: false, shippable: true, basePrice: 30, value: 2 },
  { id: "poggiatesta", name: "Poggiatesta", category: "Interni", sided: false, shippable: true, basePrice: 15, value: 1 },
  { id: "cielo", name: "Rivestimento cielo", category: "Interni", sided: false, shippable: false, basePrice: 40, value: 1 },
  { id: "aletta-parasole", name: "Aletta parasole", category: "Interni", sided: true, shippable: true, basePrice: 12, value: 1 },
  { id: "specchio-interno", name: "Specchio retrovisore interno", category: "Interni", sided: false, shippable: true, basePrice: 20, value: 2 },
  { id: "maniglia-interna", name: "Maniglia interna porta", category: "Interni", sided: true, shippable: true, basePrice: 10, value: 1 },
  { id: "maniglia-tetto", name: "Maniglia di cortesia", category: "Interni", sided: false, shippable: true, basePrice: 6, value: 1 },
  { id: "moquette", name: "Moquette", category: "Interni", sided: false, shippable: false, basePrice: 40, value: 1 },
  { id: "tappetini", name: "Tappetini", category: "Interni", sided: false, shippable: true, basePrice: 15, value: 1 },
  { id: "cappelliera", name: "Cappelliera", category: "Interni", sided: false, shippable: false, basePrice: 25, value: 1 },
  { id: "rivestimento-bagagliaio", name: "Rivestimento bagagliaio", category: "Interni", sided: false, shippable: false, basePrice: 25, value: 1 },
  { id: "rivestimento-montante", name: "Rivestimento montante", category: "Interni", sided: true, shippable: true, basePrice: 12, value: 1 },
  { id: "bocchetta-aria", name: "Bocchetta aerazione", category: "Interni", sided: true, shippable: true, basePrice: 12, value: 1 },
  { id: "copribagagliaio", name: "Copribagagliaio avvolgibile", category: "Interni", sided: false, shippable: true, basePrice: 40, value: 2 },
  { id: "guide-sedile", name: "Guide sedile", category: "Interni", sided: true, shippable: true, basePrice: 30, value: 1 },
  { id: "battitacco", name: "Battitacco", category: "Interni", sided: true, shippable: true, basePrice: 12, value: 1 },
  { id: "pedaliera", name: "Pedaliera", category: "Interni", sided: false, shippable: true, basePrice: 60, value: 2 },
  { id: "pedale-acceleratore", name: "Pedale acceleratore elettronico", category: "Interni", sided: false, shippable: true, basePrice: 40, value: 3 },
  // ——— Minuteria: un tipo per famiglia, la misura si sceglie quando si cataloga ———
  { id: "bullone", name: "Bullone testa esagonale", category: "Minuteria", sided: false, shippable: true, basePrice: 1, value: 1, misure: BULLONI },
  { id: "vite-brugola", name: "Vite a brugola", category: "Minuteria", sided: false, shippable: true, basePrice: 1, value: 1, misure: BULLONI },
  { id: "vite-torx", name: "Vite Torx", category: "Minuteria", sided: false, shippable: true, basePrice: 1, value: 1, misure: BULLONI },
  { id: "vite-lamiera", name: "Vite autofilettante", category: "Minuteria", sided: false, shippable: true, basePrice: 1, value: 1, misure: VITI_LAMIERA },
  { id: "dado", name: "Dado esagonale", category: "Minuteria", sided: false, shippable: true, basePrice: 1, value: 1, misure: FILETTI_DADI },
  { id: "dado-autobloccante", name: "Dado autobloccante", category: "Minuteria", sided: false, shippable: true, basePrice: 1, value: 1, misure: FILETTI_DADI },
  { id: "dado-flangiato", name: "Dado flangiato", category: "Minuteria", sided: false, shippable: true, basePrice: 1, value: 1, misure: FILETTI_DADI },
  { id: "rondella", name: "Rondella", category: "Minuteria", sided: false, shippable: true, basePrice: 1, value: 1, misure: RONDELLE },
  { id: "prigioniero", name: "Prigioniero", category: "Minuteria", sided: false, shippable: true, basePrice: 1, value: 1, misure: PRIGIONIERI },
  { id: "bullone-ruota", name: "Bullone ruota", category: "Minuteria", sided: false, shippable: true, basePrice: 2, value: 1, misure: BULLONI_RUOTA },
  { id: "dado-ruota", name: "Dado ruota", category: "Minuteria", sided: false, shippable: true, basePrice: 2, value: 1, misure: DADI_RUOTA },
  { id: "fascetta", name: "Fascetta stringitubo", category: "Minuteria", sided: false, shippable: true, basePrice: 1, value: 1, misure: FASCETTE },
  { id: "clip", name: "Clip e rivetto in plastica", category: "Minuteria", sided: false, shippable: true, basePrice: 1, value: 1, misure: CLIP },
  { id: "molla-richiamo", name: "Molla di richiamo", category: "Minuteria", sided: false, shippable: true, basePrice: 1, value: 1, misure: MOLLE_RICHIAMO },
];

// Tipologie per categoria (categorie nell'ordine del catalogo, tipi in ordine alfabetico), per i menu a tendina
export const TYPE_GROUPS: [string, PartType[]][] = [...new Set(PART_TYPES.map((t) => t.category))].map((c) => [
  c,
  PART_TYPES.filter((t) => t.category === c).sort((x, y) => x.name.localeCompare(y.name, "it")),
]);

// Soglia di scorta di partenza: i pezzi di valore si tengono in più esemplari, quelli minori solo su richiesta.
// La minuteria non si recupera per fare scorta: nella lista di smontaggio non compare.
export const defaultRule = (t: PartType) =>
  t.value >= 3 ? { min: 2, max: 4 } : t.value === 2 ? { min: 1, max: 3 } : { min: 0, max: 2 };
export const NON_DA_RECUPERARE = new Set(["Minuteria"]);

// Miniatura leggera (WebP 256 px) di un render, per gli elenchi: i PNG pieni pesano mezzo mega l'uno.
// Si rigenerano con scripts/miniature-render.py dopo ogni nuovo render.
export const miniRender = (src: string) => src.replace(/^\/renders\/(.+)\.png$/, "/renders/mini/$1.webp");

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
const PER_PORTA = new Set(["porta", "pannello-porta", "cristallo", "alzacristallo", "maniglia", "serratura", "cintura", "maniglia-interna", "pulsantiera-alzacristalli", "cerniera-porta"]);
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
