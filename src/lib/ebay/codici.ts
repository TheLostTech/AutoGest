// Codici di errore del collegamento eBay che viaggiano nell'indirizzo (?ebay=errore&codice=…).
// Nell'indirizzo mai testo libero: la pagina mostra solo questi testi fissi; il dettaglio resta sul server
// (archivio.errore → StatoPonte.errore). Modulo puro.

export const CODICI_COLLEGAMENTO = ["stato", "rifiutato", "token", "esaurito", "politiche", "chiavi", "imprevisto"] as const;
export type CodiceCollegamento = (typeof CODICI_COLLEGAMENTO)[number];

const TESTI: Record<CodiceCollegamento, string> = {
  stato: "Il ritorno da eBay non corrisponde a una richiesta partita da qui, oppure è scaduto. Cosa fare: tocca di nuovo «Collega account eBay».",
  rifiutato: "Il collegamento su eBay non è stato autorizzato. Cosa fare: tocca di nuovo «Collega account eBay» e acconsenti.",
  token: "eBay non ha dato il permesso di accesso al conto. Cosa fare: controlla App ID, Cert ID e RuName, poi tocca di nuovo «Collega account eBay».",
  esaurito: "Conto collegato, ma eBay non ha attivato «esaurito». Cosa fare: tocca di nuovo «Collega account eBay».",
  politiche: "Conto collegato, ma politiche o magazzino non sono pronti su eBay. Cosa fare: riprova tra qualche minuto con «Collega account eBay».",
  chiavi: "eBay non è in ambiente Sandbox con le chiavi complete. Cosa fare: scegli Sandbox, inserisci App ID, Cert ID e RuName e salva.",
  imprevisto: "Il collegamento con eBay non è riuscito. Cosa fare: riprova tra poco con «Collega account eBay».",
};

const conosciuto = (c: string): c is CodiceCollegamento => (CODICI_COLLEGAMENTO as readonly string[]).includes(c);

/** Testo fisso per il codice; qualsiasi altro valore (anche testo scritto a mano nel link) dà il testo generico. */
export function testoErroreCollegamento(codice: string | null | undefined): string {
  return codice && conosciuto(codice) ? TESTI[codice] : TESTI.imprevisto;
}
