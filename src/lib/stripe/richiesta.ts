// Controlli comuni alle route dell'abbonamento (Checkout, moduli, portale). Solo server.
import type { Accesso } from "@/lib/accesso/regole";
import { accessoDaRichiesta, soloRuoli } from "@/lib/accesso/server";
import { errore } from "@/lib/piattaforma/server";

/** Il titolare dell'azienda attiva, o il super admin in assistenza; solo per le aziende registrate. */
export async function titolare(req: Request): Promise<Accesso | Response> {
  const a = await accessoDaRichiesta(req);
  if (a instanceof Response) return a;
  if (!(a.ruoli.includes("responsabile") || !!a.assistenza)) {
    const no = soloRuoli(a, "responsabile");
    if (no) return no;
  }
  if (!a.azienda.registrata) return errore(403, "Questa azienda non ha un abbonamento da pagare.");
  return a;
}

/** Indirizzo del gestionale per i ritorni da Stripe: INDIRIZZO_GESTIONALE se c'è, altrimenti quello della richiesta. */
export function origine(req: Request): string {
  const fissa = process.env.INDIRIZZO_GESTIONALE?.trim().replace(/\/+$/, "");
  return fissa || new URL(req.url).origin;
}
