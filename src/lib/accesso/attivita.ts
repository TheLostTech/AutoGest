// Richieste "passive": letture automatiche (sincronizzazione ogni 2,5 s, riallineamento eBay) che partono da sole
// anche con il tablet fermo. Non devono contare come attività della persona: altrimenti una sessione da PIN con una
// pagina aperta (anche un'etichetta in un'altra scheda) non scadrebbe mai sul server. Puro: lo usano client e server.
export const INTESTAZIONE_ATTIVITA = "x-attivita";
export const PASSIVA = "passiva";

/** Intestazioni da aggiungere alle richieste automatiche. */
export const intestazioniPassive = (): Record<string, string> => ({ [INTESTAZIONE_ATTIVITA]: PASSIVA });

export function richiestaPassiva(headers: Headers): boolean {
  return headers.get(INTESTAZIONE_ATTIVITA)?.trim().toLowerCase() === PASSIVA;
}

/** Ultimo tocco condiviso fra le schede dello stesso browser (localStorage) e avviso di blocco a tutte le schede. */
export const CHIAVE_ULTIMO_TOCCO = "gestionale-ultimo-tocco";
export const CHIAVE_BLOCCO = "gestionale-blocco-inattivita";
/** Battito verso il server al massimo ogni 60 s, solo dopo tocchi o tasti veri. */
export const BATTITO_OGNI_MS = 60_000;
