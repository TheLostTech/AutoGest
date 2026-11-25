// Registro rifiuti e periodo RENTRI: regole pure, senza dipendenze (testate con `npm test`).
// Fonti: DM 59/2023 art. 15 c. 2 (trasmissione mensile entro la fine del mese successivo),
// art. 190 c. 3 lett. d D.Lgs. 152/2006 (annotazione entro 2 giorni lavorativi per gli impianti),
// manuale RENTRI §3.2.1 e §4.2 (registrazione numerata non modificabile: rettifica o annullamento).
import type { Fir, WasteMove } from "./types";

const MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];

// Il mese si legge in ora locale: le 23:30 del 31 ottobre in Italia sono ottobre
export function monthKey(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export function monthLabel(key: string): string {
  const [y, m] = key.split("-").map(Number);
  return `${MESI[m - 1]} ${y}`;
}

// Fine del mese successivo, ultimo istante del giorno
export function deadlineOf(key: string): string {
  const [y, m] = key.split("-").map(Number);
  return new Date(y, m + 1, 0, 23, 59, 59, 999).toISOString();
}

// "1.234,5" → 1234.5 · "38,5" e "38.5" → 38.5 · "1.234" → 1234; zero, negativi e testo → null.
// Il punto vale come separatore delle migliaia solo se seguito da gruppi di tre cifre (tastiere dei telefoni
// che hanno solo il punto come decimale).
export function parseKg(raw: string): number | null {
  const t = raw.trim();
  let s: string;
  if (/^\d{1,3}(\.\d{3})+(,\d+)?$/.test(t)) s = t.replace(/\./g, "").replace(",", ".");
  else if (/^\d+([.,]\d+)?$/.test(t)) s = t.replace(",", ".");
  else return null;
  const n = Number(s);
  return Number.isFinite(n) && n > 0 ? n : null;
}

// Per precompilare un campo: 4.3 → "4,3"
export const kgText = (n: number) => n.toLocaleString("it-IT", { useGrouping: false, maximumFractionDigits: 3 });

export const isDraft = (m: WasteMove) => m.numero === undefined;

// Dati salvati prima del 25/11/2026: la causale «ricevuto da terzi» era scritta "*T", il RENTRI vuole "T*".
// Si converte alla lettura (dal dispositivo e dal server), senza cambiare la versione dell'archivio.
export function normalizzaMovimenti<T extends { causale?: string }>(moves: T[]): T[] {
  return moves.some((m) => m.causale === "*T") ? moves.map((m) => (m.causale === "*T" ? { ...m, causale: "T*" } : m)) : moves;
}

export const CAUSALE_LABEL: Record<NonNullable<WasteMove["causale"]>, string> = {
  "T*": "ricevuto da terzi",
  NP: "nuovo produttore",
  I: "scarico interno",
  aT: "a terzi",
  RETT: "rettifica",
  ANN: "annullamento",
  DIFF: "differenza di pesata",
};

export type MissingField = "produttore" | "cf-produttore" | "certificato" | "peso" | "carico";

// Dati obbligatori per numerare una registrazione. Con `all` si controlla anche che lo scarico interno
// richiami un carico già numerato.
export function missingFields(m: WasteMove, all?: WasteMove[]): MissingField[] {
  const out: MissingField[] = [];
  if (m.causale === "I" && m.caricoRif && all) {
    const c = all.find((x) => x.id === m.caricoRif);
    if (c && isDraft(c)) out.push("carico");
  }
  if (m.causale === "T*" && m.vfu) {
    if (!m.produttore?.nome?.trim()) out.push("produttore");
    if (!m.produttore?.cf?.trim()) out.push("cf-produttore");
    if (!m.certificato?.numero?.trim()) out.push("certificato");
    if (!m.pesoPesa || !(m.kg > 0)) out.push("peso");
    return out;
  }
  if (m.causale !== "ANN" && !(m.kg > 0)) out.push("peso");
  return out;
}

// Fine del giorno lavorativo n-esimo dopo `iso` (lunedì–venerdì; festività non considerate)
export function workingDaysAfter(iso: string, n: number): string {
  const d = new Date(iso);
  let left = n;
  while (left > 0) {
    d.setDate(d.getDate() + 1);
    const day = d.getDay();
    if (day !== 0 && day !== 6) left--;
  }
  d.setHours(23, 59, 59, 999);
  return d.toISOString();
}

export type IssueCode = "bozza" | "hp-mancanti" | "esito-mancante" | "respinto" | "kg-diversi" | "fir-formato" | "oltre-limite" | "peso-diverso" | "diff-pesata";
export interface Issue {
  code: IssueCode;
  text: string;
  blocking: boolean;
}

export const MISSING_TEXT: Record<MissingField, string> = {
  produttore: "nome di chi conferisce",
  "cf-produttore": "codice fiscale di chi conferisce",
  carico: "registrazione del carico d'ingresso",
  certificato: "certificato di rottamazione",
  peso: "peso della pesa",
};

export const firNumberLooksValid = (n: string) => /^[A-Z]{5}\s?\d{5}\s?[A-Z]{2}$/.test(n.trim().toUpperCase());

// `corrected`: esiste già una rettifica o un annullamento di questa registrazione
export function moveIssues(m: WasteMove, fir?: Fir, corrected = false, all?: WasteMove[]): Issue[] {
  if (isDraft(m)) {
    const miss = missingFields(m, all);
    return [{ code: "bozza", text: miss.length ? `Bozza: manca ${miss.map((x) => MISSING_TEXT[x]).join(", ")}` : "Bozza da confermare", blocking: true }];
  }
  const out: Issue[] = [];
  if (m.verificato) return [];
  // Codice pericoloso senza classi di pericolo: nel formulario RENTRI sono obbligatorie (API formulari, campo
  // caratteristiche_pericolo «richiesta se e solo se il Codice EER si riferisce ad un rifiuto pericoloso»).
  // Nel registro sono facoltative: si avvisa solo finché il mese non è trasmesso; una rettifica le completa.
  if (m.causale !== "ANN" && m.rentri !== "trasmesso" && !corrected && m.eer.trim().endsWith("*") && !m.hp?.length)
    out.push({ code: "hp-mancanti", text: "Codice pericoloso senza classi di pericolo (HP): una rettifica le completa", blocking: false });
  if (m.causale === "T*" && m.pesoPesa && m.kgLibretto && Math.abs(m.kg - m.kgLibretto) / m.kgLibretto > 0.25)
    out.push({ code: "peso-diverso", text: `Pesa ${kgText(m.kg)} kg, libretto ${kgText(m.kgLibretto)} kg: controlla`, blocking: false });
  if (m.causale === "DIFF" && !corrected)
    out.push({ code: "diff-pesata", text: `Differenza di pesata (${m.kind === "carico" ? "+" : "−"}${kgText(m.kg)} kg): verificala`, blocking: false });
  if (m.causale === "aT" && fir) {
    if (!fir.esito) out.push({ code: "esito-mancante", text: "Formulario senza esito del destinatario", blocking: false });
    else if (corrected) {
      /* già rettificata o annullata: niente da segnalare */
    } else if (fir.esito === "respinto") out.push({ code: "respinto", text: "Carico respinto dal destinatario: annulla questo scarico", blocking: false });
    else if (fir.kgAccettati !== undefined && fir.kgAccettati !== fir.kg)
      out.push({ code: "kg-diversi", text: `Accettati ${kgText(fir.kgAccettati)} kg su ${kgText(fir.kg)}: valuta una rettifica`, blocking: false });
    if (fir.numero && !firNumberLooksValid(fir.numero)) out.push({ code: "fir-formato", text: `Numero formulario insolito: ${fir.numero}`, blocking: false });
  }
  return out;
}

export type PeriodStatus = "aperto" | "da trasmettere" | "trasmesso";
export interface Period {
  key: string;
  label: string;
  deadline: string;
  status: PeriodStatus;
  moves: WasteMove[];
  drafts: number;
  duplicates: number; // registrazioni con un numero già usato nello stesso anno (due dispositivi insieme)
  warnings: number;
  ricevuta?: string;
}

// Numeri di registro usati due volte nello stesso anno
export function duplicateIds(moves: WasteMove[]): Set<string> {
  const seen = new Map<string, string[]>();
  for (const m of moves) {
    if (m.numero === undefined || !m.registeredAt) continue;
    const k = `${new Date(m.registeredAt).getFullYear()}-${m.numero}`;
    seen.set(k, [...(seen.get(k) ?? []), m.id]);
  }
  return new Set([...seen.values()].filter((ids) => ids.length > 1).flat());
}

// Registrazioni che hanno già una rettifica o un annullamento
export const correctedIds = (moves: WasteMove[]) => new Set(moves.flatMap((m) => [m.rettificaDi, m.annullaDi]).filter((x): x is string => !!x));

// Kg attuali di una registrazione: quelli dell'ultima rettifica numerata che la richiama, altrimenti i suoi
export function currentKg(moves: WasteMove[], id: string): number | undefined {
  const m = moves.find((x) => x.id === id);
  if (!m) return undefined;
  const rett = moves.filter((x) => x.causale === "RETT" && x.rettificaDi === id && !isDraft(x)).sort((a, b) => (a.numero ?? 0) - (b.numero ?? 0));
  return rett.length ? rett[rett.length - 1].kg : m.kg;
}

// Mese di una registrazione: quello della registrazione; per le bozze quello dell'operazione
export const periodKeyOf = (m: WasteMove) => monthKey(m.registeredAt ?? m.at);

export function periodsOf(moves: WasteMove[], firs: Fir[], now: Date = new Date()): Period[] {
  const current = monthKey(now.toISOString());
  const byKey = new Map<string, WasteMove[]>();
  for (const m of moves) {
    const k = periodKeyOf(m);
    byKey.set(k, [...(byKey.get(k) ?? []), m]);
  }
  const firById = new Map(firs.map((f) => [f.id, f]));
  const dups = duplicateIds(moves);
  const corrected = correctedIds(moves);
  return [...byKey.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, ms]) => {
      const issues = ms.flatMap((m) => moveIssues(m, m.fir ? firById.get(m.fir) : undefined, corrected.has(m.id), moves));
      const registered = ms.filter((m) => !isDraft(m));
      const sent = registered.length > 0 && registered.every((m) => m.rentri === "trasmesso");
      const status: PeriodStatus = key >= current ? "aperto" : sent && !ms.some(isDraft) ? "trasmesso" : "da trasmettere";
      return {
        key,
        label: monthLabel(key),
        deadline: deadlineOf(key),
        status,
        moves: ms,
        drafts: ms.filter(isDraft).length,
        duplicates: ms.filter((m) => dups.has(m.id)).length,
        warnings: issues.filter((i) => !i.blocking).length,
        ricevuta: registered.find((m) => m.rentriRicevuta)?.rentriRicevuta,
      };
    });
}

