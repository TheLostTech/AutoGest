// Modifiche rimaste da inviare quando la sessione si chiude (blocco per inattività, "Esci", sessione scaduta).
// Si conservano nel browser accanto alla copia locale dell'azienda e si inviano al prossimo accesso.
// Puro. Quello che si rimanda al server si ricostruisce campo per campo: solo record con id delle liste note e
// contatori numerici. Mai `whole` (regole, listini, magazzini, soggetti: un reset locale li svuoterebbe sul server),
// mai `replace`, mai l'oggetto salvato così com'è (nel browser chiunque può modificarlo).
// Eccezione: una coda con `pagamento: true` (scritture rifiutate con 402, abbonamento non pagato) non scade dopo
// 24 ore: aspetta il pagamento e parte dopo. Il flag resta finché la coda non viene inviata e tolta.

export const IN_SOSPESO_MAX_MS = 86_400_000; // dopo 24 ore una modifica non inviata non si rimanda più

type Rec = Record<string, unknown>;
type Voce = { k: string; r: Rec; at: number };
export type CodaInSospeso = { v: 1; schema: string; voci: Voce[]; counters?: { valori: Contatori; at: number }; pagamento?: true };
export type CorpoRipresa = { schema: string; changes: Record<string, Rec[]>; counters?: Contatori };

const isRec = (x: unknown): x is Rec => !!x && typeof x === "object" && !Array.isArray(x);
const idDi = (r: Rec): string | null => (typeof r.id === "string" && r.id ? r.id : typeof r.typeId === "string" && r.typeId ? r.typeId : null);
const fresco = (at: unknown, ora: number): at is number => typeof at === "number" && Number.isFinite(at) && ora - at < IN_SOSPESO_MAX_MS && at <= ora + 60_000;

export type Contatori = Record<string, number | Record<string, number>>;
const numero = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

// Contatori: numeri, e al massimo un livello annidato di numeri (es. docs: { P, DC, FT, NC }: la numerazione dei
// documenti fiscali, che non va persa). Tutto il resto si scarta.
function numeri(x: unknown): Contatori | null {
  if (!isRec(x)) return null;
  const out: Contatori = {};
  for (const [k, v] of Object.entries(x)) {
    if (numero(v)) out[k] = v;
    else if (isRec(v)) {
      const dentro = Object.fromEntries(Object.entries(v).filter(([, n]) => numero(n))) as Record<string, number>;
      if (Object.keys(dentro).length) out[k] = dentro;
    }
  }
  return Object.keys(out).length ? out : null;
}

// Unione di due serie di contatori: le chiavi annidate si uniscono una per una, vince il valore più recente
function unisciContatori(a: Contatori, b: Contatori): Contatori {
  const out: Contatori = { ...a };
  for (const [k, v] of Object.entries(b)) {
    const prima = out[k];
    out[k] = isRec(v) && isRec(prima) ? { ...prima, ...v } : v;
  }
  return out;
}

/**
 * Legge una coda salvata tenendo solo ciò che ha la forma attesa, è dello schema giusto e ha meno di 24 ore
 * (senza limite di tempo se la coda aspetta il pagamento).
 */
function leggiCoda(raw: unknown, schema: string, ora: number, liste: readonly string[]): CodaInSospeso | null {
  if (!isRec(raw) || raw.v !== 1 || raw.schema !== schema || !Array.isArray(raw.voci)) return null;
  const pagamento = raw.pagamento === true;
  const tieni = (at: unknown): at is number => (pagamento ? numero(at) : fresco(at, ora));
  const voci: Voce[] = [];
  for (const v of raw.voci) {
    if (!isRec(v) || typeof v.k !== "string" || !liste.includes(v.k) || !isRec(v.r) || !idDi(v.r) || !tieni(v.at)) continue;
    voci.push({ k: v.k, r: v.r, at: v.at });
  }
  const c = isRec(raw.counters) && tieni(raw.counters.at) ? numeri(raw.counters.valori) : null;
  return {
    v: 1,
    schema,
    voci,
    ...(c ? { counters: { valori: c, at: (raw.counters as { at: number }).at } } : {}),
    ...(pagamento ? { pagamento: true as const } : {}),
  };
}

/**
 * Unisce alla coda già salvata (se dello stesso schema) le modifiche di adesso: per ogni record vince la copia più recente.
 * Con `{ pagamento: true }` la coda aspetta il pagamento (niente scadenza); una coda che già lo aspetta lo tiene.
 */
export function aggiungiInSospeso(
  prima: unknown,
  schema: string,
  changes: Record<string, unknown[]>,
  counters: unknown,
  ora: number,
  liste: readonly string[],
  opzioni?: { pagamento?: boolean },
): CodaInSospeso {
  const base = leggiCoda(prima, schema, ora, liste) ?? { v: 1 as const, schema, voci: [] };
  const perChiave = new Map(base.voci.map((v) => [`${v.k}\u0000${idDi(v.r)}`, v]));
  for (const [k, righe] of Object.entries(changes)) {
    if (!liste.includes(k) || !Array.isArray(righe)) continue;
    for (const r of righe) {
      if (!isRec(r)) continue;
      const id = idDi(r);
      if (id) perChiave.set(`${k}\u0000${id}`, { k, r, at: ora });
    }
  }
  const c = numeri(counters);
  const cont = c ? { valori: unisciContatori(base.counters?.valori ?? {}, c), at: ora } : base.counters;
  const pagamento = opzioni?.pagamento === true || base.pagamento === true;
  return { v: 1, schema, voci: [...perChiave.values()], ...(cont ? { counters: cont } : {}), ...(pagamento ? { pagamento: true as const } : {}) };
}

/** Il corpo da rimandare al server, ricostruito solo dai campi tipizzati; null se non resta niente. */
export function corpoDaRiprendere(raw: unknown, schema: string, ora: number, liste: readonly string[]): CorpoRipresa | null {
  const coda = leggiCoda(raw, schema, ora, liste);
  if (!coda) return null;
  const changes: Record<string, Rec[]> = {};
  for (const v of coda.voci) (changes[v.k] ??= []).push(v.r);
  if (!coda.voci.length && !coda.counters) return null;
  return { schema, changes, ...(coda.counters ? { counters: coda.counters.valori } : {}) };
}
