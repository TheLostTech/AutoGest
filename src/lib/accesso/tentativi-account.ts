// Password sbagliate per account (accesso con email): il limite per indirizzo IP non basta, chi cambia IP a ogni
// tentativo lo aggira. Dopo 10 password sbagliate in 15 minuti per lo stesso account, l'accesso a quell'account è
// rifiutato per 15 minuti (anche con la password giusta). Il secondo fattore ha già il suo blocco per account in
// Better Auth (10 codici sbagliati di fila, 15 minuti).
//
// Si conta solo per gli account che esistono: i conti sono al massimo quanti gli utenti, niente da dimenticare a forza
// e niente "memoria piena" che un attaccante possa usare per bloccare tutti. Le email che non esistono finiscono in
// UN solo contatore comune (30 al minuto): riempirlo rifiuta solo altri tentativi su email inesistenti.
//
// Il tentativo si conta all'ARRIVO (prenota, sincrono: nessuna attesa fra controllo e conteggio), così 20 richieste
// parallele non passano tutte: errori recenti + tentativi in corso non superano mai il massimo. Ogni prenotazione ha
// il suo gettone; l'esito (password sbagliata, giusta, altro) toglie proprio quel gettone e, se sbagliata, conta un
// errore. Un gettone rimasto senza esito (errore imprevisto del server) scade da solo dopo IN_VOLO_MS.
// Un timestamp nel futuro (orologi di istanze diverse, o richieste che prendono il lock fuori ordine) non si scarta mai:
// si scartano solo le voci troppo vecchie. Un account bloccato mentre la richiesta era in corso resta bloccato. Puro.
export const ACCOUNT_ERRORI_MAX = 10;
export const ACCOUNT_FINESTRA_MS = 15 * 60_000;
export const ACCOUNT_BLOCCO_MS = 15 * 60_000;
export const IN_VOLO_MS = 60_000;
export const SCONOSCIUTI_MAX = 30;
export const SCONOSCIUTI_FINESTRA_MS = 60_000;

export type StatoAccount = { errori: number[]; bloccatoFino: number | null; inVolo: Map<string, number> };
export type Conti = Map<string, StatoAccount>;

const recenti = (s: StatoAccount, ora: number) => s.errori.filter((t) => ora - t < ACCOUNT_FINESTRA_MS);
function scadiInVolo(s: StatoAccount, ora: number) {
  for (const [g, t] of s.inVolo) if (!(ora - t < IN_VOLO_MS)) s.inVolo.delete(g);
}

export function accountBloccato(s: StatoAccount | undefined, ora: number): boolean {
  return !!s && s.bloccatoFino !== null && s.bloccatoFino > ora;
}

function daRicordare(s: StatoAccount, ora: number): boolean {
  scadiInVolo(s, ora);
  return accountBloccato(s, ora) || recenti(s, ora).length > 0 || s.inVolo.size > 0;
}

/** All'arrivo di un accesso con email di un account che esiste: controlla e prenota, nello stesso passo (sincrono). */
export function prenota(conti: Conti, k: string, gettone: string, ora: number): "ok" | "bloccato" {
  let s = conti.get(k);
  if (!s) conti.set(k, (s = { errori: [], bloccatoFino: null, inVolo: new Map() }));
  if (accountBloccato(s, ora)) return "bloccato";
  s.errori = recenti(s, ora);
  scadiInVolo(s, ora);
  if (s.errori.length + s.inVolo.size >= ACCOUNT_ERRORI_MAX) return "bloccato";
  s.inVolo.set(gettone, ora);
  return "ok";
}

export type Esito = "sbagliata" | "giusta" | "altro";

/** Dopo la verifica: toglie esattamente quel gettone e, se la password era sbagliata, conta l'errore. true se l'account si è appena bloccato. */
export function chiudi(conti: Conti, k: string, gettone: string, ora: number, esito: Esito): boolean {
  const s = conti.get(k);
  if (!s) return false;
  const presente = s.inVolo.delete(gettone);
  let appena = false;
  if (presente && esito === "sbagliata" && !accountBloccato(s, ora)) {
    const errori = [...recenti(s, ora), ora];
    if (errori.length >= ACCOUNT_ERRORI_MAX) {
      s.errori = [];
      s.bloccatoFino = ora + ACCOUNT_BLOCCO_MS;
      appena = true;
    } else s.errori = errori;
  } else if (presente && esito === "giusta" && !accountBloccato(s, ora)) {
    // Password giusta: si riparte da zero (il secondo fattore ha il suo blocco per account)
    s.errori = [];
  }
  if (!daRicordare(s, ora)) conti.delete(k);
  return appena;
}

/** Email che non esistono: un solo contatore comune a finestra mobile. Conta all'arrivo; false = rifiutare (429). */
export function tentativoSconosciuto(comune: number[], ora: number): boolean {
  const vivi = comune.filter((t) => ora - t < SCONOSCIUTI_FINESTRA_MS && t <= ora);
  comune.length = 0;
  comune.push(...vivi);
  if (comune.length >= SCONOSCIUTI_MAX) return false;
  comune.push(ora);
  return true;
}

export const chiaveAccount = (email: unknown): string | null => (typeof email === "string" && email.trim() ? email.trim().toLowerCase().slice(0, 320) : null);