export const canTransmit = (p: Period) => p.status === "da trasmettere" && p.drafts === 0 && p.duplicates === 0 && p.moves.some((m) => !isDraft(m));

// Carichi, scarichi e giacenza per codice fino alla fine del mese `key`, solo registrazioni numerate.
// Una rettifica sostituisce i kg della registrazione che richiama; un annullamento la toglie.
export function monthStock(moves: WasteMove[], key: string, limits: { code: string; limitKg: number }[]) {
  const registered = moves.filter((m) => !isDraft(m) && periodKeyOf(m) <= key);
  const cancelled = new Set(registered.filter((m) => m.causale === "ANN" && m.annullaDi).map((m) => m.annullaDi!));
  const effective = new Map<string, WasteMove>();
  for (const m of registered) {
    if (m.causale === "ANN" || cancelled.has(m.id)) continue;
    if (m.causale === "RETT" && m.rettificaDi) {
      const orig = effective.get(m.rettificaDi);
      if (orig) effective.set(m.rettificaDi, { ...orig, kg: m.kg });
      continue;
    }
    effective.set(m.id, m);
  }
  const rows = new Map<string, { carichi: number; scarichi: number; giacenza: number }>();
  for (const m of effective.values()) {
    const r = rows.get(m.eer) ?? { carichi: 0, scarichi: 0, giacenza: 0 };
    const inMonth = periodKeyOf(m) === key;
    if (m.kind === "carico") {
      r.giacenza += m.kg;
      if (inMonth) r.carichi += m.kg;
    } else {
      r.giacenza -= m.kg;
      if (inMonth) r.scarichi += m.kg;
    }
    rows.set(m.eer, r);
  }
  const round = (n: number) => Math.round(n * 10) / 10;
  return limits.map((l) => {
    const r = rows.get(l.code) ?? { carichi: 0, scarichi: 0, giacenza: 0 };
    const giacenza = round(r.giacenza);
    return { code: l.code, carichi: round(r.carichi), scarichi: round(r.scarichi), giacenza, limitKg: l.limitKg, over: giacenza > l.limitKg, negative: giacenza < 0 };
  });
}

