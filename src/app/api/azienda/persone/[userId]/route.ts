// Modifica di una persona dell'azienda: ruoli, nuova password, nuovo PIN, sospendi o riattiva. Solo il titolare
// (o il super admin in assistenza), solo sulle persone dell'azienda della sessione; ogni modifica va nel registro.
import { accessoDaRichiesta, soloRuoli } from "@/lib/accesso/server";
import { cambioRuoliPermesso, EMAIL_USATA, modificheDaCorpo, SERVE_RESPONSABILE } from "@/lib/accesso/persone-regole";
import { PASSWORD_MIN } from "@/lib/accesso/registrazione";
import { ruoliDaStringa } from "@/lib/accesso/ruoli";
import { AVVISO_REGISTRO, contesto, daAltroSito, errore, leggiJson, ok } from "@/lib/piattaforma/server";
import { applicaModifiche, membroDellAzienda, registraDaAccesso, righeMembri, utenteSuperadmin } from "@/lib/piattaforma/utenti";

export async function PATCH(req: Request, { params }: { params: Promise<{ userId: string }> }) {
  const a = await accessoDaRichiesta(req);
  if (a instanceof Response) return a;
  const no = soloRuoli(a, "responsabile");
  if (no) return no;
  const x = daAltroSito(req, true);
  if (x) return x;
  const { userId } = await params;
  const corpo = await leggiJson(req);
  if (!corpo) return errore(400, "Richiesta non valida.");

  const c = await contesto();
  // Solo le persone di quest'azienda: le altre rispondono come se non esistessero
  const trovato = await membroDellAzienda(c, a.azienda.id, userId);
  if (!trovato) return errore(404, "Persona non trovata.");
  if (utenteSuperadmin(trovato)) return errore(403, "Questo accesso non si modifica da qui.");

  const m = modificheDaCorpo(corpo, PASSWORD_MIN);
  if ("errore" in m) return errore(400, m.errore);
  const { cambi } = m;
  if (cambi.attivo === false && userId === a.utente.id) return errore(400, "Non puoi sospendere il tuo accesso.");

  // L'azienda non resta mai senza un responsabile attivo
  if (cambi.ruoli || cambi.attivo === false) {
    const membri = (await righeMembri(c, a.azienda.id)).map((p) => ({ userId: p.id, ruoli: p.ruoli, sospeso: !p.attivo }));
    const ruoli = cambi.ruoli ?? ruoliDaStringa(trovato.membro.role);
    if (!cambioRuoliPermesso(membri, userId, ruoli, cambi.attivo === false ? true : undefined)) return errore(409, SERVE_RESPONSABILE, "responsabile");
  }

  let avviso = false;
  const fallita = await applicaModifiche(c, trovato, cambi, {
    emailUsata: EMAIL_USATA,
    motivoSospensione: "Sospeso dal titolare",
    traccia: async (azione, dettaglio) => {
      if (!(await registraDaAccesso(a, { entity: "utente", entityId: userId, action: azione, detail: dettaglio }))) avviso = true;
    },
  });
  if (fallita) return fallita;
  // Il titolare che cambia i propri ruoli, PIN o password chiude anche la propria sessione: la pagina torna all'accesso
  const esci = userId === a.utente.id && (!!cambi.ruoli || cambi.pin !== undefined || cambi.password !== undefined);
  return ok({ ok: true, ...(esci ? { esci: true } : {}), ...(avviso ? { avviso: AVVISO_REGISTRO } : {}) });
}
