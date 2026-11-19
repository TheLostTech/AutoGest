// Archivio condiviso della demo: tiene allineati telefoni e computer collegati allo stesso server.
// Solo per il prototipo: un file JSON sul Mac. Nel prodotto vero questo diventa il database centrale.
import { connection } from "next/server";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { DATA_DIR } from "@/lib/server-data";

const DIR = DATA_DIR;
const FILE = path.join(DIR, "state.json");

// Collezioni con ID: il server fonde per ID invece di sovrascrivere
const PREPEND = ["vehicles", "parts", "annunci", "orders", "docs", "firs"] as const; // i nuovi in cima
const APPEND = ["audit", "wasteMoves", "inventory"] as const; // i nuovi in fondo (cronologici)
const WHOLE = ["rules", "listini", "warehouses", "soggetti", "moduli"] as const; // piccole: si sostituiscono intere

type Rec = Record<string, unknown> & { id?: string; typeId?: string };
interface Stored {
  schema: string;
  version: number;
  state: Record<string, unknown> | null;
}
interface Push {
  schema: string;
  replace?: boolean; // ripristino dati demo o primo caricamento
  state?: Record<string, unknown>;
  changes?: Partial<Record<(typeof PREPEND)[number] | (typeof APPEND)[number], Rec[]>>;
  whole?: Partial<Record<(typeof WHOLE)[number], unknown>>;
  counters?: Record<string, unknown>;
}

let lock: Promise<unknown> = Promise.resolve();

// Sempre dal file: anche altri server sullo stesso Mac (es. :3210 e :3211) leggono e scrivono qui
async function load(): Promise<Stored> {
  try {
    return JSON.parse(await readFile(FILE, "utf8")) as Stored;
  } catch {
    return { schema: "", version: 0, state: null };
  }
}

async function save(s: Stored) {
  await mkdir(DIR, { recursive: true });
  await writeFile(FILE, JSON.stringify(s));
  return s;
}

const keyOf = (r: Rec) => r.id ?? r.typeId ?? "";
// Registro attività e movimenti: due dispositivi possono generare lo stesso numero nello stesso istante,
// quindi la chiave comprende anche l'ora, così nessuna riga va persa
const keyOfLog = (r: Rec) => `${r.id ?? ""}|${String((r as { at?: string }).at ?? "")}`;

function mergeList(cur: Rec[] = [], changed: Rec[] = [], prepend: boolean, key: (r: Rec) => string = keyOf) {
  const byId = new Map(changed.map((r) => [key(r), r]));
  const next = cur.map((r) => byId.get(key(r)) ?? r);
  const known = new Set(cur.map(key));
  const added = changed.filter((r) => !known.has(key(r)));
  return prepend ? [...added, ...next] : [...next, ...added];
}

// Contatori: vince sempre il più alto, così due dispositivi non riusano lo stesso numero più del necessario
function maxCounters(a: unknown, b: unknown): unknown {
  if (typeof a === "number" && typeof b === "number") return Math.max(a, b);
  if (a && b && typeof a === "object" && typeof b === "object") {
    const out: Record<string, unknown> = { ...(a as object) };
    for (const [k, v] of Object.entries(b as object)) out[k] = k in out ? maxCounters(out[k], v) : v;
    return out;
  }
  return b ?? a;
}

export async function GET() {
  await connection();
  const s = await load();
  return Response.json(s, { headers: { "Cache-Control": "no-store" } });
}

export async function PUT(req: Request) {
  const body = (await req.json()) as Push;
  const run = lock.then(async () => {
    const s = await load();
    if (body.replace || !s.state || s.schema !== body.schema) {
      return save({ schema: body.schema, version: s.version + 1, state: body.state ?? null });
    }
    const st = { ...s.state };
    for (const k of PREPEND) if (body.changes?.[k]?.length) st[k] = mergeList(st[k] as Rec[], body.changes[k], true);
    for (const k of APPEND) if (body.changes?.[k]?.length) st[k] = mergeList(st[k] as Rec[], body.changes[k], false, k === "inventory" ? keyOf : keyOfLog);
    for (const k of WHOLE) if (body.whole?.[k] !== undefined) st[k] = body.whole[k];
    if (body.counters) st.counters = maxCounters(st.counters, body.counters);
    return save({ schema: s.schema, version: s.version + 1, state: st });
  });
  lock = run.catch(() => undefined);
  const s = await run;
  return Response.json({ version: s.version, schema: s.schema }, { headers: { "Cache-Control": "no-store" } });
}
