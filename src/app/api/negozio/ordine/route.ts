// Ordine dal negozio pubblico: senza accesso, solo stesso sito, JSON, al massimo 2 KB e 10 annunci.
// Scrive nell'archivio dell'azienda del negozio con lo stesso blocco dei dispositivi (aggiornaStato).
import { randomBytes } from "node:crypto";
import { connection } from "next/server";
import { aggiornaStato } from "@/lib/archivio-azienda";
import { ordineNegozio, type StatoCondiviso } from "@/lib/negozio-ordine";
import { aziendaNegozio, corpoPubblico, risposta } from "@/lib/negozio-server";

const MAX_ANNUNCI = 10;

type Esito = { stato: 200; ordineId: string; token: string; importo: number } | { stato: 409; conflicts: string[] } | { stato: 400 | 503; error: string };

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
  const az = await aziendaNegozio();
  if (!az) return risposta({ error: "Il negozio non è disponibile in questo momento." }, 503);

  const cliente = nome || "Cliente online";
  const token = randomBytes(16).toString("hex");
  let r: Esito;
  try {
    r = await aggiornaStato<Esito>(az, (cur) => {
      const s = cur.state as Record<string, unknown> | null;
      if (!s || !["vehicles", "parts", "annunci", "orders", "audit"].every((k) => Array.isArray(s[k])) || typeof (s.counters as { order?: unknown } | undefined)?.order !== "number") {
        return { stored: cur, risultato: { stato: 503, error: "Il negozio non è disponibile in questo momento." }, nonScrivere: true };
      }
      const e = ordineNegozio(
        s as unknown as StatoCondiviso,
        { annuncioIds: ids as string[], cliente, consegna, attore: { user: cliente, role: "cliente", device: "Negozio online" } },
        new Date().toISOString(),
      );
      // Solo le chiavi che l'ordine cambia: le altre dell'archivio restano com'erano
      const nuovo = { ...s, parts: e.st.parts, orders: e.st.orders, counters: { ...(s.counters as object), ...e.st.counters }, audit: e.st.audit, annunci: e.st.annunci };
      if (!e.ok) {
        // Il rifiuto lascia una riga nel registro, come dal gestionale
        return { stored: { ...cur, version: cur.version + 1, state: nuovo }, risultato: { stato: 409, conflicts: e.conflicts ?? [] } };
      }
      const ordini = e.st.orders.map((o) => (o.id === e.ordineId ? { ...o, tokenNegozio: token } : o));
      const importo = ordini.find((o) => o.id === e.ordineId)?.amount ?? 0;
      return { stored: { ...cur, version: cur.version + 1, state: { ...nuovo, orders: ordini } }, risultato: { stato: 200, ordineId: e.ordineId, token, importo } };
    });
  } catch (e) {
    console.error("Ordine del negozio non registrato", e);
    return risposta({ error: "Non riesco a registrare l'ordine: riprova tra poco." }, 503);
  }
  if (r.stato === 200) return risposta({ ordineId: r.ordineId, token: r.token, importo: r.importo });
  if (r.stato === 409) return risposta({ error: "Ricambio non più disponibile", conflicts: r.conflicts }, 409);
  return risposta({ error: r.error }, r.stato);
}
