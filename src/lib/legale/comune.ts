// Pezzi comuni dei documenti legali pubblici (/privacy, /condizioni): forma del testo, fornitori, data della versione.
// Puro: le pagine li mostrano con DocumentoLegale. Piano 3, Task 1.
import { MESI } from "../periodo.ts";

/** Paragrafi e poi, se c'è, elenco puntato: il testo che introduce l'elenco è l'ultimo paragrafo. */
export type Blocco = { paragrafi: string[]; elenco?: string[] };

// Una sezione si mostra con i paragrafi, poi l'elenco, poi i blocchi di `dopo` nello stesso ordine
// (per il testo che viene dopo un elenco, o per un secondo elenco). Ovunque [testo](indirizzo) diventa un link.
export type Sezione = { id: string; titolo: string; paragrafi: string[]; elenco?: string[]; dopo?: Blocco[] };

export type Documento = { titolo: string; versione: string /* AAAA-MM-GG, da consensi.ts */; sezioni: Sezione[] };

export type Fornitore = { nome: string; cosa: string; dove: string; garanzia: string; soloSe?: string };

const FUORI_UE = "decisione di adeguatezza (EU-US Data Privacy Framework) o clausole contrattuali standard, artt. 44 e seguenti del GDPR";

// Sub-responsabili: trattano i dati per conto nostro (e, per i dati dell'azienda, come sub-responsabili).
// Decisione del 26/11/2026: si nominano. Supabase compare solo qui e nell'accordo, mai altrove.
// Le funzioni di Vercel girano negli Stati Uniti (iad1); il dominio di invio di Resend è in eu-west-1.
export const FORNITORI: Fornitore[] = [
  { nome: "Vercel", cosa: "hosting ed elaborazione del gestionale, controllo anti-robot (BotID)", dove: "Stati Uniti", garanzia: FUORI_UE },
  { nome: "Supabase", cosa: "database e spazio per i file", dove: "Unione europea (Francoforte, Germania)", garanzia: "dati conservati su server nell'Unione europea" },
  {
    nome: "Stripe",
    cosa: "pagamento dell'abbonamento; per alcuni dati, come la prevenzione delle frodi, Stripe è titolare autonomo secondo la sua informativa",
    dove: "Unione europea e Stati Uniti",
    garanzia: FUORI_UE,
  },
  { nome: "Resend", cosa: "invio delle email del servizio", dove: "Unione europea (Irlanda) per l'invio; società con sede negli Stati Uniti", garanzia: FUORI_UE },
];

// Servizi che l'azienda collega con un suo account: non sono nostri fornitori. Su istruzione dell'azienda passiamo
// loro i dati che servono; li trattano come titolari autonomi. Openapi: visura-server.ts usa il token dell'azienda.
const AUTONOMO = "titolare autonomo dei dati che riceve, secondo la sua informativa";
export const SERVIZI_COLLEGATI: Fornitore[] = [
  {
    nome: "eBay",
    cosa: "pubblicazione degli annunci dei ricambi e ricezione degli ordini",
    dove: "come indicato nella sua informativa",
    garanzia: AUTONOMO,
    soloSe: "l'azienda collega il suo account eBay",
  },
  {
    nome: "Openapi",
    cosa: "visure PRA dei veicoli",
    dove: "come indicato nella sua informativa",
    garanzia: AUTONOMO,
    soloSe: "l'azienda collega il suo account Openapi",
  },
];

/** "2026-11-27" → "27 novembre 2026". È una data senza ora: niente fusi orari. Una data impossibile è un errore. */
export function dataVersione(v: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(v);
  const [anno, mese, giorno] = m ? [Number(m[1]), Number(m[2]), Number(m[3])] : [0, 0, 0];
  // Giorno 0 del mese dopo = ultimo giorno del mese (calendario UTC: nessun fuso)
  const giorniDelMese = mese >= 1 && mese <= 12 ? new Date(Date.UTC(anno, mese, 0)).getUTCDate() : 0;
  if (!m || giorno < 1 || giorno > giorniDelMese) throw new Error(`Versione non valida: ${v}`);
  return `${giorno} ${MESI[mese - 1]} ${anno}`;
}

export type PezzoTesto = string | { testo: string; href: string };

/** Divide un paragrafo in testo e link: "[testo](indirizzo)" diventa { testo, href }. */
export function pezziTesto(s: string): PezzoTesto[] {
  const pezzi: PezzoTesto[] = [];
  let da = 0;
  for (const m of s.matchAll(/\[([^\]]+)\]\(([^)\s]+)\)/g)) {
    if (m.index > da) pezzi.push(s.slice(da, m.index));
    pezzi.push({ testo: m[1], href: m[2] });
    da = m.index + m[0].length;
  }
  if (da < s.length) pezzi.push(s.slice(da));
  return pezzi;
}
