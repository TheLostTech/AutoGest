// Avvisi di Stripe. Pubblica (niente sessione): la verifica è la firma con STRIPE_WEBHOOK_SECRET.
// Il contenuto dell'evento serve solo a trovare l'azienda: lo stato si rilegge sempre da Stripe (sincronizza),
// così l'ordine degli eventi e gli eventi doppi non contano. Spec registrazione-pagamento, sezione 5.
import Stripe from "stripe";
import { idAziendaValido } from "@/lib/accesso/id-azienda";
import { aziendaDaEvento, type EventoMinimo } from "@/lib/stripe/chiavi";
import { modalitaStripe, sincronizzaOLancia, stripe } from "@/lib/stripe/server";

const NOSTORE = { "Cache-Control": "no-store" };
const risposta = (stato: number, corpo: Record<string, unknown>) => Response.json(corpo, { status: stato, headers: NOSTORE });

// L'azienda dal cliente Stripe (metadata.azienda); null se il cliente non c'è o non è nostro.
async function aziendaDelCliente(s: Stripe, cliente: string): Promise<string | null> {
  const c = await s.customers.retrieve(cliente);
  if (c.deleted) return null;
  return c.metadata?.azienda || null;
}

async function aziendaDellOrologio(s: Stripe, orologio: string): Promise<string | null> {
  const r = await s.customers.list({ test_clock: orologio, limit: 1 });
  return r.data[0]?.metadata?.azienda || null;
}

export async function POST(req: Request) {
  const segreto = process.env.STRIPE_WEBHOOK_SECRET;
  if (!segreto) return risposta(503, { error: "Avvisi Stripe non configurati" });
  const corpo = await req.text();
  const firma = req.headers.get("stripe-signature") ?? "";
  let evento: Stripe.Event;
  try {
    // La firma si controlla senza chiave segreta (serve solo il segreto degli avvisi)
    evento = Stripe.webhooks.constructEvent(corpo, firma, segreto);
  } catch {
    return risposta(400, { error: "Firma non valida" });
  }

  const da = aziendaDaEvento(evento as unknown as EventoMinimo);
  if (!da) return risposta(200, { ricevuto: true });
  // Avviso vero ma niente chiave: non si può rileggere. 503, così Stripe ritenta quando la chiave c'è.
  if (modalitaStripe() === "spenta") {
    console.error("Avviso Stripe ricevuto, ma Stripe non è configurato", evento.id, evento.type);
    return risposta(503, { error: "Stripe non configurato" });
  }
  const s = stripe();
  let aziendaId: string | null;
  try {
    aziendaId = "azienda" in da ? da.azienda : "cliente" in da ? await aziendaDelCliente(s, da.cliente) : await aziendaDellOrologio(s, da.orologio);
  } catch (e) {
    console.error("Avviso Stripe: azienda non trovata per un errore di Stripe", evento.id, evento.type, e);
    return risposta(500, { error: "Stripe non risponde" });
  }
  // Id assente o che non può essere un'azienda nostra: nel log e 200, Stripe non deve ritentare
  if (!aziendaId || !idAziendaValido(aziendaId)) {
    console.warn("Avviso Stripe di un'azienda sconosciuta", evento.id, evento.type, da);
    return risposta(200, { ricevuto: true });
  }
  try {
    await sincronizzaOLancia(aziendaId);
  } catch (e) {
    console.error("Avviso Stripe: sincronizzazione non riuscita", evento.id, evento.type, aziendaId, e);
    return risposta(500, { error: "Sincronizzazione non riuscita" });
  }
  return risposta(200, { ricevuto: true });
}
