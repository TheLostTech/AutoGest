// Creazione di aziende e utenti, per le route del super admin e per l'avvio della piattaforma. Solo server.
import { randomBytes } from "node:crypto";
import type { AuthContext } from "better-auth";
import { ruoliAStringa } from "@/lib/accesso/ruoli";
import { impostaPin } from "@/lib/auth/pin-dispositivo";
import type { Role } from "@/lib/types";

/** Slug unico dell'azienda: il nome senza accenti e simboli, più 6 caratteri a caso. */
export function slugDa(nome: string): string {
  const base = nome.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 40);
  return `${base || "azienda"}-${randomBytes(3).toString("hex")}`;
}

/** Crea l'azienda dall'adapter: nessuno diventa membro (né proprietario). */
export async function creaAzienda(c: AuthContext, nome: string, slug: string, demo: boolean, extra?: Record<string, unknown>): Promise<{ id: string; name: string }> {
  return c.adapter.create<Record<string, unknown>, { id: string; name: string }>({
    model: "organization",
    data: { name: nome, slug, createdAt: new Date(), metadata: JSON.stringify({ demo, ...extra }) },
  });
}

export type NuovoUtente = { nome: string; ruoli: Role[]; email?: string; password?: string; pin?: string };

/**
 * Crea un membro dell'azienda con email+password e/o PIN. Chi entra solo con il PIN ha un'email interna
 * (mai raggiungibile) e nessuna password. Se qualcosa fallisce toglie tutto quello che ha creato e rilancia l'errore.
 */
export async function creaMembro(c: AuthContext, aziendaId: string, n: NuovoUtente, dopo?: (userId: string) => Promise<void>): Promise<string> {
  const conEmail = !!n.email;
  const provvisoria = `nuovo-${randomBytes(8).toString("hex")}@pin.invalid`;
  const utente = await c.internalAdapter.createUser({ name: n.nome, email: conEmail ? n.email! : provvisoria, emailVerified: conEmail ? false : true }, { method: "admin" });
  try {
    if (!conEmail) await c.internalAdapter.updateUser(utente.id, { email: `${utente.id}@pin.invalid` });
    if (conEmail && n.password) {
      await c.internalAdapter.linkAccount({ userId: utente.id, providerId: "credential", accountId: utente.id, password: await c.password.hash(n.password) });
    }
    await c.adapter.create({ model: "member", data: { organizationId: aziendaId, userId: utente.id, role: ruoliAStringa(n.ruoli), createdAt: new Date() } });
    if (n.pin) await impostaPin(c, utente.id, aziendaId, n.pin);
    if (dopo) await dopo(utente.id);
  } catch (e) {
    await c.adapter.delete({ model: "member", where: [{ field: "userId", value: utente.id }] }).catch(() => undefined);
    await c.adapter.delete({ model: "pinUtente", where: [{ field: "userId", value: utente.id }] }).catch(() => undefined);
    await c.adapter.delete({ model: "account", where: [{ field: "userId", value: utente.id }] }).catch(() => undefined);
    await c.adapter.delete({ model: "user", where: [{ field: "id", value: utente.id }] }).catch(() => undefined);
    throw e;
  }
  return utente.id;
}
