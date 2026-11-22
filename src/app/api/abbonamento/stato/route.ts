// Stato dell'abbonamento dell'azienda attiva, per il gestionale e la pagina Abbonamento.
// Si rilegge da Stripe con ?sincronizza=1, oppure per il titolare se l'ultimo aggiornamento ha più di un'ora (spec, sezione 5).
// ?orologio=1 (strumenti di prova, sezione 7): per il titolare con l'orologio di prova si legge anche il suo stato da
// Stripe (`orologioPronto`) e, appena torna pronto dopo un avanzamento, si sincronizza senza il limite dei 15 secondi.
// Senza ?orologio=1, o senza orologio, `orologioPronto` è null: la lettura normale non fa chiamate a Stripe in più.
import { connection } from "next/server";
import { ABBONAMENTO_NUOVO, contoAllaRovescia } from "@/lib/abbonamento";
import { leggiAbbonamento } from "@/lib/abbonamento-server";
import { accessoDaRichiesta } from "@/lib/accesso/server";
import { daSincronizzare } from "@/lib/stripe/chiavi";
import { conOrologio, modalitaStripe, sincronizza, statoOrologio } from "@/lib/stripe/server";

const NOSTORE = { "Cache-Control": "no-store" };

export async function GET(req: Request) {
  await connection();
  const a = await accessoDaRichiesta(req);
  if (a instanceof Response) return a;
  const modalita = modalitaStripe();
  const registrata = a.azienda.registrata;
  // Le aziende senza `registrata` (demo, create dal super admin) non hanno abbonamento: restano con gli interruttori
  if (!registrata) return Response.json({ abbonamento: null, registrata, modalita, conto: null, orologioPronto: null }, { headers: NOSTORE });

  const ora = Date.now();
  const titolare = a.ruoli.includes("responsabile") || !!a.assistenza;
  let ab = (await leggiAbbonamento(a.azienda.id)) ?? ABBONAMENTO_NUOVO(modalita !== "live", ora);
  const parametri = new URL(req.url).searchParams;
  const richiesta = parametri.get("sincronizza") === "1";
  // sincronizza non lancia mai: con Stripe irraggiungibile restituisce quello che c'è. Limitata: qualunque ruolo può
  // chiederla, quindi al massimo un tentativo ogni 15 secondi per azienda (le richieste insieme si raggruppano).
  if (daSincronizzare({ richiesta, titolare, aggiornato: ab.aggiornato, ora })) ab = await sincronizza(a.azienda.id, { limita: true });
  let orologioPronto: boolean | null = null;
  // Solo il titolare, che ha in mano i pulsanti: dagli altri ruoli questa lettura non chiama Stripe
  if (parametri.get("orologio") === "1" && titolare && conOrologio(ab)) {
    const o = await statoOrologio(a.azienda.id, ab);
    orologioPronto = o.pronto;
    ab = o.abbonamento;
  }
  return Response.json({ abbonamento: ab, registrata, modalita, conto: contoAllaRovescia(ab, Date.now()), orologioPronto }, { headers: NOSTORE });
}