export function nextRegisterNumber(moves: WasteMove[], atIso: string): number {
  const year = new Date(atIso).getFullYear();
  const nums = moves.filter((m) => m.numero !== undefined && m.registeredAt && new Date(m.registeredAt).getFullYear() === year).map((m) => m.numero!);
  return nums.length ? Math.max(...nums) + 1 : 1;
}

// ——— Termini della bonifica (messa in sicurezza del veicolo fuori uso) ———
// Legge: entro 10 giorni lavorativi dall'ingresso nel centro di raccolta (art. 6 c. 2 lett. a D.Lgs. 209/2003,
// come modificato dal D.Lgs. 119/2020). Obiettivo interno dell'azienda: 7 giorni di calendario.
export const BONIFICA_INTERNO_GIORNI = 7;
export const BONIFICA_LEGGE_GIORNI_LAVORATIVI = 10;

export type BonificaLevel = "ok" | "attenzione" | "oggi" | "scaduta";
export interface BonificaStato {
  days: number; // giorni in parcheggio
  left: number; // giorni rimasti all'obiettivo interno (negativo = superato)
  level: BonificaLevel;
  fuoriLegge: boolean;
  label: string;
  parked: string;
  due: string; // fine del giorno dell'obiettivo interno
  legalDue: string; // fine del 10° giorno lavorativo
}

