// Pagamento (simulato) di un ordine del negozio pubblico. Chi paga mostra il token dell'ordine: se non corrisponde, 404.
import { timingSafeEqual } from "node:crypto";
import { connection } from "next/server";
import { aggiornaStato } from "@/lib/archivio-azienda";
import { pagaOrdine, type StatoCondiviso } from "@/lib/negozio-ordine";
import { aziendaNegozio, corpoPubblico, risposta } from "@/lib/negozio-server";

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
  const az = await aziendaNegozio();
  if (!az) return risposta({ error: "Il negozio non è disponibile in questo momento." }, 503);

  let r: Esito;
  try {
    r = await aggiornaStato<Esito>(az, (cur) => {
      const s = cur.state as Record<string, unknown> | null;
      const ordini = s && Array.isArray(s.orders) ? (s.orders as { id: string; tokenNegozio?: string; status: string; amount: number; customer: string }[]) : null;
      if (!s || !ordini) return { stored: cur, risultato: { stato: 503, error: "Il negozio non è disponibile in questo momento." }, nonScrivere: true };
      const o = ordini.find((x) => x.id === ordineId);
      // Stessa risposta per ordine inesistente, senza token (ordini di altri canali) o con token sbagliato
      if (!o || typeof o.tokenNegozio !== "string" || !uguali(o.tokenNegozio, token)) {
        return { stored: cur, risultato: { stato: 404, error: "Ordine non trovato." }, nonScrivere: true };
      }
      if (o.status !== "in attesa di pagamento") {
        return { stored: cur, risultato: { stato: 409, error: "L'ordine non è più in attesa di pagamento." }, nonScrivere: true };
      }
      const st = pagaOrdine(s as unknown as StatoCondiviso, ordineId, riuscito, { user: o.customer, role: "cliente", device: "Provider di pagamento (simulato)" }, new Date().toISOString());
      const nuovo = { ...s, parts: st.parts, orders: st.orders, counters: { ...(s.counters as object), ...st.counters }, audit: st.audit, annunci: st.annunci };
      return { stored: { ...cur, version: cur.version + 1, state: nuovo }, risultato: { stato: 200, ordineId, pagato: riuscito, importo: o.amount } };
    });
  } catch (e) {
    console.error("Pagamento del negozio non registrato", e);
    return risposta({ error: "Non riesco a registrare il pagamento: riprova tra poco." }, 503);
  }
  if (r.stato === 200) return risposta({ ordineId: r.ordineId, pagato: r.pagato, importo: r.importo });
  return risposta({ error: r.error }, r.stato);
}
