// Strumenti della prova gratuita (spec prova-15-giorni, sezione 4): POST { passo: "giorno" | "settimana" } sposta in
// avanti di 1 o 7 giorni l'orologio dell'app con cui si conta la prova (spostamentoProva), senza aspettare 15 giorni.
// Nella prova il cliente Stripe e il suo orologio non ci sono ancora: Stripe non si chiama. Risponde { abbonamento }.
// Solo con le chiavi di prova e solo il titolare (o l'assistenza) con email e password: 403 altrimenti. Solo con la
// prova partita e non pagata (stato "nuovo"): 409 altrimenti. Dopo il pagamento si usa l'orologio di Stripe (avanza).
import { passoProvaValido, spostamentoPermesso, spostaProva } from "@/lib/abbonamento";
import { ABBONAMENTO_NON_LEGGIBILE, aggiornaAbbonamento } from "@/lib/abbonamento-server";
import { daAltroSito, errore, leggiJson } from "@/lib/piattaforma/server";
import { titolare } from "@/lib/stripe/richiesta";
import { modalitaStripe } from "@/lib/stripe/server";

const NOSTORE = { "Cache-Control": "no-store" };
const NON_IN_PROVA = new Error("prova non in corso");

export async function POST(req: Request) {
  // Con la chiave vera (o senza chiave) gli strumenti di prova non si usano, prima di ogni altro controllo
  if (modalitaStripe() !== "prova") return errore(403, "Strumenti di prova disponibili solo con le chiavi di prova di Stripe.");
  const x = daAltroSito(req, true);
  if (x) return x;
  const a = await titolare(req, { paga: true });
  if (a instanceof Response) return a;

  const passo = passoProvaValido(await leggiJson(req));
  if (!passo) return errore(400, "Richiesta non valida.");

  try {
    // Si decide sul documento appena letto, dentro il blocco dell'azienda: un pagamento arrivato intanto vince.
    // Non permesso: si lancia, così il documento non si riscrive
    const ab = await aggiornaAbbonamento(a.azienda.id, (prima) => {
      if (!spostamentoPermesso(prima)) throw NON_IN_PROVA;
      return spostaProva(prima, passo);
    });
    return Response.json({ abbonamento: ab }, { headers: NOSTORE });
  } catch (e) {
    if (e === NON_IN_PROVA) return errore(409, "La prova gratuita non è in corso: la data di prova non si sposta.");
    console.error("Prova non spostata", a.azienda.id, passo, e);
    return errore(503, ABBONAMENTO_NON_LEGGIBILE);
  }
}
