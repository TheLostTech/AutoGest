// Utenti di un'azienda: elenco e creazione (con richiesta scritta). Solo super admin.
import { randomBytes } from "node:crypto";
import { connection } from "next/server";
import { superadminDaRichiesta } from "@/lib/accesso/server";
import { RUOLI, RUOLO_LABEL, ruoliAStringa, ruoliDaStringa } from "@/lib/accesso/ruoli";
import { pinValido } from "@/lib/accesso/pin";
import { richiestaObbligatoria } from "@/lib/accesso/richieste";
import { impostaPin } from "@/lib/auth/pin-dispositivo";
import { aggiungiRichiesta, elencoRichieste } from "@/lib/piattaforma/richieste-file";
import { descrizioneRichiesta, EMAIL, richiestaDaCorpo, ruoliDaCorpo } from "@/lib/piattaforma/utenti";
import { aziendaEsiste, contesto, daAltroSito, errore, leggiJson, ok, registra, testo } from "@/lib/piattaforma/server";



export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  await connection();
  const g = await superadminDaRichiesta(req);
  if (g instanceof Response) return g;
  const { id } = await params;
  const azienda = await aziendaEsiste(id);
  if (!azienda) return errore(404, "Azienda non trovata.");
  const c = await contesto();
  const membri = await c.adapter.findMany<{ userId: string; role: string }>({ model: "member", where: [{ field: "organizationId", value: id }] });
  const ids = membri.map((m) => m.userId);
  const utenti = ids.length ? await c.adapter.findMany<{ id: string; name: string; email: string; banned?: boolean | null }>({ model: "user", where: [{ field: "id", operator: "in", value: ids }] }) : [];
  const conti = ids.length ? await c.adapter.findMany<{ userId: string; providerId: string }>({ model: "account", where: [{ field: "userId", operator: "in", value: ids }] }) : [];
  const pin = await c.adapter.findMany<{ userId: string }>({ model: "pinUtente", where: [{ field: "organizationId", value: id }] });
  const richieste = await elencoRichieste(id);
  const righe = membri
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
        richieste: richieste.filter((r) => r.userId === u.id).reverse(),
      };
    })
    .filter((x) => x !== null)
    .sort((a, b) => a.nome.localeCompare(b.nome, "it"));
  return ok({ azienda: { id: azienda.id, nome: azienda.name }, utenti: righe });
}

export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const g = await superadminDaRichiesta(req);
  if (g instanceof Response) return g;
  const x = daAltroSito(req, true);
  if (x) return x;
  const { id } = await params;
  const azienda = await aziendaEsiste(id);
  if (!azienda) return errore(404, "Azienda non trovata.");
  const corpo = await leggiJson(req);
  if (!corpo) return errore(400, "Richiesta non valida.");

  const nome = testo(corpo.nome, 2, 80);
  if (!nome) return errore(400, "Scrivi il nome della persona (da 2 a 80 caratteri).");
  const ruoli = ruoliDaCorpo(corpo.ruoli);
  if (!ruoli) return errore(400, `Scegli almeno un ruolo tra: ${RUOLI.join(", ")}.`);

  // Modo d'accesso: email + password (da qualunque dispositivo) e/o PIN (solo dai dispositivi dell'azienda)
  const emailIn = typeof corpo.email === "string" ? corpo.email.trim().toLowerCase() : "";
  const passwordIn = typeof corpo.password === "string" ? corpo.password : "";
  const pinIn = typeof corpo.pin === "string" ? corpo.pin : "";
  const conEmail = !!emailIn || !!passwordIn;
  if (conEmail && (!EMAIL.test(emailIn) || passwordIn.length < 8 || passwordIn.length > 128)) {
    return errore(400, "Per l'accesso con email servono un'email valida e una password di almeno 8 caratteri.");
  }
  if (pinIn && !pinValido(pinIn)) return errore(400, "Il PIN è di 4 cifre.");
  if (!conEmail && !pinIn) return errore(400, "Scegli come entra: email e password, PIN, o tutti e due.");

  const r = await richiestaDaCorpo(id, corpo.richiesta, richiestaObbligatoria("crea"));
  if ("errore" in r) return r.errore;

  const c = await contesto();
  if (conEmail && (await c.internalAdapter.findUserByEmail(emailIn))) return errore(409, "Esiste già una persona con questa email.");

  // Chi entra solo con il PIN ha un'email interna (mai raggiungibile) e nessuna password
  const provvisoria = `nuovo-${randomBytes(8).toString("hex")}@pin.invalid`;
  const utente = await c.internalAdapter.createUser({ name: nome, email: conEmail ? emailIn : provvisoria, emailVerified: conEmail ? false : true }, { method: "admin" });
  try {
    if (!conEmail) await c.internalAdapter.updateUser(utente.id, { email: `${utente.id}@pin.invalid` });
    if (conEmail) {
      await c.internalAdapter.linkAccount({ userId: utente.id, providerId: "credential", accountId: utente.id, password: await c.password.hash(passwordIn) });
    }
    await c.adapter.create({ model: "member", data: { organizationId: id, userId: utente.id, role: ruoliAStringa(ruoli), createdAt: new Date() } });
    if (pinIn) await impostaPin(c, utente.id, id, pinIn);
  } catch (e) {
    // Niente utenti a metà: si toglie tutto quello che è stato creato
    await c.adapter.delete({ model: "member", where: [{ field: "userId", value: utente.id }] }).catch(() => undefined);
    await c.adapter.delete({ model: "pinUtente", where: [{ field: "userId", value: utente.id }] }).catch(() => undefined);
    await c.adapter.delete({ model: "account", where: [{ field: "userId", value: utente.id }] }).catch(() => undefined);
    await c.adapter.delete({ model: "user", where: [{ field: "id", value: utente.id }] }).catch(() => undefined);
    console.error("Creazione utente non riuscita", e);
    return errore(500, "Non riesco a creare l'utente. Riprova.");
  }

  if (r.richiesta) {
    await aggiungiRichiesta(id, { userId: utente.id, azione: "Utente creato", quando: new Date().toISOString(), autore: g.utente.nome, ...r.richiesta });
  }
  const modo = [conEmail ? "email e password" : "", pinIn ? "PIN" : ""].filter(Boolean).join(" + ");
  await registra(id, g.utente.nome, {
    entity: "utente",
    entityId: utente.id,
    action: "Utente creato",
    detail: `${nome} · ${ruoli.map((x) => RUOLO_LABEL[x]).join(", ")} · accesso: ${modo} · richiesta: ${descrizioneRichiesta(r.richiesta)}`,
  });
  return ok({ id: utente.id }, 201);
}
