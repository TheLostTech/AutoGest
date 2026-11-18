// Regole dei tentativi di PIN sui dispositivi condivisi. Pure, senza database: le usa il plugin pin-dispositivo.
// Un PIN ha solo 4 cifre: la protezione sono i blocchi (per nome e per dispositivo) e il legame col dispositivo.

/** Errori di fila su un nome prima del blocco. */
export const PIN_ERRORI_UTENTE = 5;
/** Durata del blocco di un nome: 15 minuti, su tutti i dispositivi. */
export const PIN_BLOCCO_UTENTE_MS = 900_000;
/** Errori su un dispositivo (qualsiasi nome) dentro la finestra che bloccano il dispositivo. */
export const PIN_ERRORI_DISPOSITIVO = 20;
/** Finestra in cui si contano gli errori del dispositivo: 15 minuti. */
export const PIN_FINESTRA_DISPOSITIVO_MS = 900_000;

export type StatoPinUtente = { errori: number; bloccatoFino: number | null };
export type StatoPinDispositivo = { errori: number[] /* istanti */; bloccato: boolean };
export type EsitoPin = "ok" | "sbagliato" | "utente-bloccato" | "dispositivo-bloccato";

type Stato = { utente: StatoPinUtente; dispositivo: StatoPinDispositivo };

/** Esattamente 4 cifre 0-9. */
export function pinValido(pin: string): boolean {
  return /^[0-9]{4}$/.test(pin);
}

/** Blocco in corso prima di valutare il PIN: il dispositivo bloccato vince sul nome bloccato. */
export function bloccoAttivo(s: Stato, ora: number): "utente-bloccato" | "dispositivo-bloccato" | null {
  if (s.dispositivo.bloccato) return "dispositivo-bloccato";
  if (s.utente.bloccatoFino !== null && ora < s.utente.bloccatoFino) return "utente-bloccato";
  return null;
}

/**
 * Applica un tentativo. Con un blocco in corso il PIN non si valuta e nulla cambia.
 * Corretto: errori del nome a zero (quelli del dispositivo restano). Sbagliato: +1 sul nome (al quinto blocco di
 * 15 minuti) e un istante in più sul dispositivo (al ventesimo nella finestra di 15 minuti il dispositivo si blocca).
 */
export function dopoTentativo(s: Stato, corretto: boolean, ora: number): Stato & { esito: EsitoPin } {
  const blocco = bloccoAttivo(s, ora);
  if (blocco) return { utente: s.utente, dispositivo: s.dispositivo, esito: blocco };

  if (corretto) return { utente: { errori: 0, bloccatoFino: null }, dispositivo: s.dispositivo, esito: "ok" };

  // Blocco del nome scaduto: si riparte da zero
  const prima = s.utente.bloccatoFino !== null ? 0 : s.utente.errori;
  const errori = prima + 1;
  const utente: StatoPinUtente = { errori, bloccatoFino: errori >= PIN_ERRORI_UTENTE ? ora + PIN_BLOCCO_UTENTE_MS : null };

  const recenti = [...s.dispositivo.errori.filter((t) => ora - t < PIN_FINESTRA_DISPOSITIVO_MS), ora];
  const dispositivo: StatoPinDispositivo = { errori: recenti, bloccato: recenti.length >= PIN_ERRORI_DISPOSITIVO };

  return { utente, dispositivo, esito: "sbagliato" };
}
