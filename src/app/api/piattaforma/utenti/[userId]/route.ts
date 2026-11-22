// Modifica di un utente: ruoli, PIN, password, disattivazione. Solo super admin; ogni modifica va nel registro dell'azienda.
import { superadminDaRichiesta } from "@/lib/accesso/server";
import { modificheDaCorpo } from "@/lib/accesso/persone-regole";
import { richiestaObbligatoria } from "@/lib/accesso/richieste";
import { aggiungiRichiesta } from "@/lib/piattaforma/richieste-file";
import { AVVISO_REGISTRO, contesto, daAltroSito, errore, leggiJson, ok, registra, aziendaEsiste } from "@/lib/piattaforma/server";
import { applicaModifiche, descrizioneRichiesta, membroDellAzienda, richiestaDaCorpo, utenteSuperadmin } from "@/lib/piattaforma/utenti";

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
  const trovato = await membroDellAzienda(c, azienda.id, userId);
  if (!trovato) return errore(404, "Utente non trovato.");
  if (utenteSuperadmin(trovato)) return errore(403, "Questo utente non si modifica da qui.");

  const m = modificheDaCorpo(corpo, 8);
  if ("errore" in m) return errore(400, m.errore);

  // Richiesta scritta: obbligatoria per cambiare i ruoli, facoltativa per il resto
  const r = await richiestaDaCorpo(azienda.id, corpo.richiesta, !!m.cambi.ruoli && richiestaObbligatoria("ruoli"));
  if ("errore" in r) return r.errore;

  const nome = g.utente.nome;
  const quando = new Date().toISOString();
  const rich = descrizioneRichiesta(r.richiesta);
  let avviso = false;
  // Ogni passo scrive prima la richiesta e poi il registro; un guasto del registro è solo un avviso
  const fallita = await applicaModifiche(c, trovato, m.cambi, {
    emailUsata: "Esiste già una persona con questa email.",
    motivoSospensione: "Disattivato dalla piattaforma",
    traccia: async (azione, dettaglio) => {
      if (r.richiesta) await aggiungiRichiesta(azienda.id, { userId, azione, quando, autore: nome, ...r.richiesta });
      if (!(await registra(azienda.id, nome, { entity: "utente", entityId: userId, action: azione, detail: `${dettaglio} · richiesta: ${rich}` }))) avviso = true;
    },
  });
  if (fallita) return fallita;
  return ok(avviso ? { ok: true, avviso: AVVISO_REGISTRO } : { ok: true });
}
