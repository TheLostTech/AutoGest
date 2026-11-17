import { PART_TYPES, typeById } from "./catalog";
import { catalogFor, CATALOG_SOURCE } from "./partsdb";
import { corsiaId, locToString, scaffaleId, warehouseFor } from "./warehouse";
import { eerByCode, movesForBonifica, movesForIntake, typicalBonifica } from "./ambiente";
import { missingFields, monthKey } from "./periodo";
import type {
  AuditEvent,
  Soggetto,
  Condition,
  Fir,
  InventoryCount,
  Order,
  SalesDoc,
  Part,
  PartStatus,
  StockRule,
  Vehicle,
  WasteMove,
} from "./types";

// Tutti i dati qui sono sintetici (targhe, telai, pratiche, prezzi).

function rng(seed: number) {
  let s = seed;
  return () => {
    s = (s * 1664525 + 1013904223) % 4294967296;
    return s / 4294967296;
  };
}

const daysAgo = (d: number, h = 9) => {
  const base = new Date("2026-11-16T08:00:00");
  base.setDate(base.getDate() - d);
  base.setHours(h, Math.floor((d * 37) % 60));
  return base.toISOString();
};

export const pad = (n: number) => String(n).padStart(6, "0");

const V = (
  n: number,
  plate: string,
  vin: string,
  make: string,
  model: string,
  version: string,
  platform: string,
  year: number,
  fuel: string,
  km: number,
  color: string,
  days: number,
  dossier: string,
  dstatus: Vehicle["dossier"]["status"],
  work: Vehicle["work"],
  verification: Vehicle["verification"] = "verificato",
  notes?: string,
): Vehicle => ({
  id: `V-${pad(n)}`,
  plate,
  vin,
  make,
  model,
  version,
  platform,
  year,
  fuel,
  km,
  color,
  intakeAt: daysAgo(days),
  dossier: { number: dossier, kind: "Certificato di rottamazione", status: dstatus },
  verification,
  work,
  notes,
  createdBy: "Giulia (accettazione)",
});

export const SEED_VEHICLES: Vehicle[] = [
  V(118, "EK482TR", "ZFA31200003K48211", "Fiat", "Panda", "1.2 69 CV Lounge", "fiat-panda-319", 2013, "Benzina", 168400, "Bianco", 1, "CR-2026-004812", "in corso", "in smontaggio"),
  V(117, "FB903LM", "WVWZZZ1KZBW903417", "Volkswagen", "Golf VI", "1.6 TDI 105 CV Highline", "vw-golf-6", 2011, "Diesel", 231900, "Grigio scuro", 2, "CR-2026-004809", "in corso", "in smontaggio"),
  V(116, "DX215PA", "ZFA19900001P21566", "Fiat", "Punto Evo", "1.3 Multijet 75 CV", "fiat-punto-199", 2010, "Diesel", 204000, "Rosso", 5, "CR-2026-004797", "completata", "accettato"),
  V(115, "GA771ZK", "VF15RBJ0D48771220", "Renault", "Clio III", "1.2 16V 75 CV", "renault-clio-3", 2009, "Benzina", 189300, "Blu", 8, "", "da registrare", "accettato", "da verificare", "Banca dati veicoli non raggiungibile all'ingresso: modello inserito a mano."),
  V(112, "EH604SN", "ZAR94000007E60412", "Alfa Romeo", "Giulietta", "1.6 JTDm 105 CV", "alfa-giulietta-940", 2012, "Diesel", 246700, "Nero", 9, "CR-2026-004731", "completata", "smontato"),
  V(109, "DT338CF", "WF0DXXGAKD9T33811", "Ford", "Fiesta", "1.25 82 CV Titanium", "ford-fiesta-7", 2009, "Benzina", 152800, "Argento", 14, "CR-2026-004688", "completata", "smontato"),
  V(104, "FH129RB", "ZLA84600001F12907", "Lancia", "Ypsilon", "1.2 69 CV Gold", "lancia-ypsilon-846", 2012, "Benzina", 121500, "Avorio", 21, "CR-2026-004602", "completata", "smontato"),
  V(98, "DS880KV", "W0L0SDL68A4880312", "Opel", "Corsa D", "1.2 80 CV", "opel-corsa-d", 2008, "GPL", 198200, "Bianco", 33, "CR-2026-004455", "completata", "smontato"),
  V(91, "EA455GT", "VNKKL96360A455128", "Toyota", "Yaris", "1.0 VVT-i", "toyota-yaris-2", 2010, "Benzina", 143900, "Azzurro", 47, "CR-2026-004301", "completata", "smontato"),
  V(87, "FN066DP", "VF3CCHMZ6DT066231", "Peugeot", "208", "1.4 HDi 68 CV", "peugeot-208", 2013, "Diesel", 177600, "Grigio", 58, "CR-2026-004190", "completata", "smontato"),
  V(66, "DZ902KA", "ZFA31200003D90233", "Fiat", "Panda", "1.2 69 CV Pop", "fiat-panda-319", 2012, "Benzina", 201300, "Azzurro", 96, "CR-2026-003611", "completata", "smontato"),
  V(80, "EM317HC", "ZFA31200003M31790", "Fiat", "Panda", "1.3 Multijet 75 CV", "fiat-panda-319", 2014, "Diesel", 219000, "Verde", 72, "CR-2026-003987", "completata", "smontato"),
];

