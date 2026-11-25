// Utenti di un'azienda: elenco e creazione (con richiesta scritta). Solo super admin.
import { connection } from "next/server";
import { superadminDaRichiesta } from "@/lib/accesso/server";
import { RUOLO_LABEL } from "@/lib/accesso/ruoli";
import { nuovoMembroDaCorpo } from "@/lib/accesso/persone-regole";
import { richiestaObbligatoria } from "@/lib/accesso/richieste";
import { creaMembro } from "@/lib/piattaforma/crea";
import { aggiungiRichiesta, elencoRichieste } from "@/lib/piattaforma/richieste-file";
import { descrizioneAccesso, descrizioneRichiesta, richiestaDaCorpo, righeMembri } from "@/lib/piattaforma/utenti";
import { AVVISO_REGISTRO, aziendaEsiste, contesto, daAltroSito, errore, leggiJson, ok, registra } from "@/lib/piattaforma/server";

export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  await connection();
  const g = await superadminDaRichiesta(req);
  if (g instanceof Response) return g;
  const { id } = await params;
  const azienda = await aziendaEsiste(id);
  if (!azienda) return errore(404, "Azienda non trovata.");
  const c = await contesto();
  let richieste;
  try {
    richieste = await elencoRichieste(id);
  } catch (e) {
    console.error("Registro delle richieste non letto", id, e);
    return errore(503, "Non riesco a leggere le richieste scritte dell'azienda: riprova tra poco.");
  }
  const righe = (await righeMembri(c, id)).map((u) => ({ ...u, richieste: richieste.filter((r) => r.userId === u.id).reverse() }));
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

  const n = nuovoMembroDaCorpo(corpo, 8);
  if ("errore" in n) return errore(400, n.errore);
  const { nome, ruoli } = n.dati;

  const r = await richiestaDaCorpo(id, corpo.richiesta, richiestaObbligatoria("crea"));
  if ("errore" in r) return r.errore;

  const c = await contesto();
  if (n.dati.email && (await c.internalAdapter.findUserByEmail(n.dati.email))) return errore(409, "Esiste già una persona con questa email.");

  let userId: string;
  try {
    userId = await creaMembro(c, id, n.dati, async (uid) => {
      if (r.richiesta) {
        await aggiungiRichiesta(id, { userId: uid, azione: "Utente creato", quando: new Date().toISOString(), autore: g.utente.nome, ...r.richiesta });
      }
    });
  } catch (e) {
    console.error("Creazione utente non riuscita", e);
    return errore(500, "Non riesco a creare l'utente. Riprova.");
  }

  const scritto = await registra(id, g.utente.nome, {
    entity: "utente",
    entityId: userId,
    action: "Utente creato",
    detail: `${nome} · ${ruoli.map((x) => RUOLO_LABEL[x]).join(", ")} · accesso: ${descrizioneAccesso(n.dati)} · richiesta: ${descrizioneRichiesta(r.richiesta)}`,
  });
  return ok({ id: userId, ...(scritto ? {} : { avviso: AVVISO_REGISTRO }) }, 201);
}
