// Moduli in più sull'abbonamento in corso (spec registrazione-pagamento, sezione 6).
// POST { aggiungi } | { togli } | { anteprima } | { riattiva: true }: risponde { abbonamento }, oppure { importo } in
// centesimi IVA esclusa per l'anteprima. Solo il titolare (o l'assistenza), con lo stato attivo o disdetto.
import { connection } from "next/server";
import { richiestaModuli } from "@/lib/abbonamento";
import { daAltroSito, errore, leggiJson } from "@/lib/piattaforma/server";
import { PREZZI_DIVERSI } from "@/lib/stripe/forma";
import { titolare } from "@/lib/stripe/richiesta";
import { cambiaModuli, modalitaStripe, unCambioAllaVolta } from "@/lib/stripe/server";

const NOSTORE = { "Cache-Control": "no-store" };

export async function POST(req: Request) {
  await connection();
  const x = daAltroSito(req, true);
  if (x) return x;
  const a = await titolare(req, { paga: true });
  if (a instanceof Response) return a;
  if (modalitaStripe() === "spenta") return errore(503, "Pagamenti non disponibili");

  const r = richiestaModuli(await leggiJson(req));
  if (!r) return errore(400, "Richiesta non valida.");

  try {
    // Un cambio per volta per azienda: due schede non mettono lo stesso modulo due volte
    const esito = await unCambioAllaVolta(a.azienda.id, () => cambiaModuli(a.azienda.id, r));
    if ("errore" in esito) return errore(esito.stato, esito.errore);
    return Response.json(esito, { headers: NOSTORE });
  } catch (e) {
    if (e instanceof Error && e.message === PREZZI_DIVERSI) return errore(502, PREZZI_DIVERSI);
    console.error("Cambio moduli Stripe non riuscito", a.azienda.id, r, e);
    return errore(502, "Stripe non risponde: riprova tra poco.");
  }
}