const OPERATORS = ["Marco (smontaggio)", "Luca (smontaggio)", "Davide (smontaggio)"];

// Pesi in ordine di marcia (demo) per piattaforma
const WEIGHTS: Record<string, number> = {
  "fiat-panda-319": 975,
  "vw-golf-6": 1260,
  "fiat-punto-199": 1080,
  "renault-clio-3": 1050,
  "alfa-giulietta-940": 1320,
  "ford-fiesta-7": 1040,
  "lancia-ypsilon-846": 965,
  "opel-corsa-d": 1060,
  "toyota-yaris-2": 1010,
  "peugeot-208": 1050,
};

export const SEED_RULES: StockRule[] = PART_TYPES.map((t) => ({
  typeId: t.id,
  min: t.value >= 4 ? 2 : t.value === 3 ? 2 : 1,
  max: t.value >= 4 ? 4 : t.value === 3 ? 4 : 3,
}));

// Quali ricambi sono già stati recuperati da quali veicoli (storico demo)
const PLAN: Record<string, string[]> = {
  "V-000118": ["faro", "faro", "specchietto", "alternatore"],
  "V-000117": ["centralina", "faro", "cerchio", "cerchio"],
  "V-000112": ["motore", "cambio", "faro", "faro", "alternatore", "compressore", "quadro", "cerchio", "cerchio", "cerchio", "cerchio", "porta", "specchietto"],
  "V-000109": ["alternatore", "motorino", "fanale", "fanale", "radiatore", "porta", "porta", "batteria", "disco", "ammortizzatore"],
  "V-000104": ["faro", "fanale", "specchietto", "specchietto", "quadro", "centralina", "cofano", "cerchio", "cerchio"],
  "V-000098": ["motore", "alternatore", "motorino", "radiatore", "porta", "paraurti", "disco", "disco"],
  "V-000091": ["faro", "faro", "compressore", "quadro", "ammortizzatore", "ammortizzatore", "specchietto"],
  "V-000087": ["centralina", "alternatore", "fanale", "cerchio", "cerchio", "batteria", "porta"],
  "V-000066": ["cerchio", "cerchio", "cerchio", "cerchio", "porta", "porta", "specchietto", "fanale", "fanale", "batteria", "disco", "disco", "ammortizzatore", "radiatore", "quadro", "paraurti"],
  "V-000080": ["motore", "cambio", "alternatore", "motorino", "faro", "specchietto", "compressore", "radiatore", "cofano", "quadro"],
};


