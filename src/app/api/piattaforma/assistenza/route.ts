// Ingresso e uscita per assistenza. Il super admin non è membro dell'azienda: l'azienda attiva della sessione
// la scrive solo il server (campo non modificabile dal client) e il permesso sta nella riga `assistenza`.
import { superadminDaRichiesta } from "@/lib/accesso/server";
import { ASSISTENZA_MS } from "@/lib/accesso/regole";
import { aziendaEsiste, contesto, daAltroSito, errore, leggiJson, ok, registra, testo, tokenSessione } from "@/lib/piattaforma/server";

export async function POST(req: Request) {
  const g = await superadminDaRichiesta(req);
  if (g instanceof Response) return g;
  const x = daAltroSito(req, true);
  if (x) return x;
  const corpo = await leggiJson(req);
  const motivo = testo(corpo?.motivo, 3, 300);
  if (!motivo) return errore(400, "Scrivi il motivo dell'ingresso (da 3 a 300 caratteri).");
  const azienda = await aziendaEsiste(corpo?.aziendaId);
  if (!azienda) return errore(404, "Azienda non trovata.");
  const token = await tokenSessione(req);
  if (!token) return errore(401, "Accedi per continuare.", "nessuna-sessione");

  const c = await contesto();
  const ora = new Date();
  // Un solo ingresso aperto alla volta: i precedenti si chiudono
  const aperti = await c.adapter.findMany<{ id: string }>({
    model: "assistenza",
    where: [{ field: "userId", value: g.utente.id }],
  });
  for (const a of aperti) {
    const r = a as { id: string; fine?: unknown };
    if (!r.fine) await c.adapter.update({ model: "assistenza", where: [{ field: "id", value: r.id }], update: { fine: ora } });
  }
  const scade = new Date(ora.getTime() + ASSISTENZA_MS);
  await c.adapter.create({ model: "assistenza", data: { userId: g.utente.id, organizationId: azienda.id, motivo, inizio: ora, scade } });
  await c.internalAdapter.updateSession(token, { activeOrganizationId: azienda.id });
  await registra(azienda.id, g.utente.nome, { entity: "sistema", entityId: azienda.id, action: "Ingresso assistenza", detail: motivo });
  return ok({ ok: true, scade: scade.toISOString() });
}

export async function DELETE(req: Request) {
  const g = await superadminDaRichiesta(req);
  if (g instanceof Response) return g;
  const x = daAltroSito(req, false);
  if (x) return x;
  const token = await tokenSessione(req);
  if (!token) return errore(401, "Accedi per continuare.", "nessuna-sessione");

  const c = await contesto();
  const ora = new Date();
  const righe = await c.adapter.findMany<{ id: string; organizationId: string; scade: unknown; fine?: unknown }>({
    model: "assistenza",
    where: [{ field: "userId", value: g.utente.id }],
  });
  const aperte = righe.filter((r) => !r.fine);
  for (const r of aperte) await c.adapter.update({ model: "assistenza", where: [{ field: "id", value: r.id }], update: { fine: ora } });
  await c.internalAdapter.updateSession(token, { activeOrganizationId: null });
  // Nel registro solo gli ingressi ancora validi: uno già scaduto non fa rumore in un'azienda lasciata da ore
  for (const r of aperte.filter((r) => new Date(r.scade as string | number | Date).getTime() > ora.getTime())) await registra(r.organizationId, g.utente.nome, { entity: "sistema", entityId: r.organizationId, action: "Uscita assistenza" });
  return ok();
}
