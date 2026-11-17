// Credenziali dei collegamenti esterni (Impostazioni → Collegamenti).
// Restano sul server, fuori dall'archivio condiviso con i telefoni: password, token e certificati sono
// cifrati su disco (AES-256-GCM) e non tornano mai al browser, che vede solo se ci sono.
// Chiave: variabile CHIAVE_COLLEGAMENTI (64 caratteri esadecimali) o, se manca, un file generato nella
// cartella dati. Nel prodotto vero la chiave va in un archivio di segreti, non accanto ai dati.
import { connection } from "next/server";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { DATA_DIR } from "@/lib/server-data";
import { servizioById, type StatoServizio } from "@/lib/collegamenti";
import { cifra } from "@/lib/cifratura";

const FILE = path.join(DATA_DIR, "collegamenti.json");
const MAX_FILE = 64 * 1024; // un certificato .p12 pesa pochi KB
const MAX_TEXT = 4000;

interface Salvato {
  valori: Record<string, string | string[]>;
  segreti: Record<string, string>; // cifrati
  file: Record<string, { nome: string; byte: number; dati: string }>; // dati cifrati
  aggiornato?: string;
}
type Archivio = Record<string, Salvato>;

async function load(): Promise<Archivio> {
  try {
    return JSON.parse(await readFile(FILE, "utf8")) as Archivio;
  } catch {
    return {};
  }
}

async function save(a: Archivio) {
  await mkdir(DATA_DIR, { recursive: true });
  await writeFile(FILE, JSON.stringify(a), { mode: 0o600 });
}

function pubblico(s?: Salvato): StatoServizio {
  return {
    valori: s?.valori ?? {},
    segreti: Object.fromEntries(Object.keys(s?.segreti ?? {}).map((k) => [k, true])),
    file: Object.fromEntries(Object.entries(s?.file ?? {}).map(([k, f]) => [k, { nome: f.nome, byte: f.byte }])),
    aggiornato: s?.aggiornato,
  };
}

const json = (body: unknown, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "no-store" } });

export async function GET() {
  await connection();
  const a = await load();
  return json(Object.fromEntries(Object.entries(a).map(([id, s]) => [id, pubblico(s)])));
}

interface Modifica {
  id: string;
  valori?: Record<string, unknown>;
  segreti?: Record<string, unknown>; // solo quelli nuovi; vuoto = invariato
  file?: Record<string, { nome?: unknown; dati?: unknown }>; // dati in base64
  togli?: string[]; // segreti o file da cancellare
}

let lock: Promise<unknown> = Promise.resolve();

export async function PUT(req: Request) {
  const body = (await req.json().catch(() => null)) as Modifica | null;
  const serv = body && servizioById(String(body.id));
  if (!body || !serv) return json({ error: "Servizio sconosciuto" }, 400);
  const campo = (k: string) => serv.campi.find((c) => c.key === k);

  const run = lock.then(async () => {
    const a = await load();
    const s: Salvato = a[serv.id] ?? { valori: {}, segreti: {}, file: {} };

    for (const [k, v] of Object.entries(body.valori ?? {})) {
      const c = campo(k);
      if (!c || c.tipo === "segreto" || c.tipo === "file") continue;
      if (c.tipo === "multipla") {
        if (Array.isArray(v)) s.valori[k] = v.filter((x): x is string => typeof x === "string" && !!c.opzioni?.includes(x));
      } else if (typeof v === "string") {
        if (c.tipo === "scelta" && v && !c.opzioni?.includes(v)) continue;
        s.valori[k] = v.trim().slice(0, MAX_TEXT);
      }
    }
    for (const [k, v] of Object.entries(body.segreti ?? {})) {
      if (campo(k)?.tipo !== "segreto" || typeof v !== "string" || !v) continue;
      s.segreti[k] = await cifra(Buffer.from(v.slice(0, MAX_TEXT), "utf8"));
    }
    for (const [k, f] of Object.entries(body.file ?? {})) {
      if (campo(k)?.tipo !== "file" || typeof f?.dati !== "string") continue;
      const bytes = Buffer.from(f.dati, "base64");
      if (!bytes.length || bytes.length > MAX_FILE) throw new Error("File vuoto o troppo grande (massimo 64 KB)");
      s.file[k] = { nome: String(f.nome ?? "certificato").slice(0, 200), byte: bytes.length, dati: await cifra(bytes) };
    }
    for (const k of body.togli ?? []) {
      delete s.segreti[k];
      delete s.file[k];
    }
    s.aggiornato = new Date().toISOString();
    a[serv.id] = s;
    await save(a);
    return pubblico(s);
  });
  lock = run.catch(() => undefined);
  try {
    return json(await run);
  } catch (e) {
    return json({ error: e instanceof Error ? e.message : "Salvataggio non riuscito" }, 400);
  }
}

// Scollega: cancella tutti i dati salvati del servizio
export async function DELETE(req: Request) {
  const id = new URL(req.url).searchParams.get("id") ?? "";
  if (!servizioById(id)) return json({ error: "Servizio sconosciuto" }, 400);
  const run = lock.then(async () => {
    const a = await load();
    delete a[id];
    await save(a);
  });
  lock = run.catch(() => undefined);
  await run;
  return json({ ok: true });
}
