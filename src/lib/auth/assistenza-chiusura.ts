import type { AuthContext } from "better-auth";
import { aggiungiEventi } from "@/lib/archivio-azienda";

// Uscite implicite dall'assistenza: "Esci" dal menu, uscita dalla Piattaforma, sessione chiusa dalla registrazione
// di un dispositivo o dall'attivazione del secondo fattore, sessione scaduta. In ogni caso gli ingressi ancora aperti
// del super admin si chiudono e in ogni azienda resta la riga "Uscita assistenza" (come con il pulsante della fascia).
// Il registro è best-effort qui: l'uscita avviene comunque (non si deve restare dentro per un registro guasto).

type Riga = { id: string; organizationId: string; scade: unknown; fine?: unknown };
const ms = (d: unknown) => new Date(d as string | number | Date).getTime();

export async function chiudiAssistenzeAperte(c: AuthContext, userId: string, dettaglio: string): Promise<void> {
  const aperte = (await c.adapter.findMany<Riga>({ model: "assistenza", where: [{ field: "userId", value: userId }] })).filter((r) => !r.fine);
  if (!aperte.length) return;
  const ora = new Date();
  const utente = await c.adapter.findOne<{ name: string }>({ model: "user", where: [{ field: "id", value: userId }] });
  const nome = utente?.name ?? "Super admin";
  for (const r of aperte) {
    await c.adapter.update({ model: "assistenza", where: [{ field: "id", value: r.id }], update: { fine: ora } });
    const scaduto = ms(r.scade) <= ora.getTime();
    await aggiungiEventi(r.organizationId, [
      { user: `${nome} (assistenza)`, role: "sistema", device: "Piattaforma", entity: "sistema", entityId: r.organizationId, action: "Uscita assistenza", detail: scaduto ? `${dettaglio} (scaduto)` : dettaglio },
    ]).catch((e) => console.error("Uscita assistenza non registrata", r.organizationId, e));
  }
}
