// Avvio della piattaforma (chiamato una volta da instrumentation.ts): tabelle, azienda demo con i suoi utenti,
// passaggio dei dati di prima, primo super admin. Ogni passo si può ripetere senza duplicare nulla.
// Con il deposito Supabase (cloud) solo tabelle (Better Auth e dati) e super admin: niente azienda demo, niente dati
// di prima, nessun file scritto (il disco non c'è o non è condiviso tra le istanze).
// Solo server.
import { randomBytes, randomInt } from "node:crypto";
import { copyFile, cp, mkdir, readFile, rename, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import type { AuthContext } from "better-auth";
import { getMigrations } from "better-auth/db/migration";
import { symmetricDecrypt, symmetricEncrypt } from "better-auth/crypto";
import { SEGRETO_DI_PROVA } from "@/lib/auth/segreto";
import { auth } from "@/lib/auth/server";
import { creaStatoAzienda } from "@/lib/archivio-azienda";
import { pool } from "@/lib/db/pool";
import { preparaSchema } from "@/lib/db/schema";
import { sceltaDeposito } from "@/lib/deposito";
import { DEFAULT_LISTINI } from "@/lib/pricing";
import { buildSeed } from "@/lib/seed";
import { DATA_DIR, cartellaAzienda } from "@/lib/server-data";
import { WAREHOUSES } from "@/lib/warehouse";
import { creaAzienda, creaMembro } from "@/lib/piattaforma/crea";
import { segnaPiattaformaNonPronta } from "./pronta";
import { UTENTI_DEMO } from "./demo-utenti";

const eDemo = (metadata: unknown): boolean => {
  try {
    const m = typeof metadata === "string" ? JSON.parse(metadata) : metadata;
    return typeof m === "object" && m !== null && (m as { demo?: unknown }).demo === true;
  } catch {
    return false;
  }
};

const esiste = (p: string) => stat(p).then(() => true, () => false);

// Stesso contenuto che produce initial() nello store: dati demo, listini e magazzini di serie.
function statoDemo(): Record<string, unknown> {
  const s = buildSeed();
  return {
    vehicles: s.vehicles,
    parts: s.parts,
    annunci: s.annunci,
    orders: s.orders,
    audit: s.audit,
    rules: s.rules,
    wasteMoves: s.wasteMoves,
    firs: s.firs,
    soggetti: s.soggetti,
    docs: s.docs,
    inventory: s.inventory,
    listini: DEFAULT_LISTINI,
    warehouses: WAREHOUSES,
    counters: s.counters,
  };
}

const MARCATORE = ".passaggio-fatto";

/**
 * Copia (mai sposta) i dati di prima nella cartella dell'azienda demo. Si fa una volta sola, nella prima preparazione:
 * a copia finita si scrive il marcatore, e da quel momento nulla viene più ricopiato (foto tolte, archivio tolto, ecc.).
 */
async function copiaDatiStorici(aziendaId: string): Promise<boolean> {
  const dest = cartellaAzienda(aziendaId);
  await mkdir(dest, { recursive: true });
  if (await esiste(path.join(dest, MARCATORE))) return false;
  let copiato = false;
  const vecchio = path.join(DATA_DIR, "state.json");
  if (!(await esiste(path.join(dest, "state.json"))) && (await esiste(vecchio))) {
    // File temporaneo + rinomina: un arresto a metà non lascia un archivio tronco
    const tmp = path.join(dest, `state.json.${process.pid}.tmp`);
    await copyFile(vecchio, tmp);
    await rename(tmp, path.join(dest, "state.json"));
    copiato = true;
  }
  for (const f of ["collegamenti.json", "ebay.json"]) {
    const da = path.join(DATA_DIR, f);
    if ((await esiste(da)) && !(await esiste(path.join(dest, f)))) await copyFile(da, path.join(dest, f));
  }
  // Foto e PDF delle visure PRA (questi ultimi dalla visura vera arrivata prima del login)
  for (const d of ["foto", "visure"]) {
    const da = path.join(DATA_DIR, d);
    if (await esiste(da)) await cp(da, path.join(dest, d), { recursive: true, force: false, errorOnExist: false });
  }
  await writeFile(path.join(dest, MARCATORE), new Date().toISOString());
  return copiato;
}

type Credenziali = Record<string, { password?: string; pin?: string }>;
const FILE_CREDENZIALI = () => path.join(DATA_DIR, "credenziali-demo.json");

// Valori casuali per gli utenti demo, scritti in un file solo per il proprietario. Se il file c'è già non si rigenera.
async function credenzialiDemo(): Promise<Credenziali> {
  try {
    return JSON.parse(await readFile(FILE_CREDENZIALI(), "utf8")) as Credenziali;
  } catch {}
  const cred: Credenziali = {};
  for (const u of UTENTI_DEMO) {
    cred[u.nome] = {
      ...(u.email ? { email: u.email, password: randomBytes(18).toString("base64url") } : {}),
      ...(u.conPin ? { pin: String(randomInt(0, 10000)).padStart(4, "0") } : {}),
    } as Credenziali[string];
  }
  await writeFile(FILE_CREDENZIALI(), JSON.stringify(cred, null, 2), { mode: 0o600, flag: "wx" });
  return cred;
}

async function aziendaDemo(c: AuthContext): Promise<{ id: string; preparata: boolean } | null> {
  const righe = await c.adapter.findMany<{ id: string; metadata?: unknown }>({ model: "organization" });
  const d = righe.find((o) => eDemo(o.metadata));
  if (d) {
    let preparata = false;
    try {
      const m = typeof d.metadata === "string" ? JSON.parse(d.metadata) : d.metadata;
      preparata = (m as { preparata?: unknown } | null)?.preparata === true;
    } catch {}
    return { id: d.id, preparata };
  }
  if (righe.length) return null; // ci sono altre aziende ma nessuna demo: non se ne crea una
  const o = await creaAzienda(c, "Autodemolizione demo", "demo", true);
  console.log("[avvio] azienda demo creata");
  return { id: o.id, preparata: false };
}

// Un utente rimasto a metà dopo un arresto (senza appartenenza all'azienda) si toglie prima di ricrearlo.
async function togliOrfano(c: AuthContext, filtro: { field: string; value: string }) {
  const u = await c.adapter.findOne<{ id: string }>({ model: "user", where: [filtro] });
  if (!u) return;
  const m = await c.adapter.findOne<{ id: string }>({ model: "member", where: [{ field: "userId", value: u.id }] });
  if (m) return;
  for (const model of ["pinUtente", "account", "session"]) await c.adapter.deleteMany({ model, where: [{ field: "userId", value: u.id }] }).catch(() => undefined);
  await c.adapter.delete({ model: "user", where: [{ field: "id", value: u.id }] });
}

async function utentiDemo(c: AuthContext, aziendaId: string) {
  if (process.env.NODE_ENV === "production" && process.env.DEMO_UTENTI !== "1") {
    console.log("[avvio] produzione: utenti demo non creati (servirebbe DEMO_UTENTI=1)");
    return;
  }
  const cred = await credenzialiDemo();
  // Solo nella prima preparazione: chi è già presente (preparazione interrotta e ripresa) non si ricrea
  const membri = await c.adapter.findMany<{ userId: string }>({ model: "member", where: [{ field: "organizationId", value: aziendaId }] });
  const ids = membri.map((m) => m.userId);
  const presenti = ids.length ? await c.adapter.findMany<{ name: string }>({ model: "user", where: [{ field: "id", operator: "in", value: ids }] }) : [];
  const nomi = new Set(presenti.map((u) => u.name));
  let creati = 0;
  for (const u of UTENTI_DEMO) {
    if (nomi.has(u.nome)) continue;
    if (u.email) await togliOrfano(c, { field: "email", value: u.email });
    const k = cred[u.nome] ?? {};
    await creaMembro(c, aziendaId, { nome: u.nome, ruoli: u.ruoli, email: u.email, password: u.email ? k.password : undefined, pin: u.conPin ? k.pin : undefined });
    creati++;
  }
  if (creati) console.log(`[avvio] utenti demo creati: ${creati} (valori in ${path.basename(FILE_CREDENZIALI())})`);
}

async function superadmin(c: AuthContext) {
  const email = process.env.SUPERADMIN_EMAIL?.trim().toLowerCase();
  if (!email) return;
  const esistenti = await c.adapter.findMany<{ id: string }>({ model: "user", where: [{ field: "role", value: "superadmin" }], limit: 1 });
  if (esistenti.length) return;
  const password = process.env.SUPERADMIN_PASSWORD ?? "";
  if (password.length < 8 || password.length > 128) {
    console.error("[avvio] SUPERADMIN_EMAIL c'è ma SUPERADMIN_PASSWORD manca o non è di almeno 8 caratteri: super admin non creato.");
    return;
  }
  if (await c.internalAdapter.findUserByEmail(email)) {
    console.error("[avvio] l'email di SUPERADMIN_EMAIL è già di un altro utente: super admin non creato.");
    return;
  }
  const nome = process.env.SUPERADMIN_NOME?.trim() || "Amministratore";
  const u = await c.internalAdapter.createUser({ name: nome, email, emailVerified: true, role: "superadmin" } as never, { method: "admin" });
  try {
    await c.internalAdapter.linkAccount({ userId: u.id, providerId: "credential", accountId: u.id, password: await c.password.hash(password) });
  } catch (e) {
    await c.adapter.delete({ model: "user", where: [{ field: "id", value: u.id }] }).catch(() => undefined);
    throw e;
  }
  console.log("[avvio] super admin creato");
}

// Codici del secondo fattore salvati quando il segreto era ancora il valore di prova di Better Auth (prima di segreto.ts):
// si ricifrano con il segreto vero, altrimenti il super admin non potrebbe più entrare. Ogni avvio, senza effetti se già fatto.
async function ricifraDueFattori(c: AuthContext) {
  const segreto = c.secretConfig;
  if (typeof segreto !== "string" || segreto === SEGRETO_DI_PROVA) return;
  const righe = await c.adapter.findMany<{ id: string; secret: string }>({ model: "twoFactor" });
  for (const r of righe) {
    if (typeof r.secret !== "string" || !r.secret) continue;
    const giaBuono = await symmetricDecrypt({ key: segreto, data: r.secret }).then(() => true, () => false);
    if (giaBuono) continue;
    const chiaro = await symmetricDecrypt({ key: SEGRETO_DI_PROVA, data: r.secret }).catch(() => null);
    if (chiaro === null) {
      console.error("[avvio] codice del secondo fattore non leggibile (segreto cambiato?): l'utente dovrà riattivarlo.");
      continue;
    }
    await c.adapter.update({ model: "twoFactor", where: [{ field: "id", value: r.id }], update: { secret: await symmetricEncrypt({ key: segreto, data: chiaro }) } });
    console.log("[avvio] codice del secondo fattore ricifrato con il segreto della cartella dati");
  }
}

export async function avviaPiattaforma(): Promise<void> {
  try {
    const { runMigrations } = await getMigrations(auth.options);
    await runMigrations();
    const c = (await auth.$context) as unknown as AuthContext;
    await ricifraDueFattori(c);

    if (sceltaDeposito(process.env) === "supabase") {
      await preparaSchema(pool());
    } else {
      const demo = await aziendaDemo(c);
      if (demo && !demo.preparata) await preparaDemo(c, demo.id);
    }
    await superadmin(c);
    segnaPiattaformaNonPronta(false);
  } catch (e) {
    segnaPiattaformaNonPronta(true);
    console.error("[avvio] avvio della piattaforma non riuscito: le API rispondono 503 finché non si risolve.", e);
  }
}

// Prima preparazione dell'azienda demo: utenti, dati di prima, archivio. Alla fine il marcatore nei metadati dell'azienda:
// dai avvii dopo non si tocca più nulla (un utente o una foto tolti non tornano).
async function preparaDemo(c: AuthContext, demoId: string) {
  await utentiDemo(c, demoId);
  // Archivio dell'azienda demo: i dati di prima se ci sono, altrimenti lo stato demo scritto qui dal server
  // (non dal primo dispositivo: sulla demo solo un responsabile può sostituire l'archivio).
  if (await copiaDatiStorici(demoId)) console.log("[avvio] dati di prima copiati nell'azienda demo (gli originali restano dove sono)");
  if (!(await esiste(path.join(cartellaAzienda(demoId), "state.json")))) await creaStatoAzienda(demoId, statoDemo());
  await c.adapter.update({ model: "organization", where: [{ field: "id", value: demoId }], update: { metadata: JSON.stringify({ demo: true, preparata: true }) } });
}
