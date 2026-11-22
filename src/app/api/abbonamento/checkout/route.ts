// Pagamento del primo abbonamento con Stripe Checkout (spec registrazione-pagamento, sezione 4).
// POST crea la sessione e risponde { url }; GET ?session_id= ricontrolla il ritorno, per la pagina /abbonamento/fatto.
import { connection } from "next/server";
import { sceltaValida } from "@/lib/abbonamento";
import { percorsoDaSicuro } from "@/lib/accesso/percorsi";
import type { Accesso } from "@/lib/accesso/regole";
import { ruoliDaStringa } from "@/lib/accesso/ruoli";
import { contesto, daAltroSito, errore, leggiJson } from "@/lib/piattaforma/server";
import { chiaveCheckout } from "@/lib/stripe/chiavi";
import { origine, titolare } from "@/lib/stripe/richiesta";
import { aliquotaIva, clientePer, esitoCheckout, modalitaStripe, preparaCheckout, prezziPer, STATI_IN_CORSO, stripe, sincronizza, unCheckoutAllaVolta } from "@/lib/stripe/server";

const NOSTORE = { "Cache-Control": "no-store" };
const ALTRO_AMBIENTE = "Abbonamento di un altro ambiente Stripe: serve l'assistenza";
const PAGAMENTO_IN_CORSO = "Un pagamento è già in corso: aspetta la conferma di Stripe, questa pagina si aggiorna da sola.";

// L'email del cliente Stripe: quella di chi paga; in assistenza quella di un titolare dell'azienda (non del super admin).
async function emailCliente(a: Accesso): Promise<string> {
  const c = await contesto();
  let userId = a.utente.id;
  if (a.assistenza) {
    const membri = await c.adapter.findMany<{ userId: string; role: string }>({ model: "member", where: [{ field: "organizationId", value: a.azienda.id }] });
    const t = membri.find((m) => ruoliDaStringa(m.role).includes("responsabile"));
    if (t) userId = t.userId;
  }
  const u = await c.internalAdapter.findUserById(userId).catch(() => null);
  return u?.email ?? "";
}

export async function POST(req: Request) {
  await connection();
  const x = daAltroSito(req, true);
  if (x) return x;
  const a = await titolare(req, { paga: true });
  if (a instanceof Response) return a;
  if (modalitaStripe() === "spenta") return errore(503, "Pagamenti non disponibili");

  const corpo = await leggiJson(req);
  const scelta = sceltaValida(corpo);
  if (!scelta) return errore(400, "Scegli mensile o annuale e i moduli.");
  const da = percorsoDaSicuro(typeof corpo?.da === "string" ? corpo.da : "/");

  // Un Checkout per volta per azienda: la seconda scheda vede quello che ha fatto la prima
  return unCheckoutAllaVolta(a.azienda.id, () => crea(req, a, scelta, da));
}

async function crea(req: Request, a: Accesso, scelta: NonNullable<ReturnType<typeof sceltaValida>>, da: string): Promise<Response> {
  const ab = await sincronizza(a.azienda.id);
  if (STATI_IN_CORSO.has(ab.stato)) return errore(409, "Abbonamento già attivo: aggiungi i moduli da Abbonamento");

  try {
    const customer = await clientePer(a.azienda.id, a.azienda.nome, await emailCliente(a));
    // Doppio clic: stessa azienda, scelta e minuto danno la stessa sessione (Stripe ripete la risposta)
    const chiave = chiaveCheckout(a.azienda.id, scelta.periodo, scelta.moduli, Date.now());
    // Le sessioni aperte di questo cliente scadono; con un pagamento già in attesa di Stripe non se ne apre un altro
    const { pagamentoInCorso } = await preparaCheckout(customer, chiave);
    if (pagamentoInCorso) return errore(409, PAGAMENTO_IN_CORSO);
    const [prezzi, iva] = await Promise.all([prezziPer(scelta.moduli, scelta.periodo), aliquotaIva()]);
    const base = origine(req);
    const sessione = await stripe().checkout.sessions.create(
      {
        mode: "subscription",
        customer,
        line_items: prezzi.map((price) => ({ price, quantity: 1, tax_rates: [iva] })),
        client_reference_id: a.azienda.id,
        subscription_data: { metadata: { azienda: a.azienda.id } },
        // La chiave sta anche sulla sessione: al doppio clic preparaCheckout non fa scadere quella che Stripe ripete
        metadata: { azienda: a.azienda.id, chiave },
        tax_id_collection: { enabled: true },
        billing_address_collection: "required",
        customer_update: { name: "auto", address: "auto" },
        locale: "it",
        success_url: `${base}/abbonamento/fatto?session_id={CHECKOUT_SESSION_ID}`,
        cancel_url: `${base}${da}`,
      },
      { idempotencyKey: chiave },
    );
    if (!sessione.url) throw new Error("Sessione Checkout senza indirizzo");
    return Response.json({ url: sessione.url }, { headers: NOSTORE });
  } catch (e) {
    if (e instanceof Error && e.message === ALTRO_AMBIENTE) return errore(409, ALTRO_AMBIENTE);
    // Stessa chiave con parametri diversi (un'altra scheda, nello stesso minuto, partita da un'altra pagina): quella
    // sessione è ancora aperta, non se ne crea una seconda
    if ((e as { type?: unknown } | null)?.type === "StripeIdempotencyError") return errore(409, PAGAMENTO_IN_CORSO);
    console.error("Checkout Stripe non creato", a.azienda.id, e);
    return errore(502, "Stripe non risponde: riprova tra poco.");
  }
}

export async function GET(req: Request) {
  await connection();
  const a = await titolare(req);
  if (a instanceof Response) return a;
  const sessionId = new URL(req.url).searchParams.get("session_id") ?? "";
  const esito = await esitoCheckout(a.azienda.id, sessionId);
  if ("errore" in esito) return errore(esito.stato, esito.errore);
  return Response.json(esito, { headers: NOSTORE });
}
