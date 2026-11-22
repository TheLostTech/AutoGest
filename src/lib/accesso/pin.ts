// Regole dei tentativi di PIN sui dispositivi condivisi. Pure, senza database: le usa il plugin pin-dispositivo.
// Un PIN ha solo 4 cifre: la protezione sono i blocchi (per nome e per dispositivo) e il legame col dispositivo.

/** Errori di fila su un nome prima del blocco. */
export const PIN_ERRORI_UTENTE = 5;
/** Durata del blocco di un nome: 15 minuti, su tutti i dispositivi. */
export const PIN_BLOCCO_UTENTE_MS = 900_000;
/** Errori su un dispositivo (qualsiasi nome) dentro la finestra breve che bloccano il dispositivo. */
export const PIN_ERRORI_DISPOSITIVO = 20;
/** Finestra breve in cui si contano gli errori del dispositivo: 15 minuti. */
export const PIN_FINESTRA_DISPOSITIVO_MS = 900_000;
/** Errori su un dispositivo in un giorno che lo bloccano (attacco lento, sotto la soglia dei 15 minuti). */
export const PIN_ERRORI_DISPOSITIVO_GIORNO = 50;
/** Finestra lunga: 24 ore (errori del dispositivo e cicli di blocco di un nome). */
export const PIN_GIORNO_MS = 86_400_000;
/** Cicli di blocco di un nome in 24 ore che disattivano il suo PIN fino a un nuovo PIN dal responsabile. */
export const PIN_BLOCCHI_DISATTIVA = 3;

export type StatoPinUtente = {
  errori: number;
  bloccatoFino: number | null;
  blocchi: number[]; // istanti dei blocchi di 15 minuti (ultime 24 ore)
  disattivato: boolean; // PIN spento finché il responsabile non ne imposta uno nuovo
};
export type StatoPinDispositivo = { errori: number[] /* istanti, ultime 24 ore */; bloccato: boolean };
export type EsitoPin = "ok" | "sbagliato" | "utente-bloccato" | "dispositivo-bloccato";

type Stato = { utente: StatoPinUtente; dispositivo: StatoPinDispositivo };

/** Esattamente 4 cifre 0-9. */
export function pinValido(pin: string): boolean {
  return /^[0-9]{4}$/.test(pin);
}

/** Blocco in corso prima di valutare il PIN: il dispositivo bloccato vince sul nome bloccato o disattivato. */
export function bloccoAttivo(s: Stato, ora: number): "utente-bloccato" | "dispositivo-bloccato" | null {
  if (s.dispositivo.bloccato) return "dispositivo-bloccato";
  if (s.utente.disattivato) return "utente-bloccato";
  if (s.utente.bloccatoFino !== null && ora < s.utente.bloccatoFino) return "utente-bloccato";
  return null;
}

/**
 * Applica un tentativo. Con un blocco in corso il PIN non si valuta e nulla cambia.
 * Corretto: errori del nome a zero (quelli del dispositivo e i cicli di blocco restano).
 * Sbagliato: +1 sul nome (al quinto blocco di 15 minuti; al terzo blocco in 24 ore PIN disattivato) e un istante in
 * più sul dispositivo (20 in 15 minuti o 50 in 24 ore: dispositivo bloccato finché il responsabile non lo sblocca).
 */
export function dopoTentativo(s: Stato, corretto: boolean, ora: number): Stato & { esito: EsitoPin } {
  const blocco = bloccoAttivo(s, ora);
  if (blocco) return { utente: s.utente, dispositivo: s.dispositivo, esito: blocco };

  const blocchi = s.utente.blocchi.filter((t) => ora - t < PIN_GIORNO_MS);
  if (corretto) return { utente: { errori: 0, bloccatoFino: null, blocchi, disattivato: false }, dispositivo: s.dispositivo, esito: "ok" };

  // Blocco del nome scaduto: si riparte da zero
  const prima = s.utente.bloccatoFino !== null ? 0 : s.utente.errori;
  const errori = prima + 1;
  const scatta = errori >= PIN_ERRORI_UTENTE;
  const nuoviBlocchi = scatta ? [...blocchi, ora] : blocchi;
  const utente: StatoPinUtente = {
    errori,
    bloccatoFino: scatta ? ora + PIN_BLOCCO_UTENTE_MS : null,
    blocchi: nuoviBlocchi,
    disattivato: nuoviBlocchi.length >= PIN_BLOCCHI_DISATTIVA,
  };

  const recenti = [...s.dispositivo.errori.filter((t) => ora - t < PIN_GIORNO_MS), ora];
  const inBreve = recenti.filter((t) => ora - t < PIN_FINESTRA_DISPOSITIVO_MS).length;
  const dispositivo: StatoPinDispositivo = {
    errori: recenti,
    bloccato: inBreve >= PIN_ERRORI_DISPOSITIVO || recenti.length >= PIN_ERRORI_DISPOSITIVO_GIORNO,
  };

  return { utente, dispositivo, esito: "sbagliato" };
}
