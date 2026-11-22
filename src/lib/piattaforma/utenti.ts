// Utenti di un'azienda: le parti comuni alle route della Piattaforma (super admin) e a quelle di Persone (titolare). Solo server.
import { RUOLO_LABEL, ruoliAStringa, ruoliDaStringa } from "@/lib/accesso/ruoli";
import type { Accesso } from "@/lib/accesso/regole";
import type { ModificheIn } from "@/lib/accesso/persone-regole";
import { impostaPin } from "@/lib/auth/pin-dispositivo";
import { aggiungiEventi, type NuovoEvento } from "@/lib/archivio-azienda";
import { FILE_RICHIESTA, leggiFileRichiesta } from "./richieste-file";
import { chiudiSessioni, errore, eSuperadmin, testo, type Contesto } from "./server";
import type { Role } from "@/lib/types";

export type RichiestaIn = { fileId?: string; estremi?: string };

/** Richiesta scritta del corpo: serve almeno un file (già caricato per quest'azienda) o gli estremi. */
export async function richiestaDaCorpo(aziendaId: string, v: unknown, obbligatoria: boolean): Promise<{ richiesta: RichiestaIn | null } | { errore: Response }> {
  const o = v && typeof v === "object" ? (v as Record<string, unknown>) : null;
  const estremi = testo(o?.estremi, 3, 500) ?? undefined;
  const fileId = typeof o?.fileId === "string" && o.fileId ? o.fileId : undefined;
  if (fileId && (!FILE_RICHIESTA.test(fileId) || !(await leggiFileRichiesta(aziendaId, fileId)))) {
    return { errore: errore(400, "Il file della richiesta non c'è: caricalo di nuovo.") };
  }
  if (!fileId && !estremi) {
    return obbligatoria ? { errore: errore(400, "Serve la richiesta scritta dell'azienda: allega il file o scrivi gli estremi (data e chi la firma).", "richiesta") } : { richiesta: null };
  }
  return { richiesta: { ...(fileId ? { fileId } : {}), ...(estremi ? { estremi } : {}) } };
}

export const descrizioneRichiesta = (r: RichiestaIn | null) => (r ? [r.estremi, r.fileId ? "file allegato" : ""].filter(Boolean).join(" + ") : "nessuna");

export type RigaMembro = { id: string; nome: string; email: string | null; ruoli: Role[]; conPassword: boolean; conPin: boolean; attivo: boolean };

/** Le persone dell'azienda, per nome. Mai hash di password o PIN; chi entra solo col PIN ha `email: null` (l'email interna non esce). */
export async function righeMembri(c: Contesto, aziendaId: string): Promise<RigaMembro[]> {
  const membri = await c.adapter.findMany<{ userId: string; role: string }>({ model: "member", where: [{ field: "organizationId", value: aziendaId }] });
  const ids = membri.map((m) => m.userId);
  const utenti = ids.length ? await c.adapter.findMany<{ id: string; name: string; email: string; banned?: boolean | null }>({ model: "user", where: [{ field: "id", operator: "in", value: ids }] }) : [];
  const conti = ids.length ? await c.adapter.findMany<{ userId: string; providerId: string }>({ model: "account", where: [{ field: "userId", operator: "in", value: ids }] }) : [];
  const pin = await c.adapter.findMany<{ userId: string }>({ model: "pinUtente", where: [{ field: "organizationId", value: aziendaId }] });
  return membri
    .map((m) => {
      const u = utenti.find((x) => x.id === m.userId);
      if (!u) return null;
      return {
        id: u.id,
        nome: u.name,
        email: u.email.endsWith("@pin.invalid") ? null : u.email,
        ruoli: ruoliDaStringa(m.role),
        conPassword: conti.some((a) => a.userId === u.id && a.providerId === "credential"),
        conPin: pin.some((p) => p.userId === u.id),
        attivo: !u.banned,
      };
    })
    .filter((x) => x !== null)
    .sort((a, b) => a.nome.localeCompare(b.nome, "it"));
}

export type MembroTrovato = { aziendaId: string; membro: { id: string; role: string }; utente: { id: string; name: string; role?: string | null } };

/** L'utente se è membro di quell'azienda, altrimenti null: le route rispondono 404, come se non esistesse. */
export async function membroDellAzienda(c: Contesto, aziendaId: string, userId: string): Promise<MembroTrovato | null> {
  const membro = await c.adapter.findOne<{ id: string; role: string }>({
    model: "member",
    where: [
      { field: "userId", value: userId },
      { field: "organizationId", value: aziendaId },
    ],
  });
  const utente = membro ? await c.internalAdapter.findUserById(userId) : null;
  return membro && utente ? { aziendaId, membro, utente: utente as MembroTrovato["utente"] } : null;
}

