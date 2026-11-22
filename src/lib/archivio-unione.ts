// Fusione dei salvataggi dei dispositivi nell'archivio di un'azienda. Puro: nessun accesso a file.
// Collezioni con ID: il server fonde per ID invece di sovrascrivere.
const PREPEND = ["vehicles", "parts", "annunci", "orders", "docs", "firs"] as const; // i nuovi in cima
const APPEND = ["audit", "wasteMoves", "inventory"] as const; // i nuovi in fondo (cronologici)
const WHOLE = ["rules", "listini", "warehouses", "soggetti", "moduli"] as const; // piccole: si sostituiscono intere

export type Rec = Record<string, unknown> & { id?: string; typeId?: string };
export interface Stored {
  schema: string;
  version: number;
  state: Record<string, unknown> | null;
}
export interface Push {
  schema: string;
  replace?: boolean; // ripristino dati demo o primo caricamento
  state?: Record<string, unknown>;
  changes?: Partial<Record<(typeof PREPEND)[number] | (typeof APPEND)[number], Rec[]>>;
  whole?: Partial<Record<(typeof WHOLE)[number], unknown>>;
  counters?: Record<string, unknown>;
}

const keyOf = (r: Rec) => r.id ?? r.typeId ?? "";
// Registro attività e movimenti: due dispositivi possono generare lo stesso numero nello stesso istante,
// quindi la chiave comprende anche l'ora, così nessuna riga va persa
const keyOfLog = (r: Rec) => `${r.id ?? ""}|${String((r as { at?: string }).at ?? "")}`;

export function mergeList(cur: Rec[] = [], changed: Rec[] = [], prepend: boolean, key: (r: Rec) => string = keyOf) {
  const byId = new Map(changed.map((r) => [key(r), r]));
  const next = cur.map((r) => byId.get(key(r)) ?? r);
  const known = new Set(cur.map(key));
  const added = changed.filter((r) => !known.has(key(r)));
  return prepend ? [...added, ...next] : [...next, ...added];
}

// Contatori: vince sempre il più alto, così due dispositivi non riusano lo stesso numero più del necessario
export function maxCounters(a: unknown, b: unknown): unknown {
  if (typeof a === "number" && typeof b === "number") return Math.max(a, b);
  if (a && b && typeof a === "object" && typeof b === "object") {
    const out: Record<string, unknown> = { ...(a as object) };
    for (const [k, v] of Object.entries(b as object)) out[k] = k in out ? maxCounters(out[k], v) : v;
    return out;
  }
  return b ?? a;
}

export function unisciPush(s: Stored, body: Push): Stored {
  if (body.replace || !s.state || s.schema !== body.schema) {
    return { schema: body.schema, version: s.version + 1, state: body.state ?? null };
  }
  const st = { ...s.state };
  for (const k of PREPEND) if (body.changes?.[k]?.length) st[k] = mergeList(st[k] as Rec[], body.changes[k], true);
  for (const k of APPEND) if (body.changes?.[k]?.length) st[k] = mergeList(st[k] as Rec[], body.changes[k], false, k === "inventory" ? keyOf : keyOfLog);
  for (const k of WHOLE) if (body.whole?.[k] !== undefined) st[k] = body.whole[k];
  if (body.counters) st.counters = maxCounters(st.counters, body.counters);
  return { schema: s.schema, version: s.version + 1, state: st };
}

/**
 * Cosa fare con un salvataggio. Sostituire tutto l'archivio (replace, archivio vuoto o schema diverso) è permesso
 * solo sull'azienda demo e solo al responsabile: sulle altre aziende non succede mai da solo (409).
 */
export function esitoPush(cur: Stored, body: Push, ctx: { demo: boolean; responsabile: boolean }): "unisci" | "sostituisci" | 403 | 409 {
  const sostituirebbe = !!body.replace || !cur.state || cur.schema !== body.schema;
  if (!sostituirebbe) return "unisci";
  if (!ctx.demo) return 409;
  return ctx.responsabile ? "sostituisci" : 403;
}
