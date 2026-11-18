// Password sbagliate per account (accesso con email): il limite per indirizzo IP non basta, chi cambia IP a ogni
// tentativo lo aggira. Dopo 10 password sbagliate in 15 minuti per lo stesso account, l'accesso a quell'account è
// rifiutato per 15 minuti (anche con la password giusta). Vale anche per email che non esistono, così la risposta
// non dice quali account ci sono. Il secondo fattore ha già il suo blocco per account in Better Auth (10 errori, 15 min).
//
// Il conto parte all'ARRIVO della richiesta (prenota, sincrono: nessuna attesa fra controllo e conteggio), così 20
// richieste parallele non passano tutte il controllo: errori recenti + tentativi in corso non superano mai il massimo.
// L'esito (password sbagliata, giusta, altro) poi trasforma la prenotazione in errore o la libera. Una prenotazione senza
// esito (errore imprevisto del server) scade da sola dopo IN_VOLO_MS.
//
// Memoria limitata: al massimo maxVoci account. Non si dimentica MAI un account bloccato, con errori recenti o con
// tentativi in corso (inondare il server di email a caso non azzera il conto di nessuno); se è tutto pieno di account
// così, le email nuove si rifiutano (429) finché qualcuno non si libera. Puro.
export const ACCOUNT_ERRORI_MAX = 10;
export const ACCOUNT_FINESTRA_MS = 15 * 60_000;
export const ACCOUNT_BLOCCO_MS = 15 * 60_000;
export const IN_VOLO_MS = 30_000;
export const MAX_VOCI = 10_000;

export type StatoAccount = { errori: number[]; bloccatoFino: number | null; inVolo: number[] };
export type Conti = Map<string, StatoAccount>;

const recenti = (s: StatoAccount, ora: number) => s.errori.filter((t) => ora - t < ACCOUNT_FINESTRA_MS && t <= ora);
const inVoloVivi = (s: StatoAccount, ora: number) => s.inVolo.filter((t) => ora - t < IN_VOLO_MS && t <= ora);

export function accountBloccato(s: StatoAccount | undefined, ora: number): boolean {
  return !!s && s.bloccatoFino !== null && s.bloccatoFino > ora;
}

/** Da ricordare: bloccato, con errori recenti o con tentativi in corso. Gli altri si possono dimenticare. */
export function daRicordare(s: StatoAccount, ora: number): boolean {
  return accountBloccato(s, ora) || recenti(s, ora).length > 0 || inVoloVivi(s, ora).length > 0;
}

function pulisci(conti: Conti, ora: number) {
  for (const [k, s] of conti) if (!daRicordare(s, ora)) conti.delete(k);
}

export type Prenotazione = "ok" | "bloccato" | "pieno";

/** All'arrivo di un accesso con email: controlla e conta il tentativo in corso, nello stesso passo (sincrono). */
export function prenota(conti: Conti, k: string, ora: number, maxVoci = MAX_VOCI): Prenotazione {
  let s = conti.get(k);
  if (s) {
    if (accountBloccato(s, ora)) return "bloccato";
    s.errori = recenti(s, ora);
    s.inVolo = inVoloVivi(s, ora);
    if (s.errori.length + s.inVolo.length >= ACCOUNT_ERRORI_MAX) return "bloccato";
  } else {
    if (conti.size >= maxVoci) pulisci(conti, ora);
    if (conti.size >= maxVoci) return "pieno";
    s = { errori: [], bloccatoFino: null, inVolo: [] };
    conti.set(k, s);
  }
  s.inVolo.push(ora);
  return "ok";
}

export type Esito = "sbagliata" | "giusta" | "altro";

/** Dopo la verifica: la prenotazione diventa un errore (password sbagliata) o si libera. true se l'account si è appena bloccato. */
export function chiudi(conti: Conti, k: string, ora: number, esito: Esito): boolean {
  const s = conti.get(k);
  if (!s) return false;
  // Si toglie la prenotazione più vecchia (l'ordine non conta: serve il numero)
  const vivi = inVoloVivi(s, ora);
  vivi.shift();
  s.inVolo = vivi;
  let appena = false;
  if (esito === "sbagliata" && !accountBloccato(s, ora)) {
    const errori = [...recenti(s, ora), ora];
    if (errori.length >= ACCOUNT_ERRORI_MAX) {
      s.errori = [];
      s.bloccatoFino = ora + ACCOUNT_BLOCCO_MS;
      appena = true;
    } else s.errori = errori;
  } else if (esito === "giusta") {
    // Password giusta: si riparte da zero (il secondo fattore ha il suo blocco per account)
    s.errori = [];
  }
  if (!daRicordare(s, ora)) conti.delete(k);
  return appena;
}

export const chiaveAccount = (email: unknown): string | null => (typeof email === "string" && email.trim() ? email.trim().toLowerCase().slice(0, 320) : null);