const giorni = (n: number) => `${n} ${n === 1 ? "giorno" : "giorni"}`;
const dayStart = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
const shortDay = (iso: string) => new Date(iso).toLocaleDateString("it-IT", { weekday: "short", day: "numeric", month: "short" });

export function bonificaStato(intakeIso: string, now: Date = new Date()): BonificaStato {
  const intake = new Date(intakeIso);
  const days = Math.max(0, Math.round((dayStart(now) - dayStart(intake)) / 864e5));
  const left = BONIFICA_INTERNO_GIORNI - days;
  const due = new Date(dayStart(intake) + BONIFICA_INTERNO_GIORNI * 864e5);
  due.setHours(23, 59, 59, 999);
  const legalDue = workingDaysAfter(intakeIso, BONIFICA_LEGGE_GIORNI_LAVORATIVI);
  const fuoriLegge = now.getTime() > new Date(legalDue).getTime();
  const level: BonificaLevel = left < 0 ? "scaduta" : left === 0 ? "oggi" : left <= 2 ? "attenzione" : "ok";
  const label = fuoriLegge
    ? "Bonifica oltre il termine di legge"
    : left < 0
      ? `Oltre i ${BONIFICA_INTERNO_GIORNI} giorni · per legge entro ${shortDay(legalDue)}`
      : left === 0
        ? "Bonifica da fare oggi"
        : `Bonifica entro ${giorni(left)}`;
  return { days, left, level, fuoriLegge, label, parked: days === 0 ? "entrato oggi" : `in parcheggio da ${giorni(days)}`, due: due.toISOString(), legalDue };
}

// Lo stesso formulario (stesso numero, spazi e maiuscole a parte) non si registra due volte
const firKey = (n: string) => n.replace(/\s+/g, "").toUpperCase();
export const firNumberTaken = (firs: Fir[], numero: string) => firs.some((f) => f.numero && firKey(f.numero) === firKey(numero));

