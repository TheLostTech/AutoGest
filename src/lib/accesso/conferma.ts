// Conferma dell'email del titolare: costanti, link e controlli comuni a server (auth/conferma-titolare.ts,
// /api/conferma) e pagine (/accesso, /registrati, /conferma). Puro: niente rete, disco o React.
// Per confermare serve la password scelta alla registrazione: chi rifà una registrazione in sospeso con la stessa
// email e un'altra password non si fa confermare l'account dal vero titolare che apre il link.
import { indirizzoPubblico } from "../email/indirizzo.ts";
import { PASSWORD_MAX } from "./registrazione.ts";

export const CODICE_DA_CONFERMARE = "EMAIL_DA_CONFERMARE";
export const MESSAGGIO_DA_CONFERMARE = "Conferma prima la tua email: ti abbiamo mandato un link. Non lo trovi? Rimandalo da qui.";
export const EMAIL_CONFERMATA = "Email confermata: la prova di 15 giorni è iniziata.";
export const PASSWORD_SBAGLIATA = "Password non corretta.";
export const LINK_NON_VALIDO = "Il link non è più valido: chiedi una nuova email dalla pagina di accesso.";

type Ambiente = Record<string, string | undefined>;

/**
 * Link dell'email: la nostra pagina /conferma con il gettone firmato da Better Auth. L'indirizzo è quello pubblico
 * (BETTER_AUTH_URL o Vercel). Solo fuori produzione, se manca, si prende dalla richiesta: in produzione l'host della
 * richiesta lo può scegliere chi la manda, e il link finirebbe su un altro sito.
 */
export function linkConferma(token: string, origineRichiesta: string | null, env: Ambiente = process.env): string {
  let origine = indirizzoPubblico(env);
  if (!origine) {
    if (env.NODE_ENV === "production") throw new Error("Indirizzo pubblico non configurato: imposta BETTER_AUTH_URL");
    origine = origineRichiesta;
  }
  if (!origine) throw new Error("Indirizzo del link di conferma non disponibile");
  return `${origine}/conferma?token=${encodeURIComponent(token)}`;
}

/** Corpo di POST /api/conferma: il gettone dell'email e la password scelta alla registrazione. */
export function richiestaConferma(corpo: unknown): { token: string; password: string } | null {
  if (!corpo || typeof corpo !== "object" || Array.isArray(corpo)) return null;
  const { token, password } = corpo as { token?: unknown; password?: unknown };
  if (typeof token !== "string" || typeof password !== "string") return null;
  const t = token.trim();
  if (!t || t.length > 4096 || !password || password.length > PASSWORD_MAX) return null;
  return { token: t, password };
}

// Email di conferma per un titolare in attesa: al massimo 5 in 24 ore e almeno un minuto tra una e l'altra. Il rimando
// non ha BotID: senza tetto chi registra con l'email di altri potrebbe farle arrivare di continuo dal nostro dominio.
export const INVII_CONFERMA_MAX = 5;
export const INVII_CONFERMA_FINESTRA_MS = 24 * 3600_000;
export const INVII_CONFERMA_PAUSA_MS = 60_000;

/** Orari degli invii aggiornati se si può mandare adesso, altrimenti null. Valori rotti o nel futuro non contano. */
export function invioConferma(invii: unknown, ora: number): number[] | null {
  const vivi = (Array.isArray(invii) ? invii : []).filter((t): t is number => typeof t === "number" && t <= ora && ora - t < INVII_CONFERMA_FINESTRA_MS);
  if (vivi.length >= INVII_CONFERMA_MAX) return null;
  if (vivi.some((t) => ora - t < INVII_CONFERMA_PAUSA_MS)) return null;
  return [...vivi, ora];
}

export type Avviso = { tono: "ok" | "danger"; testo: string };

/** Esito di "Rimanda l'email", dallo stato HTTP della risposta (0 = rete). */
export function esitoRimando(stato: number): Avviso {
  // La risposta è la stessa per tutti (e oltre il tetto non parte nulla): il testo non promette un invio
  if (stato >= 200 && stato < 300) return { tono: "ok", testo: "Se la registrazione aspetta la conferma, il nuovo link arriva entro pochi minuti: controlla anche la posta indesiderata. Puoi chiederlo una volta al minuto, al massimo 5 volte al giorno." };
  if (stato === 429) return { tono: "danger", testo: "Hai chiesto troppe email in poco tempo: riprova tra un minuto." };
  if (stato === 0) return { tono: "danger", testo: "Non riesco a collegarmi al server. Controlla la rete e riprova." };
  return { tono: "danger", testo: "Non sono riuscito a mandare l'email. Riprova tra qualche minuto." };
}