/** Un super admin non si modifica dalle schermate delle aziende. */
export const utenteSuperadmin = (t: MembroTrovato) => eSuperadmin(t.utente.role);

/**
 * Applica le modifiche già controllate (modificheDaCorpo): ruoli, PIN, password, attivo o sospeso.
 * Ogni passo chiama `traccia(azione, dettaglio)` per il registro. Se ruoli, PIN, password o sospensione sono stati
 * toccati (anche a metà), le sessioni aperte della persona si chiudono. Risponde null se è andato tutto bene.
 */
export async function applicaModifiche(
  c: Contesto,
  t: MembroTrovato,
  cambi: ModificheIn,
  o: { emailUsata: string; motivoSospensione: string; traccia: (azione: string, dettaglio: string) => Promise<void> },
): Promise<Response | null> {
  const userId = t.utente.id;
  const conto = await c.adapter.findOne<{ id: string }>({
    model: "account",
    where: [
      { field: "userId", value: userId },
      { field: "providerId", value: "credential" },
    ],
  });
  if (cambi.password !== undefined && !conto) {
    if (!cambi.email) return errore(400, "Questa persona entra solo con il PIN: per darle una password scrivi anche un'email.", "email");
    if (await c.internalAdapter.findUserByEmail(cambi.email)) return errore(409, o.emailUsata);
  }

  // Si segna PRIMA di ogni modifica: se un passo fallisce a metà, le sessioni si chiudono comunque (finally)
  let chiudi = false;
  try {
    if (cambi.ruoli) {
      const prima = ruoliDaStringa(t.membro.role);
      chiudi = true;
      await c.adapter.update({ model: "member", where: [{ field: "id", value: t.membro.id }], update: { role: ruoliAStringa(cambi.ruoli) } });
      await o.traccia("Ruoli cambiati", `${t.utente.name} · da ${prima.map((x) => RUOLO_LABEL[x]).join(", ") || "nessuno"} a ${cambi.ruoli.map((x) => RUOLO_LABEL[x]).join(", ")}`);
    }
    if (cambi.pin !== undefined) {
      chiudi = true;
      await impostaPin(c, userId, t.aziendaId, cambi.pin);
      await o.traccia("PIN reimpostato", t.utente.name);
    }
    if (cambi.password !== undefined) {
      chiudi = true;
      const hash = await c.password.hash(cambi.password);
      if (conto) await c.internalAdapter.updatePassword(userId, hash);
      else {
        await c.internalAdapter.updateUser(userId, { email: cambi.email!, emailVerified: false });
        await c.internalAdapter.linkAccount({ userId, providerId: "credential", accountId: userId, password: hash });
      }
      await o.traccia(conto ? "Password reimpostata" : "Accesso con email attivato", t.utente.name);
    }
    if (cambi.attivo !== undefined) {
      if (!cambi.attivo) chiudi = true;
      await c.internalAdapter.updateUser(userId, cambi.attivo ? { banned: false, banReason: null, banExpires: null } : { banned: true, banReason: o.motivoSospensione, banExpires: null });
      await o.traccia(cambi.attivo ? "Utente riattivato" : "Utente disattivato", t.utente.name);
    }
  } catch (e) {
    console.error("Modifica utente non completata", userId, e);
    return errore(500, "La modifica non è stata completata del tutto: controlla la scheda. Le sessioni aperte della persona sono state chiuse.");
  } finally {
    // Ruoli, PIN, password o sospensione toccati (anche a metà): le sessioni aperte non valgono più
    if (chiudi) await chiudiSessioni(c, userId);
  }
  return null;
}

/** "email e password", "PIN" o tutti e due: per il dettaglio della riga "Utente creato". */
export const descrizioneAccesso = (n: { email?: string; pin?: string }) => [n.email ? "email e password" : "", n.pin ? "PIN" : ""].filter(Boolean).join(" + ");

/** Una riga nel registro attività firmata da chi è entrato nell'azienda (il titolare, o il super admin in assistenza). Best-effort. */
export async function registraDaAccesso(a: Accesso, e: Omit<NuovoEvento, "user" | "role" | "device">): Promise<boolean> {
  try {
    await aggiungiEventi(a.azienda.id, [{ user: a.assistenza ? `${a.utente.nome} (assistenza)` : a.utente.nome, role: "responsabile", device: a.dispositivo?.nome || "Browser", ...e }]);
    return true;
  } catch (err) {
    console.error("Registro attività non aggiornato", a.azienda.id, err);
    return false;
  }
}
