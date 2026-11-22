// Persone dell'azienda (accessi dei dipendenti): elenco e creazione. Solo il titolare (o il super admin in assistenza),
// sempre sull'azienda della sessione: nessun id d'azienda arriva dal browser.
import { connection } from "next/server";
import { accessoDaRichiesta, soloRuoli } from "@/lib/accesso/server";
import { RUOLO_LABEL } from "@/lib/accesso/ruoli";
import { EMAIL_USATA, nuovoMembroDaCorpo, scritturaPersoneNegata } from "@/lib/accesso/persone-regole";
import { PASSWORD_MIN } from "@/lib/accesso/registrazione";
import { creaMembro } from "@/lib/piattaforma/crea";
import { AVVISO_REGISTRO, contesto, daAltroSito, errore, leggiJson, ok } from "@/lib/piattaforma/server";
import { descrizioneAccesso, registraDaAccesso, righeMembri } from "@/lib/piattaforma/utenti";

export async function GET(req: Request) {
  await connection();
  const a = await accessoDaRichiesta(req);
  if (a instanceof Response) return a;
  const no = soloRuoli(a, "responsabile");
  if (no) return no;
  const c = await contesto();
  return ok({ persone: await righeMembri(c, a.azienda.id), io: a.utente.id });
}

export async function POST(req: Request) {
  const a = await accessoDaRichiesta(req);
  if (a instanceof Response) return a;
  const no = soloRuoli(a, "responsabile");
  if (no) return no;
  // Con il PIN di un dispositivo condiviso si legge l'elenco, ma non si creano accessi
  const pin = scritturaPersoneNegata(a.tipo);
  if (pin) return errore(403, pin, "serve-password");
  const x = daAltroSito(req, true);
  if (x) return x;
  const corpo = await leggiJson(req);
  if (!corpo) return errore(400, "Richiesta non valida.");

  const n = nuovoMembroDaCorpo(corpo, PASSWORD_MIN);
  if ("errore" in n) return errore(400, n.errore);
  const { nome, ruoli } = n.dati;

  const c = await contesto();
  if (n.dati.email && (await c.internalAdapter.findUserByEmail(n.dati.email))) return errore(409, EMAIL_USATA);

  let userId: string;
  try {
    userId = await creaMembro(c, a.azienda.id, n.dati);
  } catch (e) {
    console.error("Creazione persona non riuscita", a.azienda.id, e);
    return errore(500, "Non riesco a creare l'accesso. Riprova.");
  }

  const scritto = await registraDaAccesso(a, {
    entity: "utente",
    entityId: userId,
    action: "Utente creato",
    detail: `${nome} · ${ruoli.map((r) => RUOLO_LABEL[r]).join(", ")} · accesso: ${descrizioneAccesso(n.dati)}`,
  });
  return ok({ id: userId, ...(scritto ? {} : { avviso: AVVISO_REGISTRO }) }, 201);
}
