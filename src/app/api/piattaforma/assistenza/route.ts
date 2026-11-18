// Ingresso e uscita per assistenza. Il super admin non è membro dell'azienda: l'azienda attiva della sessione
// la scrive solo il server (campo non modificabile dal client) e il permesso sta nella riga `assistenza`.
// Un ingresso senza traccia nel registro dell'azienda non deve esistere: se il registro non si scrive, l'ingresso fallisce.
import { superadminDaRichiesta } from "@/lib/accesso/server";
import { ASSISTENZA_MS } from "@/lib/accesso/regole";
import { AVVISO_REGISTRO, aziendaEsiste, contesto, daAltroSito, errore, leggiJson, ok, registra, registraObbligatorio, testo, tokenSessione } from "@/lib/piattaforma/server";

type Riga = { id: string; organizationId: string; scade: unknown; fine?: unknown };
const ms = (d: unknown) => new Date(d as string | number | Date).getTime();

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
  const scade = new Date(ora.getTime() + ASSISTENZA_MS);
  const precedenti = (await c.adapter.findMany<Riga>({ model: "assistenza", where: [{ field: "userId", value: g.utente.id }] })).filter((r) => !r.fine);

  // Prima la riga e la traccia nel registro: se questa non si scrive, l'ingresso non c'è (e quelli precedenti restano com'erano)
  const nuova = await c.adapter.create<Record<string, unknown>, { id: string }>({
    model: "assistenza",
    data: { userId: g.utente.id, organizationId: azienda.id, motivo, inizio: ora, scade },
  });
  try {
    await registraObbligatorio(azienda.id, g.utente.nome, { entity: "sistema", entityId: azienda.id, action: "Ingresso assistenza", detail: motivo });
  } catch (e) {
    console.error("Ingresso assistenza non registrato", azienda.id, e);
    await c.adapter.delete({ model: "assistenza", where: [{ field: "id", value: nuova.id }] }).catch(() => undefined);
    return errore(500, "Non riesco a scrivere l'ingresso nel registro dell'azienda: l'ingresso non è stato fatto. Riprova.");
  }

  // Un solo ingresso aperto alla volta: i precedenti si chiudono, e in ogni azienda lasciata resta l'uscita
  let avviso = false;
  for (const r of precedenti) {
    await c.adapter.update({ model: "assistenza", where: [{ field: "id", value: r.id }], update: { fine: ora } });
    const scaduto = ms(r.scade) <= ora.getTime();
    const scritto = await registra(r.organizationId, g.utente.nome, { entity: "sistema", entityId: r.organizationId, action: "Uscita assistenza", detail: scaduto ? "scaduto" : "ingresso in un'altra azienda" });
    if (!scritto) avviso = true;
  }
  await c.internalAdapter.updateSession(token, { activeOrganizationId: azienda.id });
  return ok({ ok: true, scade: scade.toISOString(), ...(avviso ? { avviso: AVVISO_REGISTRO } : {}) });
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
  const aperte = (await c.adapter.findMany<Riga>({ model: "assistenza", where: [{ field: "userId", value: g.utente.id }] })).filter((r) => !r.fine);
  for (const r of aperte) await c.adapter.update({ model: "assistenza", where: [{ field: "id", value: r.id }], update: { fine: ora } });
  await c.internalAdapter.updateSession(token, { activeOrganizationId: null });
  // L'uscita va nel registro anche se l'ingresso era già scaduto (con la nota)
  let avviso = false;
  for (const r of aperte) {
    const scaduto = ms(r.scade) <= ora.getTime();
    const scritto = await registra(r.organizationId, g.utente.nome, { entity: "sistema", entityId: r.organizationId, action: "Uscita assistenza", ...(scaduto ? { detail: "scaduto" } : {}) });
    if (!scritto) avviso = true;
  }
  return ok(avviso ? { ok: true, avviso: AVVISO_REGISTRO } : { ok: true });
}
