// Modifica di un utente: ruoli, PIN, password, disattivazione. Solo super admin; ogni modifica va nel registro dell'azienda.
import { superadminDaRichiesta } from "@/lib/accesso/server";
import { RUOLO_LABEL, ruoliAStringa, ruoliDaStringa } from "@/lib/accesso/ruoli";
import { pinValido } from "@/lib/accesso/pin";
import { richiestaObbligatoria } from "@/lib/accesso/richieste";
import { impostaPin } from "@/lib/auth/pin-dispositivo";
import { aggiungiRichiesta } from "@/lib/piattaforma/richieste-file";
import { AVVISO_REGISTRO, chiudiSessioni, contesto, daAltroSito, errore, eSuperadmin, leggiJson, ok, registra, aziendaEsiste } from "@/lib/piattaforma/server";
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
  if (emailNuova && (!EMAIL.test(emailNuova) || emailNuova.endsWith("@pin.invalid"))) return errore(400, "Email non valida.");
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
  let avviso = false;
  // Ogni passo scrive prima la richiesta e poi il registro; un guasto del registro è solo un avviso
  const traccia = async (azione: string, detail: string) => {
    if (r.richiesta) await aggiungiRichiesta(azienda.id, { userId, azione, quando, autore: nome, ...r.richiesta });
    if (!(await registra(azienda.id, nome, { entity: "utente", entityId: userId, action: azione, detail }))) avviso = true;
  };
  const rich = descrizioneRichiesta(r.richiesta);
  // Si segna PRIMA di ogni modifica: se un passo fallisce a metà, le sessioni si chiudono comunque (finally)
  let chiudi = false;

  try {
    if (nuoviRuoli) {
      const prima = ruoliDaStringa(membro.role);
      chiudi = true;
      await c.adapter.update({ model: "member", where: [{ field: "id", value: membro.id }], update: { role: ruoliAStringa(nuoviRuoli) } });
      await traccia("Ruoli cambiati", `${utente.name} · da ${prima.map((x) => RUOLO_LABEL[x]).join(", ") || "nessuno"} a ${nuoviRuoli.map((x) => RUOLO_LABEL[x]).join(", ")} · richiesta: ${rich}`);
    }
    if (typeof corpo.pin === "string") {
      chiudi = true;
      await impostaPin(c, userId, azienda.id, corpo.pin);
      await traccia("PIN reimpostato", `${utente.name} · richiesta: ${rich}`);
    }
    if (typeof corpo.password === "string") {
      chiudi = true;
      const hash = await c.password.hash(corpo.password);
      if (conto) await c.internalAdapter.updatePassword(userId, hash);
      else {
        await c.internalAdapter.updateUser(userId, { email: emailNuova, emailVerified: false });
        await c.internalAdapter.linkAccount({ userId, providerId: "credential", accountId: userId, password: hash });
      }
      await traccia(conto ? "Password reimpostata" : "Accesso con email attivato", `${utente.name} · richiesta: ${rich}`);
    }
    if (typeof corpo.attivo === "boolean") {
      const attivo = corpo.attivo;
      if (!attivo) chiudi = true;
      await c.internalAdapter.updateUser(userId, attivo ? { banned: false, banReason: null, banExpires: null } : { banned: true, banReason: "Disattivato dalla piattaforma", banExpires: null });
      await traccia(attivo ? "Utente riattivato" : "Utente disattivato", `${utente.name} · richiesta: ${rich}`);
    }
  } catch (e) {
    console.error("Modifica utente non completata", userId, e);
    return errore(500, "La modifica non è stata completata del tutto: controlla la scheda. Le sessioni aperte della persona sono state chiuse.");
  } finally {
    // Ruoli, PIN, password o disattivazione toccati (anche a metà): le sessioni aperte non valgono più
    if (chiudi) await chiudiSessioni(c, userId);
  }
  return ok(avviso ? { ok: true, avviso: AVVISO_REGISTRO } : { ok: true });
}
