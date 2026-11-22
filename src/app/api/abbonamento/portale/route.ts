// Portale clienti Stripe: carta, fatture, dati di fatturazione e disdetta a fine periodo (spec registrazione-pagamento,
// sezione 6). POST risponde { url }; Stripe riporta su /impostazioni/abbonamento.
import { connection } from "next/server";
import { leggiAbbonamento } from "@/lib/abbonamento-server";
import { daAltroSito, errore } from "@/lib/piattaforma/server";
import { stessoAmbiente } from "@/lib/stripe/chiavi";
import { origine, titolare } from "@/lib/stripe/richiesta";
import { modalitaStripe, stripe } from "@/lib/stripe/server";

const NOSTORE = { "Cache-Control": "no-store" };

export async function POST(req: Request) {
  await connection();
  const x = daAltroSito(req, true);
  if (x) return x;
  const a = await titolare(req);
  if (a instanceof Response) return a;
  const m = modalitaStripe();
  if (m === "spenta") return errore(503, "Pagamenti non disponibili");

  const ab = await leggiAbbonamento(a.azienda.id);
  if (!ab?.customerId) return errore(409, "Nessun pagamento ancora fatto: il portale si apre dopo il primo abbonamento.");
  if (!stessoAmbiente(ab, m)) return errore(409, "Abbonamento di un altro ambiente Stripe: serve l'assistenza");

  try {
    const s = await stripe().billingPortal.sessions.create({
      customer: ab.customerId,
      return_url: `${origine(req)}/impostazioni/abbonamento`,
      locale: "it",
    });
    return Response.json({ url: s.url }, { headers: NOSTORE });
  } catch (e) {
    console.error("Portale Stripe non aperto", a.azienda.id, e);
    return errore(502, "Stripe non risponde: riprova tra poco.");
  }
}
