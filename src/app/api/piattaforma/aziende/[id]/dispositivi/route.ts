// Dispositivi dell'azienda dalla scheda azienda: elenco, revoca, sblocco. Solo super admin.
import { connection } from "next/server";
import { superadminDaRichiesta } from "@/lib/accesso/server";
import { inFilaPin } from "@/lib/auth/pin-dispositivo";
import { AVVISO_REGISTRO, aziendaEsiste, contesto, daAltroSito, errore, leggiJson, ok, registra } from "@/lib/piattaforma/server";

type Riga = { id: string; organizationId: string; nome: string; creato: unknown; revocato?: unknown; bloccato?: unknown };
const iso = (d: unknown) => new Date(d as string | number | Date).toISOString();

export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  await connection();
  const g = await superadminDaRichiesta(req);
  if (g instanceof Response) return g;
  const azienda = await aziendaEsiste((await params).id);
  if (!azienda) return errore(404, "Azienda non trovata.");
  const c = await contesto();
  const righe = await c.adapter.findMany<Riga>({ model: "dispositivo", where: [{ field: "organizationId", value: azienda.id }], sortBy: { field: "creato", direction: "desc" } });
  return ok({ dispositivi: righe.map((d) => ({ id: d.id, nome: d.nome, creato: iso(d.creato), revocato: d.revocato ? iso(d.revocato) : null, bloccato: !!d.bloccato })) });
}

export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const g = await superadminDaRichiesta(req);
  if (g instanceof Response) return g;
  const x = daAltroSito(req, true);
  if (x) return x;
  const azienda = await aziendaEsiste((await params).id);
  if (!azienda) return errore(404, "Azienda non trovata.");
  const corpo = await leggiJson(req);
  const c = await contesto();
  const d = typeof corpo?.dispositivoId === "string" ? await c.adapter.findOne<Riga>({ model: "dispositivo", where: [{ field: "id", value: corpo.dispositivoId }] }) : null;
  if (!d || d.organizationId !== azienda.id) return errore(404, "Dispositivo non trovato.");
  let avviso = false;
  const esito = () => ok(avviso ? { ok: true, avviso: AVVISO_REGISTRO } : { ok: true });
  if (corpo?.azione === "revoca") {
    if (!d.revocato) {
      await c.adapter.update({ model: "dispositivo", where: [{ field: "id", value: d.id }], update: { revocato: new Date() } });
      const aperte = await c.adapter.findMany<{ token: string }>({ model: "session", where: [{ field: "dispositivoId", value: d.id }] });
      for (const s of aperte) await c.internalAdapter.deleteSession(s.token);
      avviso = !(await registra(azienda.id, g.utente.nome, { entity: "sistema", entityId: d.id, action: "Dispositivo revocato", detail: d.nome }));
    }
    return esito();
  }
  if (corpo?.azione === "sblocca") {
    if (d.revocato) return errore(400, "Il dispositivo è revocato: va registrato di nuovo.");
    // Nella stessa fila dei tentativi di PIN dell'azienda (come lo sblocco dal responsabile): mai a metà di un tentativo
    await inFilaPin(azienda.id, () => c.adapter.update({ model: "dispositivo", where: [{ field: "id", value: d.id }], update: { bloccato: false, erroriPin: "[]" } }));
    avviso = !(await registra(azienda.id, g.utente.nome, { entity: "sistema", entityId: d.id, action: "Dispositivo sbloccato", detail: d.nome }));
    return esito();
  }
  return errore(400, "Azione non valida.");
}
