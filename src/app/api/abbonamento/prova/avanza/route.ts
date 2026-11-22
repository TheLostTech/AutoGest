// Strumenti di prova (spec registrazione-pagamento, sezione 7): POST { passo } fa avanzare l'orologio di prova di Stripe
// dell'azienda di un giorno, una settimana, un mese o un anno. Risponde 202 { frozenTime } (ms, l'ora d'arrivo):
// Stripe finisce in background e la pagina ricontrolla con GET /api/abbonamento/stato?orologio=1.
// Solo con le chiavi di prova: altrimenti la route non esiste (404). Solo il titolare (o l'assistenza).
import { connection } from "next/server";
import { passoValido } from "@/lib/abbonamento";
import { daAltroSito, errore, leggiJson } from "@/lib/piattaforma/server";
import { titolare } from "@/lib/stripe/richiesta";
import { avanzaOrologio, modalitaStripe } from "@/lib/stripe/server";

const NOSTORE = { "Cache-Control": "no-store" };

export async function POST(req: Request) {
  await connection();
  // Con la chiave vera (o senza chiave) gli strumenti di prova non esistono, prima di ogni altro controllo
  if (modalitaStripe() !== "prova") return errore(404, "Non trovato");
  const x = daAltroSito(req, true);
  if (x) return x;
  const a = await titolare(req, { paga: true });
  if (a instanceof Response) return a;

  const passo = passoValido(await leggiJson(req));
  if (!passo) return errore(400, "Richiesta non valida.");

  try {
    const esito = await avanzaOrologio(a.azienda.id, passo);
    if ("errore" in esito) return errore(esito.stato, esito.errore);
    return Response.json(esito, { status: 202, headers: NOSTORE });
  } catch (e) {
    console.error("Orologio di prova non avanzato", a.azienda.id, passo, e);
    return errore(502, "Stripe non risponde: riprova tra poco.");
  }
}
