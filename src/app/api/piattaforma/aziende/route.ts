// Elenco delle aziende e creazione di una nuova. Solo super admin con codice dal telefono verificato.
import { randomBytes } from "node:crypto";
import { connection } from "next/server";
import { superadminDaRichiesta } from "@/lib/accesso/server";
import { creaStatoAzienda } from "@/lib/archivio-azienda";
import { statoVuoto } from "@/lib/stato-iniziale";
import { DEFAULT_LISTINI } from "@/lib/pricing";
import { WAREHOUSES } from "@/lib/warehouse";
import { AVVISO_REGISTRO, contesto, daAltroSito, errore, leggiJson, ok, registra, testo } from "@/lib/piattaforma/server";

export async function GET(req: Request) {
  await connection();
  const g = await superadminDaRichiesta(req);
  if (g instanceof Response) return g;
  const c = await contesto();
  const aziende = await c.adapter.findMany<{ id: string; name: string; createdAt: unknown; metadata?: unknown }>({ model: "organization", sortBy: { field: "createdAt", direction: "asc" } });
  const membri = await c.adapter.findMany<{ userId: string; organizationId: string }>({ model: "member" });
  const righe = [];
  for (const a of aziende) {
    const ids = membri.filter((m) => m.organizationId === a.id).map((m) => m.userId);
    // Ultimo accesso: la sessione più recente dei suoi utenti (niente tabelle nuove)
    const ultima = ids.length
      ? await c.adapter.findMany<{ createdAt: unknown }>({ model: "session", where: [{ field: "userId", operator: "in", value: ids }], sortBy: { field: "createdAt", direction: "desc" }, limit: 1 })
      : [];
    let demo = false;
    try {
      const m = typeof a.metadata === "string" ? JSON.parse(a.metadata) : a.metadata;
      demo = (m as { demo?: unknown } | null)?.demo === true;
    } catch {}
    righe.push({
      id: a.id,
      nome: a.name,
      demo,
      utenti: ids.length,
      ultimoAccesso: ultima[0] ? new Date(ultima[0].createdAt as string | number | Date).toISOString() : null,
    });
  }
  return ok({ aziende: righe });
}

function slugDa(nome: string): string {
  const base = nome.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 40);
  return `${base || "azienda"}-${randomBytes(3).toString("hex")}`;
}

export async function POST(req: Request) {
  const g = await superadminDaRichiesta(req);
  if (g instanceof Response) return g;
  const x = daAltroSito(req, true);
  if (x) return x;
  const corpo = await leggiJson(req);
  const nome = testo(corpo?.nome, 2, 80);
  if (!nome) return errore(400, "Scrivi il nome dell'azienda (da 2 a 80 caratteri).");
  const c = await contesto();
  // Creata dall'adapter: il super admin non diventa mai membro (né proprietario) dell'azienda.
  const org = await c.adapter.create<Record<string, unknown>, { id: string; name: string }>({
    model: "organization",
    data: { name: nome, slug: slugDa(nome), createdAt: new Date(), metadata: JSON.stringify({ demo: false }) },
  });
  // Archivio vuoto: tutte le liste a zero, nessun dato demo
  await creaStatoAzienda(org.id, statoVuoto({ listini: DEFAULT_LISTINI, warehouses: WAREHOUSES }));
  const scritto = await registra(org.id, g.utente.nome, { entity: "sistema", entityId: org.id, action: "Azienda creata", detail: nome });
  return ok({ id: org.id, nome: org.name, ...(scritto ? {} : { avviso: AVVISO_REGISTRO }) }, 201);
}