export function buildSeed() {
  const r = rng(42);
  const parts: Part[] = [];
  const audit: AuditEvent[] = [];
  let pn = 2300; // la numerazione riprende dopo il magazzino migrato
  let an = 1;
  const log = (e: Omit<AuditEvent, "id">) =>
    audit.push({ id: `E-${pad(an++)}`, ...e });

  for (const v of SEED_VEHICLES) {
    log({
      at: v.intakeAt,
      user: v.createdBy,
      role: "accettazione",
      device: "PC ufficio",
      entity: "veicolo",
      entityId: v.id,
      action: "Ingresso veicolo registrato",
      detail: `${v.plate} · ${v.make} ${v.model}`,
    });
    const list = PLAN[v.id] ?? [];
    const vDays = Math.round(
      (new Date("2026-11-16").getTime() - new Date(v.intakeAt).getTime()) / 864e5,
    );
    const sideCount: Record<string, number> = {};
    list.forEach((typeId, i) => {
      const t = typeById(typeId);
      const id = `R-${pad(++pn)}`;
      const condRoll = r();
      const condition: Condition = condRoll < 0.2 ? "A" : condRoll < 0.7 ? "B" : condRoll < 0.92 ? "C" : "D";
      const sc = (sideCount[typeId] = (sideCount[typeId] ?? 0) + 1);
      const side = t.sided ? (sc % 2 === 1 ? (typeId === "fanale" ? "Posteriore sx" : "Anteriore sx") : typeId === "fanale" ? "Posteriore dx" : "Anteriore dx") : undefined;
      const age = Math.max(0, vDays - Math.floor(i / 3));
      const fresh = age <= 2;
      let status: PartStatus = fresh ? (i % 2 === 0 ? "bozza" : "disponibile") : "disponibile";
      const roll = r();
      if (!fresh && roll < 0.22) status = "venduto";
      else if (!fresh && roll < 0.27) status = "riservato";
      else if (!fresh && roll < 0.3) status = "invendibile";
      const priced = !fresh || i % 3 !== 0;
      const price = priced ? Math.round((t.basePrice * (condition === "A" ? 1.2 : condition === "B" ? 1 : condition === "C" ? 0.75 : 0.5)) / 5) * 5 : undefined;
      const hasPhoto = !!t.render && r() > 0.12;
      const located = !fresh || i % 2 === 1;
      const wh = warehouseFor(t.category, t.shippable);
      const cat = catalogFor(typeId, v.platform, side);
      const oemRead = !!cat && r() > 0.25;
      const verified = oemRead && r() > 0.35;
      const legacy = v.intakeAt < daysAgo(60) ? `K000${"ABCDEFGHJKLMNPRSTUVWXYZ"[Math.floor(r() * 23)]}${"ABCDEFGHJKLMNPRSTUVWXYZ"[Math.floor(r() * 23)]}${Math.floor(r() * 10)}${String(Math.floor(r() * 99)).padStart(2, "0")}` : undefined;
      const published = (status === "disponibile" || status === "riservato") && hasPhoto && !!price && !fresh;
      const p: Part = {
        id,
        vehicleId: v.id,
        typeId,
        description: `${t.name} ${v.make} ${v.model}${side ? ` ${side.toLowerCase()}` : ""}`,
        condition,
        status,
        side,
        oem: oemRead ? cat!.oem : undefined,
        oemVerified: verified,
        manufacturer: oemRead ? cat!.manufacturer : undefined,
        compat: verified ? { platforms: cat!.platforms, source: CATALOG_SOURCE, verified: true } : undefined,
        legacyCode: legacy,
        km: v.km,
        defects: condition === "C" ? "Graffi superficiali" : condition === "D" ? "Da verificare al banco prova" : undefined,
        price,
        location: located
          ? {
              mag: wh.id,
              corsia: corsiaId(1 + Math.floor(r() * Math.min(wh.corsie, 3))),
              scaffale: scaffaleId(1 + Math.floor(r() * Math.min(wh.scaffali, 5))),
              ripiano: wh.ripiani[Math.floor(r() * wh.ripiani.length)],
              contenitore: wh.contenitori ? String(1 + Math.floor(r() * wh.contenitori)) : undefined,
            }
          : undefined,
        photos: hasPhoto && t.render ? [t.render] : [],
        labelPrints: located ? 1 : 0,
        listing: published ? "pubblicato" : "non pubblicato",
        createdAt: daysAgo(age, 9 + (i % 8)),
        createdBy: OPERATORS[i % OPERATORS.length],
      };
      parts.push(p);
      log({ at: p.createdAt, user: p.createdBy, role: "smontatore", device: "Smartphone campo 1", entity: "ricambio", entityId: id, action: "Ricambio catalogato", detail: `${t.name} da ${v.id}` });
      if (p.labelPrints) log({ at: p.createdAt, user: p.createdBy, role: "smontatore", device: "Stampante etichette banco", entity: "ricambio", entityId: id, action: "Etichetta stampata" });
      if (p.location) log({ at: p.createdAt, user: "Paolo (magazzino)", role: "magazziniere", device: "Smartphone magazzino", entity: "ricambio", entityId: id, action: "Posizione assegnata", detail: locToString(p.location) });
      if (p.listing === "pubblicato") log({ at: p.createdAt, user: "Sara (responsabile)", role: "responsabile", device: "PC ufficio", entity: "ricambio", entityId: id, action: "Pubblicato sul negozio" });
    });
  }

  const orders: Order[] = [];
  let on = 410;
  for (const p of parts.filter((p) => p.status === "venduto" || p.status === "riservato")) {
    const channel = (["banco", "negozio", "marketplace"] as const)[on % 3];
    const id = `O-${pad(++on)}`;
    const at = p.createdAt;
    const sold = p.status === "venduto";
    orders.push({
      id,
      channel,
      partIds: [p.id],
      amount: p.price ?? 0,
      status: sold ? (channel === "banco" ? "consegnato" : "spedito") : "in attesa di pagamento",
      customer: channel === "banco" ? "Cliente al banco" : channel === "negozio" ? "Cliente online" : "Acquirente marketplace (demo)",
      paymentRef: sold ? `PAY-DEMO-${on}` : undefined,
      createdAt: at,
      history: sold
        ? [
            { at, status: "in attesa di pagamento" },
            { at, status: "pagato" },
            { at, status: channel === "banco" ? "consegnato" : "spedito" },
          ]
        : [{ at, status: "in attesa di pagamento" }],
    });
    log({ at, user: channel === "banco" ? "Anna (vendite)" : "Sistema", role: channel === "banco" ? "vendite" : "sistema", device: channel === "banco" ? "PC banco" : channel, entity: "ordine", entityId: id, action: sold ? "Vendita registrata" : "Ricambio riservato", detail: p.id });
  }

  // ——— Ambiente: pesi, bonifiche, registro di carico e scarico, formulari ———
  const hours = (iso: string, h: number) => new Date(new Date(iso).getTime() + h * 36e5).toISOString();
  const vehicles: Vehicle[] = SEED_VEHICLES.map((v, i) => {
    const base: Vehicle = { ...v, weightKg: WEIGHTS[v.platform] ?? 1000 };
    if (!v.dossier.number) return base; // V-000115: pratica ancora da avviare
    const dealer = i % 4 === 2;
    const n = Number(v.id.slice(-3));
    // Codici fiscali e partite IVA finti, solo per la demo
    const conferente = dealer
      ? { tipo: "concessionaria" as const, nome: "Concessionaria Demo Auto", cf: "01234567890" }
      : { tipo: "privato" as const, nome: `Detentore demo ${v.id.slice(-3)}`, cf: `DMODTN${80 + (n % 20)}A01L219X` };
    const documenti = ["libretto", "proprieta", "identita", "targa-ant", "targa-post", ...(dealer ? ["delega"] : [])];
    const done = v.dossier.status === "completata";
    return {
      ...base,
      conferente,
      documenti,
      visura: { at: v.intakeAt, fermo: false, intestatario: conferente.nome },
      presaInCarico: { at: v.intakeAt, by: "Giulia (accettazione)" },
      radiazione: done
        ? { stato: "completata", richiestaAt: hours(v.intakeAt, 24), completataAt: hours(v.intakeAt, 24 * 6), estremi: `RAD-${v.dossier.number.slice(-6)}` }
        : v.id === "V-000117"
          ? { stato: "richiesta", richiestaAt: hours(v.intakeAt, 20) }
          : { stato: "da richiedere" },
    };
  });
  const raw: Omit<WasteMove, "id">[] = [];
  for (const v of vehicles) {
    // Tutti pesati alla pesa, tranne V-000116: la sua registrazione resta in bozza finché non si inserisce il peso
    raw.push(...movesForIntake(v, v.intakeAt, v.id !== "V-000116"));
    if (v.work === "accettato") continue;
    const at = hours(v.intakeAt, 3);
    const items = typicalBonifica(v).map((it) => ({ ...it, qty: it.key === "carburante" ? Math.round(2 + r() * 12) : it.key === "oli" ? Math.round((3.5 + r() * 2.5) * 10) / 10 : it.qty }));
    const { moves, residualKg } = movesForBonifica(v, items, at);
    v.bonifica = { at, by: "Davide (smontaggio)", items, residualKg };
    raw.push(...moves);
    log({ at, user: "Davide (smontaggio)", role: "smontatore", device: "Smartphone campo 2", entity: "veicolo", entityId: v.id, action: "Bonifica registrata", detail: `${moves.length} movimenti nel registro rifiuti` });
  }

  // Anagrafica dei soggetti dei formulari (dati finti)
  const soggetti: Soggetto[] = [
    { id: "S-001", ruolo: "impianto", nome: "Autodemolizione Demo S.r.l.", cf: "01234567890", sede: "Via Demo 1, Torino (TO)", autorizzazione: "Aut. unica art. 208 D.Lgs. 152/06 n. DEMO-0001/2019", operazione: "R13" },
    { id: "S-002", ruolo: "destinatario", nome: "Centro Recuperi Demo S.r.l.", cf: "02345678901", sede: "Via Recuperi 17, Torino (TO)", autorizzazione: "AIA art. 29-ter n. DEMO-0002/2022", operazione: "R13" },
    { id: "S-003", ruolo: "trasportatore", nome: "Centro Recuperi Demo S.r.l.", cf: "02345678901", albo: "TO/000001" },
    { id: "S-004", ruolo: "intermediario", nome: "Metalli Demo S.p.A.", cf: "03456789012", albo: "TO/000004" },
    { id: "S-005", ruolo: "destinatario", nome: "Recupero Oli Demo", cf: "04567890123", sede: "Via Oli 5, Asti (AT)", autorizzazione: "Aut. art. 208 n. DEMO-0005/2020", operazione: "R13" },
    { id: "S-006", ruolo: "destinatario", nome: "Recupero Catalizzatori Demo", cf: "05678901234", sede: "Via Catalizzatori 3, Novara (NO)", autorizzazione: "Aut. art. 208 n. DEMO-0006/2021", operazione: "R13" },
    { id: "S-007", ruolo: "destinatario", nome: "Raccolta Batterie Demo", cf: "06789012345", sede: "Via Batterie 9, Torino (TO)", autorizzazione: "Aut. art. 208 n. DEMO-0007/2018", operazione: "R13" },
    { id: "S-008", ruolo: "trasportatore", nome: "Trasporti Demo Snc", cf: "07890123456", albo: "TO/000002" },
    { id: "S-009", ruolo: "trasportatore", nome: "Autotrasporti Esempio Srl", cf: "08901234567", albo: "TO/000003" },
  ];
  const nomeOf = (id: string) => soggetti.find((x) => x.id === id)!.nome;

  // Formulari ricevuti: li emette e li vidima la ditta che ritira, l'impianto li firma
  const firs: Fir[] = [];
  let fn = 140;
  const oldOnes = vehicles.filter((v) => v.bonifica && v.intakeAt < daysAgo(30));
  const sumOf = (vs: Vehicle[], pick: (v: Vehicle) => number) => Math.round(vs.reduce((a, v) => a + pick(v), 0) * 10) / 10;
  const itemKgOf = (v: Vehicle, key: string, kgPer: number) => (v.bonifica?.items.find((i) => i.key === key)?.qty ?? 0) * kgPer;
  const plannedFirs: (Pick<Fir, "eer" | "kg" | "at" | "status" | "numero" | "destinatarioId" | "trasportatoreId" | "intermediarioId" | "targa" | "conducente" | "esito" | "kgAccettati">)[] = [
    // ottobre: carcasse accettate solo in parte (avviso nel periodo), oli firmati ma senza esito del destinatario
    { eer: "16 01 06", kg: sumOf(oldOnes, (v) => v.bonifica!.residualKg), at: daysAgo(25, 10), status: "accettato", numero: "DEMOA 00101 AA", destinatarioId: "S-002", trasportatoreId: "S-003", intermediarioId: "S-004", targa: "AB123CD", conducente: "Autista Demo", esito: "parziale" },
    { eer: "13 02 08*", kg: sumOf(oldOnes, (v) => itemKgOf(v, "oli", 0.9)), at: daysAgo(20, 11), status: "firmato", numero: "DEMOB 00102 AA", destinatarioId: "S-005", trasportatoreId: "S-008", targa: "EF456GH", conducente: "Autista Demo" },
    // novembre: catalizzatori accettati per intero
    { eer: "16 08 01", kg: sumOf(vehicles.filter((v) => v.bonifica && v.intakeAt < daysAgo(5)), () => 5), at: daysAgo(2, 15), status: "accettato", numero: "DEMOC 00103 AA", destinatarioId: "S-006", trasportatoreId: "S-008", targa: "EF456GH", conducente: "Autista Demo", esito: "accettato" },
  ];
  for (const f of plannedFirs) {
    const id = `F-${pad(++fn)}`;
    const history: Fir["history"] = [{ at: f.at, status: "da firmare", by: "Sara (responsabile)" }, { at: hours(f.at, 1), status: "firmato", by: "Sara (responsabile)" }];
    const accepted = f.status === "accettato";
    if (accepted) history.push({ at: hours(f.at, 30), status: "accettato", by: nomeOf(f.destinatarioId!) });
    const kgAccettati = f.esito === "parziale" ? Math.round(f.kg - 150) : f.esito === "accettato" ? f.kg : undefined;
    firs.push({
      id,
      ...f,
      destinatario: nomeOf(f.destinatarioId!),
      trasportatore: nomeOf(f.trasportatoreId!),
      emessoAt: f.at,
      inizioTrasportoAt: hours(f.at, 1),
      rinfusa: true,
      history,
      kgAccettati,
      arrivoAt: accepted ? hours(f.at, 3) : undefined,
    });
    const e = eerByCode(f.eer);
    raw.push({ at: hours(f.at, 1), kind: "scarico", eer: f.eer, kg: f.kg, origin: id, note: `Uscita verso ${nomeOf(f.destinatarioId!)}`, rentri: "da trasmettere", causale: "aT", fir: id, operazione: "R13", statoFisico: e?.stato, hp: e?.hp });
  }
  const batt = sumOf(vehicles.filter((v) => v.bonifica), () => 14);
  firs.push({ id: `F-${pad(++fn)}`, at: daysAgo(0, 7), eer: "16 06 01*", kg: batt, destinatario: nomeOf("S-007"), trasportatore: nomeOf("S-009"), status: "da firmare", history: [{ at: daysAgo(0, 7), status: "da firmare", by: "Sara (responsabile)" }], numero: "DEMOD 00104 AA", emessoAt: daysAgo(0, 7), destinatarioId: "S-007", trasportatoreId: "S-009", targa: "IL789MN", conducente: "Autista Demo", rinfusa: false });

  // Ottobre resta con una bozza: il primo ingresso del mese senza codice fiscale di chi conferisce
  raw.sort((a, b) => a.at.localeCompare(b.at));
  const octIntake = raw.find((m) => m.causale === "*T" && monthKey(m.at) === "2026-10");
  if (octIntake?.produttore) {
    octIntake.produttore = { nome: octIntake.produttore.nome };
    const veh = vehicles.find((v) => v.id === octIntake.origin);
    if (veh?.conferente) veh.conferente = { ...veh.conferente, cf: undefined };
  }

  // Registro: numeri progressivi per anno, registrazione lo stesso giorno dell'operazione;
  // i mesi prima di ottobre sono già trasmessi, ottobre è da trasmettere, novembre è in corso
  // Trasmissione simulata il 10 del mese successivo
  const sentOn = (key: string) => { const [y, mo] = key.split("-").map(Number); return new Date(y, mo, 10, 11).toISOString(); };
  const perYear = new Map<number, number>();
  // Il carico d'ingresso di ogni veicolo, per sapere se lo scarico interno della bonifica può essere numerato
  const draftIntake = new Set(raw.filter((m) => m.causale === "*T" && missingFields(m as WasteMove).length > 0).map((m) => m.origin));
  const wasteMoves: WasteMove[] = raw.map((m, i) => {
    const id = `M-${pad(i + 1)}`;
    const draft = missingFields(m as WasteMove).length > 0 || (m.causale === "I" && draftIntake.has(m.origin));
    const key = monthKey(m.at);
    const sent = !draft && key < "2026-10";
    const year = new Date(m.at).getFullYear();
    const numero = draft ? undefined : (perYear.get(year) ?? 0) + 1;
    if (numero) perYear.set(year, numero);
    return {
      ...m,
      id,
      ...(draft ? {} : { numero, registeredAt: m.at, by: m.causale === "*T" ? "Giulia (accettazione)" : "Davide (smontaggio)" }),
      rentri: sent ? "trasmesso" : "da trasmettere",
      rentriAt: sent ? sentOn(key) : undefined,
      rentriRicevuta: sent ? `RENTRI-SIM-${key}-DEMO01` : undefined,
    };
  });
  // Lo scarico interno della bonifica richiama il carico d'ingresso del veicolo
  for (const m of wasteMoves) if (m.causale === "I") m.caricoRif = wasteMoves.find((x) => x.causale === "*T" && x.origin === m.origin)?.id;

  // ——— Documenti di vendita: scontrini e una fattura per le vendite al banco, un preventivo aperto ———
  const docs: SalesDoc[] = [];
  const dn = { P: 0, DC: 0, FT: 0, NC: 0 };
  const num = (k: keyof typeof dn) => `${k}-2026-${String(++dn[k]).padStart(4, "0")}`;
  const line = (p: Part) => ({ partId: p.id, description: `${p.id} · ${p.description}`, price: p.price ?? 0 });
  const officina = { name: "Officina Demo Snc", taxId: "IT00000000001" };
  orders
    .filter((o) => o.channel === "banco" && o.status === "consegnato")
    .sort((a, b) => a.createdAt.localeCompare(b.createdAt))
    .forEach((o, i) => {
      const ps = o.partIds.map((pid) => parts.find((p) => p.id === pid)!);
      const invoice = i === 0;
      docs.push({
        id: num(invoice ? "FT" : "DC"),
        type: invoice ? "fattura" : "documento commerciale",
        at: o.createdAt,
        customer: invoice ? officina : { name: o.customer },
        lines: ps.map(line),
        total: o.amount,
        orderId: o.id,
        status: invoice ? "inviata allo SdI" : "emesso",
      });
      if (invoice) o.customer = officina.name;
    });
  const quoted = parts.filter((p) => p.status === "disponibile" && p.price && p.typeId === "faro").slice(0, 2);
  if (quoted.length) docs.push({ id: num("P"), type: "preventivo", at: daysAgo(3, 15), customer: officina, lines: quoted.map(line), total: quoted.reduce((a, p) => a + (p.price ?? 0), 0), status: "aperto" });
  docs.sort((a, b) => b.at.localeCompare(a.at));

  audit.sort((a, b) => a.at.localeCompare(b.at));
  return {
    vehicles,
    parts,
    orders,
    audit,
    rules: SEED_RULES,
    wasteMoves,
    firs,
    soggetti,
    docs,
    inventory: [] as InventoryCount[],
    counters: { vehicle: 118, part: pn, order: on, event: an, move: wasteMoves.length, fir: fn, docs: dn, inventory: 0 },
  };
}

export { locToString };
