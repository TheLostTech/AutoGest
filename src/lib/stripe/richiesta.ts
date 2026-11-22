// Controlli comuni alle route dell'abbonamento (Checkout, moduli, portale). Solo server.
import { scritturaPersoneNegata } from "@/lib/accesso/persone-regole";
import type { Accesso } from "@/lib/accesso/regole";
import { accessoDaRichiesta, soloRuoli } from "@/lib/accesso/server";
import { errore } from "@/lib/piattaforma/server";
import { origineRitorno } from "./chiavi";

/**
 * Il titolare dell'azienda attiva, o il super admin in assistenza; solo per le aziende registrate.
 * `paga`: la richiesta spende o apre Stripe (Checkout, moduli, portale, orologio di prova). Come per le Persone, serve
 * una sessione con email e password: con il PIN di 4 cifre di un dispositivo condiviso si guarda, non si paga.
 */
export async function titolare(req: Request, opzioni: { paga?: boolean } = {}): Promise<Accesso | Response> {
  const a = await accessoDaRichiesta(req);
  if (a instanceof Response) return a;
  if (!(a.ruoli.includes("responsabile") || !!a.assistenza)) {
    const no = soloRuoli(a, "responsabile");
    if (no) return no;
  }
  if (!a.azienda.registrata) return errore(403, "Questa azienda non ha un abbonamento da pagare.");
  if (opzioni.paga) {
    const pin = scritturaPersoneNegata(a.tipo);
    if (pin) return errore(403, pin, "serve-password");
  }
  return a;
}

/**
 * Indirizzo del gestionale per i ritorni da Stripe: quello da cui il titolare sta usando il gestionale (Origin, già
 * controllato da daAltroSito contro Host), così torna dove ha il cookie della sessione. Poi INDIRIZZO_GESTIONALE,
 * poi l'indirizzo della richiesta.
 */
export function origine(req: Request): string {
  return origineRitorno(req.headers.get("origin"), process.env.INDIRIZZO_GESTIONALE, req.url);
}
