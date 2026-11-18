// Pagamento (simulato) di un ordine del negozio pubblico. Chi paga mostra il token dell'ordine: se non corrisponde, 404.
// Il pagamento simulato esiste solo se l'azienda del negozio è la demo: con dati veri l'esito lo dirà il provider (non ancora attivo).
import { timingSafeEqual } from "node:crypto";
import { connection } from "next/server";
import { aggiornaStato } from "@/lib/archivio-azienda";
import { nelArchivio, pagaOrdine, rilasciaScaduti, type StatoCondiviso } from "@/lib/negozio-ordine";
import { archivioNegozioValido } from "@/lib/negozio-regole";
import { corpoPubblico, datiNegozio, risposta } from "@/lib/negozio-server";

const uguali = (a: string, b: string) => {
  const x = Buffer.from(a);
  const y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
};

type Esito = { stato: 200; ordineId: string; pagato: boolean; importo: number } | { stato: 404 | 409 | 503; error: string };

export async function POST(req: Request) {
  await connection();
  const corpo = await corpoPubblico(req);
  if (corpo instanceof Response) return corpo;
  const { ordineId, token, riuscito } = corpo;
  if (typeof ordineId !== "string" || !/^O-\d{1,10}$/.test(ordineId) || typeof token !== "string" || !/^[0-9a-f]{32}$/.test(token) || typeof riuscito !== "boolean") {
    return risposta({ error: "Richiesta non valida." }, 400);
  }
  const negozio = await datiNegozio();
  if (!negozio) return risposta({ error: "Il negozio non è disponibile in questo momento." }, 503);
  if (!negozio.demo) return risposta({ error: "Pagamento online non ancora attivo" }, 403);

  let r: Esito;
  try {
    r = await aggiornaStato<Esito>(negozio.id, (cur) => {
      const s = cur.state;
      if (!s || !archivioNegozioValido(s)) return { stored: cur, risultato: { stato: 503, error: "Il negozio non è disponibile in questo momento." }, nonScrivere: true };
      const ora = Date.now();
      const iniziale = s as unknown as StatoCondiviso;
      // Prima si liberano le riserve scadute (anche quella di questo ordine, se è passato troppo tempo)
      const st = rilasciaScaduti(iniziale, ora);
      const rilasciato = st !== iniziale;
      const scrive = (risultato: Esito) => ({ stored: rilasciato ? { ...cur, version: cur.version + 1, state: nelArchivio(s, st) } : cur, risultato, nonScrivere: !rilasciato });
      const o = st.orders.find((x) => x.id === ordineId);
      // Stessa risposta per ordine inesistente, senza token (ordini di altri canali) o con token sbagliato
      if (!o || typeof o.tokenNegozio !== "string" || !uguali(o.tokenNegozio, token)) return scrive({ stato: 404, error: "Ordine non trovato." });
      if (o.status !== "in attesa di pagamento") return scrive({ stato: 409, error: "L'ordine non è più in attesa di pagamento." });
      const fine = pagaOrdine(st, ordineId, riuscito, { user: o.customer, role: "cliente", device: "Provider di pagamento (simulato)" }, new Date(ora).toISOString());
      return { stored: { ...cur, version: cur.version + 1, state: nelArchivio(s, fine) }, risultato: { stato: 200, ordineId, pagato: riuscito, importo: o.amount } };
    });
  } catch (e) {
    console.error("Pagamento del negozio non registrato", e);
    return risposta({ error: "Non riesco a registrare il pagamento: riprova tra poco." }, 503);
  }
  if (r.stato === 200) return risposta({ ordineId: r.ordineId, pagato: r.pagato, importo: r.importo });
  return risposta({ error: r.error }, r.stato);
}
