// Pezzi comuni dei documenti legali pubblici (/privacy, /condizioni): forma del testo, fornitori, data della versione.
// Puro: le pagine li mostrano con DocumentoLegale. Piano 3, Task 1.

// Una sezione si mostra con i paragrafi e poi, se c'è, l'elenco puntato: il testo che introduce l'elenco è l'ultimo paragrafo.
// Nei paragrafi e nell'elenco [testo](indirizzo) diventa un link.
export type Sezione = { id: string; titolo: string; paragrafi: string[]; elenco?: string[] };

export type Documento = { titolo: string; versione: string /* AAAA-MM-GG, da consensi.ts */; sezioni: Sezione[] };

export type Fornitore = { nome: string; cosa: string; dove: string; garanzia: string; soloSe?: string };

const FUORI_UE = "decisione di adeguatezza (EU-US Data Privacy Framework) o clausole contrattuali standard, artt. 44 e seguenti del GDPR";

// Decisione del 26/11/2026: i fornitori si nominano. Supabase compare solo qui e nell'accordo, mai altrove.
export const FORNITORI: Fornitore[] = [
  { nome: "Vercel", cosa: "hosting del gestionale e delle sue funzioni, controllo anti-robot (BotID)", dove: "Stati Uniti", garanzia: FUORI_UE },
  { nome: "Supabase", cosa: "database e spazio per i file", dove: "Unione europea (Francoforte, Germania)", garanzia: "i dati restano su server nell'Unione europea" },
  { nome: "Stripe", cosa: "pagamento dell'abbonamento", dove: "Unione europea e Stati Uniti", garanzia: FUORI_UE },
  { nome: "Resend", cosa: "invio delle email del servizio", dove: "Stati Uniti", garanzia: FUORI_UE },
  {
    nome: "eBay",
    cosa: "pubblicazione degli annunci e ricezione degli ordini sul conto eBay dell'azienda",
    dove: "Unione europea e Stati Uniti",
    garanzia: FUORI_UE,
    soloSe: "l'azienda collega il suo account eBay",
  },
];

const MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];

/** "2026-11-27" → "27 novembre 2026". È una data senza ora: niente fusi orari. */
export function dataVersione(v: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(v);
  const mese = m ? MESI[Number(m[2]) - 1] : undefined;
  if (!m || !mese) throw new Error(`Versione non valida: ${v}`);
  return `${Number(m[3])} ${mese} ${m[1]}`;
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
