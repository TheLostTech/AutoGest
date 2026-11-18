// Password sbagliate per account (accesso con email): il limite per indirizzo IP non basta, chi cambia IP a ogni
// tentativo lo aggira. Dopo 10 password sbagliate in 15 minuti per lo stesso account, l'accesso a quell'account è
// rifiutato per 15 minuti (anche con la password giusta). Vale anche per email che non esistono, così la risposta
// non dice quali account ci sono. Il secondo fattore ha già il suo blocco per account in Better Auth (10 errori, 15 min).
// Puro.
export const ACCOUNT_ERRORI_MAX = 10;
export const ACCOUNT_FINESTRA_MS = 15 * 60_000;
export const ACCOUNT_BLOCCO_MS = 15 * 60_000;

export type StatoAccount = { errori: number[]; bloccatoFino: number | null };
export const statoAccountVuoto = (): StatoAccount => ({ errori: [], bloccatoFino: null });

export function accountBloccato(s: StatoAccount | undefined, ora: number): boolean {
  return !!s && s.bloccatoFino !== null && s.bloccatoFino > ora;
}

/** Una password sbagliata: si conta nella finestra di 15 minuti; al decimo errore l'account si blocca. */
export function dopoPasswordSbagliata(s: StatoAccount | undefined, ora: number): { stato: StatoAccount; appenaBloccato: boolean } {
  const prima = s ?? statoAccountVuoto();
  if (accountBloccato(prima, ora)) return { stato: prima, appenaBloccato: false };
  const errori = [...prima.errori.filter((t) => ora - t < ACCOUNT_FINESTRA_MS && t <= ora), ora];
  if (errori.length >= ACCOUNT_ERRORI_MAX) return { stato: { errori: [], bloccatoFino: ora + ACCOUNT_BLOCCO_MS }, appenaBloccato: true };
  return { stato: { errori, bloccatoFino: null }, appenaBloccato: false };
}

/** Stato da tenere in memoria? (niente errori recenti e nessun blocco: si può dimenticare) */
export function daRicordare(s: StatoAccount, ora: number): boolean {
  return accountBloccato(s, ora) || s.errori.some((t) => ora - t < ACCOUNT_FINESTRA_MS);
}

export const chiaveAccount = (email: unknown): string | null => (typeof email === "string" && email.trim() ? email.trim().toLowerCase().slice(0, 320) : null);