// ——— MUD, Comunicazione veicoli fuori uso, Scheda AUT ———
// Il 16 01 04 ricevuto nell'anno va diviso tra veicoli prodotti prima e dopo il 1° gennaio 1980, dove «come anno di
// produzione si intende l'anno di immatricolazione» (DPCM MUD 30/01/2026, Allegato 1, §7.2.1.1).
// Si contano i carichi «ricevuto da terzi» dei veicoli fuori uso, numerati, con rettifiche e annullamenti applicati.
export interface MudVeicoli {
  anno: number;
  veicoli: number;
  totaleKg: number;
  prima1980Kg: number;
  dal1980Kg: number;
  senzaAnno: number; // veicoli senza anno di immatricolazione: da completare prima della dichiarazione
}

export function mudVeicoliRicevuti(moves: WasteMove[], annoDi: (vehicleId: string) => number | undefined, anno: number): MudVeicoli {
  const annullate = new Set(moves.filter((m) => m.causale === "ANN" && !isDraft(m) && m.annullaDi).map((m) => m.annullaDi!));
  const out: MudVeicoli = { anno, veicoli: 0, totaleKg: 0, prima1980Kg: 0, dal1980Kg: 0, senzaAnno: 0 };
  for (const m of moves) {
    if (m.causale !== "T*" || !m.vfu || isDraft(m) || annullate.has(m.id)) continue;
    if (new Date(m.at).getFullYear() !== anno) continue;
    const kg = currentKg(moves, m.id) ?? m.kg;
    const imm = annoDi(m.origin);
    out.veicoli++;
    out.totaleKg += kg;
    if (!imm) out.senzaAnno++;
    else if (imm < 1980) out.prima1980Kg += kg;
    else out.dal1980Kg += kg;
  }
  const r = (n: number) => Math.round(n * 10) / 10;
  return { ...out, totaleKg: r(out.totaleKg), prima1980Kg: r(out.prima1980Kg), dal1980Kg: r(out.dal1980Kg) };
}

// ——— Riga del registro come la vuole il RENTRI ———
// Rettifica e annullamento non sono causali: la rettifica ripete la causale della registrazione che corregge e ne
// indica il numero (numero_registrazione_rettifica), l'annullamento indica il numero di quella annullata
// (numero_registrazione_annullata). Manuale RENTRI del registro, §3.2.5–3.2.6.
// La nostra «differenza di pesata» in più è un carico NP (rifiuto prodotto dal trattamento); quella in meno non ha
// una causale RENTRI: la consulente la registra come rettifica dei carichi stimati.
export interface RigaRentri {
  causale: string;
  rettificaDi?: string; // numero/anno della registrazione rettificata
  annullaDi?: string; // numero/anno della registrazione annullata
  provenienza: "U" | "S";
  nota?: string;
}

const numeroAnno = (m?: WasteMove) => (m?.numero !== undefined ? `${m.numero}/${new Date(m.registeredAt ?? m.at).getFullYear()}` : undefined);

export function rigaRentri(m: WasteMove, all: WasteMove[]): RigaRentri {
  const provenienza = m.provenienza ?? "S";
  const causaleDi = (x: WasteMove | undefined, depth = 0): string => {
    if (!x || depth > 5) return "";
    if (x.causale === "RETT") return causaleDi(all.find((y) => y.id === x.rettificaDi), depth + 1);
    if (x.causale === "DIFF") return x.kind === "carico" ? "NP" : "";
    if (x.causale === "ANN") return "";
    return x.causale ?? "";
  };
  if (m.causale === "ANN") return { causale: "", annullaDi: numeroAnno(all.find((y) => y.id === m.annullaDi)), provenienza };
  if (m.causale === "RETT") return { causale: causaleDi(m), rettificaDi: numeroAnno(all.find((y) => y.id === m.rettificaDi)), provenienza };
  if (m.causale === "DIFF" && m.kind === "scarico")
    return { causale: "", provenienza, nota: "Differenza di pesata in meno: senza causale RENTRI, va registrata come rettifica dei carichi stimati" };
  return { causale: causaleDi(m), provenienza };
}
