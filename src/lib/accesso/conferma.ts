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

export type Avviso = { tono: "ok" | "danger"; testo: string };

/** Esito di "Rimanda l'email", dallo stato HTTP della risposta (0 = rete). */
export function esitoRimando(stato: number): Avviso {
  if (stato >= 200 && stato < 300) return { tono: "ok", testo: "Ti abbiamo mandato un nuovo link. Controlla la posta, anche quella indesiderata." };
  if (stato === 429) return { tono: "danger", testo: "Hai chiesto troppe email in poco tempo: riprova tra un minuto." };
  if (stato === 0) return { tono: "danger", testo: "Non riesco a collegarmi al server. Controlla la rete e riprova." };
  return { tono: "danger", testo: "Non sono riuscito a mandare l'email. Riprova tra qualche minuto." };
}
