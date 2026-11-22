// Stato dell'abbonamento dell'azienda attiva, per il gestionale e la pagina Abbonamento.
// Si rilegge da Stripe con ?sincronizza=1, oppure per il titolare se l'ultimo aggiornamento ha più di un'ora (spec, sezione 5).
import { connection } from "next/server";
import { ABBONAMENTO_NUOVO, contoAllaRovescia } from "@/lib/abbonamento";
import { leggiAbbonamento } from "@/lib/abbonamento-server";
import { accessoDaRichiesta } from "@/lib/accesso/server";
import { daSincronizzare } from "@/lib/stripe/chiavi";
import { modalitaStripe, sincronizza } from "@/lib/stripe/server";

const NOSTORE = { "Cache-Control": "no-store" };

export async function GET(req: Request) {
  await connection();
  const a = await accessoDaRichiesta(req);
  if (a instanceof Response) return a;
  const modalita = modalitaStripe();
  const registrata = a.azienda.registrata;
  // Le aziende senza `registrata` (demo, create dal super admin) non hanno abbonamento: restano con gli interruttori
  if (!registrata) return Response.json({ abbonamento: null, registrata, modalita, conto: null }, { headers: NOSTORE });

  const ora = Date.now();
  const titolare = a.ruoli.includes("responsabile") || !!a.assistenza;
  let ab = (await leggiAbbonamento(a.azienda.id)) ?? ABBONAMENTO_NUOVO(modalita !== "live", ora);
  const richiesta = new URL(req.url).searchParams.get("sincronizza") === "1";
  // sincronizza non lancia mai: con Stripe irraggiungibile restituisce quello che c'è. Limitata: qualunque ruolo può
  // chiederla, quindi al massimo un tentativo ogni 15 secondi per azienda (le richieste insieme si raggruppano).
  if (daSincronizzare({ richiesta, titolare, aggiornato: ab.aggiornato, ora })) ab = await sincronizza(a.azienda.id, { limita: true });
  return Response.json({ abbonamento: ab, registrata, modalita, conto: contoAllaRovescia(ab, Date.now()) }, { headers: NOSTORE });
}
