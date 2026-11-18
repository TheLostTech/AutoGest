// Modifica di un utente: ruoli, PIN, password, disattivazione. Solo super admin; ogni modifica va nel registro dell'azienda.
import { superadminDaRichiesta } from "@/lib/accesso/server";
import { RUOLO_LABEL, ruoliAStringa, ruoliDaStringa } from "@/lib/accesso/ruoli";
import { pinValido } from "@/lib/accesso/pin";
import { richiestaObbligatoria } from "@/lib/accesso/richieste";
import { impostaPin } from "@/lib/auth/pin-dispositivo";
import { aggiungiRichiesta } from "@/lib/piattaforma/richieste-file";
import { chiudiSessioni, contesto, daAltroSito, errore, eSuperadmin, leggiJson, ok, registra, aziendaEsiste } from "@/lib/piattaforma/server";
import { descrizioneRichiesta, EMAIL, richiestaDaCorpo, ruoliDaCorpo } from "@/lib/piattaforma/utenti";

export async function PATCH(req: Request, { params }: { params: Promise<{ userId: string }> }) {
  const g = await superadminDaRichiesta(req);
  if (g instanceof Response) return g;
  const x = daAltroSito(req, true);
  if (x) return x;
  const { userId } = await params;
  const corpo = await leggiJson(req);
  if (!corpo) return errore(400, "Richiesta non valida.");
  const azienda = await aziendaEsiste(corpo.aziendaId);
  if (!azienda) return errore(404, "Azienda non trovata.");

  const c = await contesto();
  // L'utente deve essere di quell'azienda; altrimenti risponde come se non esistesse
  const membro = await c.adapter.findOne<{ id: string; role: string }>({
    model: "member",
    where: [
      { field: "userId", value: userId },
      { field: "organizationId", value: azienda.id },
    ],
  });
  const utente = membro ? await c.internalAdapter.findUserById(userId) : null;
  if (!membro || !utente) return errore(404, "Utente non trovato.");
  if (eSuperadmin((utente as { role?: string | null }).role)) return errore(403, "Questo utente non si modifica da qui.");

  const nuoviRuoli = corpo.ruoli !== undefined ? ruoliDaCorpo(corpo.ruoli) : null;
  if (corpo.ruoli !== undefined && !nuoviRuoli) return errore(400, "Scegli almeno un ruolo valido.");
  if (corpo.pin !== undefined && (typeof corpo.pin !== "string" || !pinValido(corpo.pin))) return errore(400, "Il PIN è di 4 cifre.");
  if (corpo.password !== undefined && (typeof corpo.password !== "string" || corpo.password.length < 8 || corpo.password.length > 128)) {
    return errore(400, "La password deve avere almeno 8 caratteri.");
  }
  if (corpo.attivo !== undefined && typeof corpo.attivo !== "boolean") return errore(400, "Richiesta non valida.");
  const emailNuova = typeof corpo.email === "string" && corpo.email.trim() ? corpo.email.trim().toLowerCase() : "";
  if (emailNuova && !EMAIL.test(emailNuova)) return errore(400, "Email non valida.");
  if (nuoviRuoli === null && corpo.pin === undefined && corpo.password === undefined && corpo.attivo === undefined) return errore(400, "Niente da modificare.");

  // Richiesta scritta: obbligatoria per cambiare i ruoli, facoltativa per il resto
  const r = await richiestaDaCorpo(azienda.id, corpo.richiesta, !!nuoviRuoli && richiestaObbligatoria("ruoli"));
  if ("errore" in r) return r.errore;

  const conto = await c.adapter.findOne<{ id: string }>({
    model: "account",
    where: [
      { field: "userId", value: userId },
      { field: "providerId", value: "credential" },
    ],
  });
  if (corpo.password !== undefined && !conto) {
    if (!emailNuova) return errore(400, "Questa persona entra solo con il PIN: per darle una password scrivi anche un'email.", "email");
    if (await c.internalAdapter.findUserByEmail(emailNuova)) return errore(409, "Esiste già una persona con questa email.");
  }

  const nome = g.utente.nome;
  const quando = new Date().toISOString();
  const traccia = async (azione: string) => {
    if (r.richiesta) await aggiungiRichiesta(azienda.id, { userId, azione, quando, autore: nome, ...r.richiesta });
  };
  let chiudi = false;

  if (nuoviRuoli) {
    const prima = ruoliDaStringa(membro.role);
    await c.adapter.update({ model: "member", where: [{ field: "id", value: membro.id }], update: { role: ruoliAStringa(nuoviRuoli) } });
    await traccia("Ruoli cambiati");
    await registra(azienda.id, nome, {
      entity: "utente",
      entityId: userId,
      action: "Ruoli cambiati",
      detail: `${utente.name} · da ${prima.map((x) => RUOLO_LABEL[x]).join(", ") || "nessuno"} a ${nuoviRuoli.map((x) => RUOLO_LABEL[x]).join(", ")} · richiesta: ${descrizioneRichiesta(r.richiesta)}`,
    });
    chiudi = true;
  }
  if (typeof corpo.pin === "string") {
    await impostaPin(c, userId, azienda.id, corpo.pin);
    await traccia("PIN reimpostato");
    await registra(azienda.id, nome, { entity: "utente", entityId: userId, action: "PIN reimpostato", detail: `${utente.name} · richiesta: ${descrizioneRichiesta(r.richiesta)}` });
    chiudi = true;
  }
  if (typeof corpo.password === "string") {
    const hash = await c.password.hash(corpo.password);
    if (conto) await c.internalAdapter.updatePassword(userId, hash);
    else {
      await c.internalAdapter.updateUser(userId, { email: emailNuova, emailVerified: false });
      await c.internalAdapter.linkAccount({ userId, providerId: "credential", accountId: userId, password: hash });
    }
    await traccia(conto ? "Password reimpostata" : "Accesso con email attivato");
    await registra(azienda.id, nome, {
      entity: "utente",
      entityId: userId,
      action: conto ? "Password reimpostata" : "Accesso con email attivato",
      detail: `${utente.name} · richiesta: ${descrizioneRichiesta(r.richiesta)}`,
    });
    chiudi = true;
  }
  if (typeof corpo.attivo === "boolean") {
    const attivo = corpo.attivo;
    await c.internalAdapter.updateUser(userId, attivo ? { banned: false, banReason: null, banExpires: null } : { banned: true, banReason: "Disattivato dalla piattaforma", banExpires: null });
    await traccia(attivo ? "Utente riattivato" : "Utente disattivato");
    await registra(azienda.id, nome, { entity: "utente", entityId: userId, action: attivo ? "Utente riattivato" : "Utente disattivato", detail: `${utente.name} · richiesta: ${descrizioneRichiesta(r.richiesta)}` });
    if (!attivo) chiudi = true;
  }
  // Ruoli, PIN, password o disattivazione cambiati: le sessioni aperte non valgono più
  if (chiudi) await chiudiSessioni(c, userId);
  return ok();
}
