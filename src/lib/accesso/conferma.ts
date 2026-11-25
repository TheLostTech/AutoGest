// Conferma dell'email del titolare: costanti e messaggi comuni a server (auth/conferma-titolare.ts) e pagine
// (/accesso, /registrati). Puro: niente rete, disco o React.

/** Dove porta il link dell'email. Se il link è scaduto o non valido Better Auth aggiunge &error=CODICE. */
export const RITORNO_CONFERMA = "/accesso?confermata=1";
export const CODICE_DA_CONFERMARE = "EMAIL_DA_CONFERMARE";
export const MESSAGGIO_DA_CONFERMARE = "Conferma prima la tua email: ti abbiamo mandato un link. Non lo trovi? Rimandalo da qui.";
export const EMAIL_CONFERMATA = "Email confermata: la prova di 15 giorni è iniziata.";

export type Avviso = { tono: "ok" | "danger"; testo: string };

/** Avviso della pagina di accesso all'arrivo dal link dell'email (?confermata=1, con &error=… se non è andato). */
export function avvisoConferma(confermata: string | undefined, errore: string | undefined): Avviso | null {
  if (confermata !== "1") return null;
  if (!errore) return { tono: "ok", testo: EMAIL_CONFERMATA };
  if (errore === "TOKEN_EXPIRED") {
    return { tono: "danger", testo: "Il link di conferma è scaduto: vale 48 ore. Accedi con email e password per riceverne uno nuovo." };
  }
  return {
    tono: "danger",
    testo: "Il link di conferma non è valido. Se ti sei registrato più di una volta, usa il link dell'ultima email; altrimenti accedi con email e password per riceverne uno nuovo.",
  };
}

/** Esito di "Rimanda l'email", dallo stato HTTP della risposta (0 = rete). */
export function esitoRimando(stato: number): Avviso {
  if (stato >= 200 && stato < 300) return { tono: "ok", testo: "Ti abbiamo mandato un nuovo link. Controlla la posta, anche quella indesiderata." };
  if (stato === 429) return { tono: "danger", testo: "Hai chiesto troppe email in poco tempo: riprova tra un minuto." };
  if (stato === 0) return { tono: "danger", testo: "Non riesco a collegarmi al server. Controlla la rete e riprova." };
  return { tono: "danger", testo: "Non sono riuscito a mandare l'email. Riprova tra qualche minuto." };
}
