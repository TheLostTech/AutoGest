// Avvio della piattaforma (chiamato una volta da instrumentation.ts): tabelle, azienda demo con i suoi utenti,
// passaggio dei dati di prima, primo super admin. Ogni passo si può ripetere senza duplicare nulla.
// Solo server.
import { copyFile, cp, mkdir, stat } from "node:fs/promises";
import path from "node:path";
import type { AuthContext } from "better-auth";
import { getMigrations } from "better-auth/db/migration";
import { auth } from "@/lib/auth/server";
import { creaStatoAzienda } from "@/lib/archivio-azienda";
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

/** Copia (mai sposta) i dati di prima nella cartella dell'azienda demo; quello che c'è già lì non si tocca. */
async function copiaDatiStorici(aziendaId: string): Promise<boolean> {
  const dest = cartellaAzienda(aziendaId);
  await mkdir(dest, { recursive: true });
  let copiato = false;
  const vecchio = path.join(DATA_DIR, "state.json");
  if (!(await esiste(path.join(dest, "state.json"))) && (await esiste(vecchio))) {
    await copyFile(vecchio, path.join(dest, "state.json"));
    copiato = true;
  }
  for (const f of ["collegamenti.json", "ebay.json"]) {
    const da = path.join(DATA_DIR, f);
    if ((await esiste(da)) && !(await esiste(path.join(dest, f)))) await copyFile(da, path.join(dest, f));
  }
  const foto = path.join(DATA_DIR, "foto");
  if (await esiste(foto)) await cp(foto, path.join(dest, "foto"), { recursive: true, force: false, errorOnExist: false });
  return copiato;
}

// L'azienda demo nasce solo su una piattaforma senza aziende; se c'è già (anche a metà di un avvio interrotto) si riprende da lì.
async function aziendaDemo(c: AuthContext): Promise<string | null> {
  const righe = await c.adapter.findMany<{ id: string; metadata?: unknown }>({ model: "organization" });
  const d = righe.find((o) => eDemo(o.metadata));
  if (d) return d.id;
  if (righe.length) return null;
  const o = await creaAzienda(c, "Autodemolizione demo", "demo", true);
  console.log("[avvio] azienda demo creata");
  return o.id;
}

async function utentiDemo(c: AuthContext, aziendaId: string) {
  const membri = await c.adapter.findMany<{ userId: string }>({ model: "member", where: [{ field: "organizationId", value: aziendaId }] });
  const ids = membri.map((m) => m.userId);
  const presenti = ids.length ? await c.adapter.findMany<{ name: string }>({ model: "user", where: [{ field: "id", operator: "in", value: ids }] }) : [];
  const nomi = new Set(presenti.map((u) => u.name));
  let creati = 0;
  for (const u of UTENTI_DEMO) {
    if (nomi.has(u.nome)) continue;
    await creaMembro(c, aziendaId, { nome: u.nome, ruoli: u.ruoli, email: u.email, password: u.password, pin: u.pin });
    creati++;
  }
  if (creati) console.log(`[avvio] utenti demo creati: ${creati}`);
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

export async function avviaPiattaforma(): Promise<void> {
  try {
    const { runMigrations } = await getMigrations(auth.options);
    await runMigrations();
    const c = (await auth.$context) as unknown as AuthContext;

    const demoId = await aziendaDemo(c);
    if (demoId) await preparaDemo(c, demoId);
    await superadmin(c);
    segnaPiattaformaNonPronta(false);
  } catch (e) {
    segnaPiattaformaNonPronta(true);
    console.error("[avvio] avvio della piattaforma non riuscito: le API rispondono 503 finché non si risolve.", e);
  }
}

async function preparaDemo(c: AuthContext, demoId: string) {
  await utentiDemo(c, demoId);
  // Archivio dell'azienda demo: i dati di prima se ci sono, altrimenti lo stato demo scritto qui dal server
  // (non dal primo dispositivo: sulla demo solo un responsabile può sostituire l'archivio).
  if (await copiaDatiStorici(demoId)) console.log("[avvio] dati di prima copiati nell'azienda demo (gli originali restano dove sono)");
  if (!(await esiste(path.join(cartellaAzienda(demoId), "state.json")))) await creaStatoAzienda(demoId, statoDemo());
}
