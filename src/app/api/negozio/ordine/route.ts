// Ordine dal negozio pubblico: senza accesso, solo stesso sito, JSON, al massimo 2 KB e 10 annunci.
// Scrive nell'archivio dell'azienda del negozio con lo stesso blocco dei dispositivi (aggiornaStato).
// Dentro il blocco, a ogni richiesta: le riserve non pagate da più di 30 minuti si rilasciano, e non si accettano più di
// 20 ordini in attesa. Annunci che non esistono o non sono online: 400 senza scrivere nulla.
import { randomBytes } from "node:crypto";
import { connection } from "next/server";
import { aggiornaStato } from "@/lib/archivio-azienda";
import { nelArchivio, ordineNegozio, rilasciaScaduti, type StatoCondiviso } from "@/lib/negozio-ordine";
import { archivioNegozioValido, decidiOrdine, decidiPagamento } from "@/lib/negozio-regole";
import { corpoPubblico, datiNegozio, risposta } from "@/lib/negozio-server";

const MAX_ANNUNCI = 10;

type Esito = { stato: 200; ordineId: string; token: string; importo: number } | { stato: 409; conflicts: string[] } | { stato: 400 | 429 | 503; error: string };

export async function POST(req: Request) {
  await connection();
  const corpo = await corpoPubblico(req);
  if (corpo instanceof Response) return corpo;
  const ids = corpo.annuncioIds;
  if (!Array.isArray(ids) || ids.length < 1 || ids.length > MAX_ANNUNCI || !ids.every((x) => typeof x === "string" && /^A-\d{1,10}$/.test(x))) {
    return risposta({ error: "Carrello non valido." }, 400);
  }
  const nome = typeof corpo.nome === "string" ? corpo.nome.trim().slice(0, 80) : "";
  const consegna = corpo.consegna === "ritiro" ? "ritiro" : "corriere";
  const negozio = await datiNegozio();
  if (!negozio) return risposta({ error: "Il negozio non è disponibile in questo momento." }, 503);
  // Senza pagamento attivo non si riserva nulla: un ordine non pagabile bloccherebbe i pezzi per altri
  const dp = decidiPagamento(negozio.demo);
  if (!dp.ok) return risposta({ error: dp.error }, dp.stato);

  const cliente = nome || "Cliente online";
  const token = randomBytes(16).toString("hex");
  let r: Esito;
  try {
    r = await aggiornaStato<Esito>(negozio.id, (cur) => {
      const s = cur.state;
      if (!s || !archivioNegozioValido(s)) {
        return { stored: cur, risultato: { stato: 503, error: "Il negozio non è disponibile in questo momento." }, nonScrivere: true };
      }
      const ora = Date.now();
      const iniziale = s as unknown as StatoCondiviso;
      // Prima si liberano i pezzi delle riserve scadute; se è cambiato qualcosa si scrive anche quando l'ordine è rifiutato
      const st = rilasciaScaduti(iniziale, ora);
      const rilasciato = st !== iniziale;
      const d = decidiOrdine(st, ids as string[]);
      if (!d.ok) {
        return { stored: rilasciato ? { ...cur, version: cur.version + 1, state: nelArchivio(s, st) } : cur, risultato: { stato: d.stato, error: d.error }, nonScrivere: !rilasciato };
      }
      const e = ordineNegozio(st, { annuncioIds: ids as string[], cliente, consegna, attore: { user: cliente, role: "cliente", device: "Negozio online" } }, new Date(ora).toISOString());
      if (!e.ok) {
        // Conflitto vero su annunci online (pezzi finiti): resta una riga nel registro, come dal gestionale
        return { stored: { ...cur, version: cur.version + 1, state: nelArchivio(s, e.st) }, risultato: { stato: 409, conflicts: e.conflicts ?? [] } };
      }
      const ordini = e.st.orders.map((o) => (o.id === e.ordineId ? { ...o, tokenNegozio: token } : o));
      const importo = ordini.find((o) => o.id === e.ordineId)?.amount ?? 0;
      return { stored: { ...cur, version: cur.version + 1, state: nelArchivio(s, { ...e.st, orders: ordini }) }, risultato: { stato: 200, ordineId: e.ordineId, token, importo } };
    });
  } catch (e) {
    console.error("Ordine del negozio non registrato", e);
    return risposta({ error: "Non riesco a registrare l'ordine: riprova tra poco." }, 503);
  }
  if (r.stato === 200) return risposta({ ordineId: r.ordineId, token: r.token, importo: r.importo, pagamentoAttivo: negozio.demo });
  if (r.stato === 409) return risposta({ error: "Ricambio non più disponibile", conflicts: r.conflicts }, 409);
  return risposta({ error: r.error }, r.stato);
}
