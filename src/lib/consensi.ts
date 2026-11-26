// Scheda della registrazione: contatti del titolare e consensi dati, con versione dei testi, ora e indirizzo.
// Puro: la route la salva nel deposito (tipo "registrazione"). Spec prova-15-giorni, "Decisioni" (consensi).
import type { DatiRegistrazione } from "./accesso/registrazione";

// Data dell'ultima modifica di /condizioni e di /privacy: si cambia insieme al testo
export const VERSIONE_CONDIZIONI = "2026-11-26";
export const VERSIONE_PRIVACY = "2026-11-26";

export type Consenso = { versione: string; ora: string /* ISO */; ip: string | null };

export type SchedaRegistrazione = {
  titolare: string;
  email: string;
  telefono: string | null;
  azienda: string;
  registrata: string;
  confermata: string | null;
  condizioni: Consenso;
  privacy: Consenso;
  commerciale: Consenso | null;
  /** Orari (ms) delle email di conferma mandate nelle ultime 24 ore (invioConferma). */
  inviiConferma?: number[];
};

export function schedaRegistrazione(d: DatiRegistrazione, ip: string | null, ora: number): SchedaRegistrazione {
  const quando = new Date(ora).toISOString();
  const consenso = (versione: string): Consenso => ({ versione, ora: quando, ip });
  return {
    titolare: d.nome,
    email: d.email,
    telefono: d.telefono,
    azienda: d.azienda,
    registrata: quando,
    confermata: null,
    condizioni: consenso(VERSIONE_CONDIZIONI),
    privacy: consenso(VERSIONE_PRIVACY),
    // Il consenso ai contatti commerciali è descritto nell'informativa privacy: ne prende la versione
    commerciale: d.commerciale ? consenso(VERSIONE_PRIVACY) : null,
  };
}
