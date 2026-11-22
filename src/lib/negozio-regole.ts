// Regole del negozio pubblico che decidono se un ordine si accetta e quando una riserva scade. Modulo puro.
import type { Annuncio, Order } from "./types";

/** Un ordine del negozio non pagato tiene i pezzi riservati al massimo per questo tempo. */
export const SCADENZA_RISERVA_MS = 30 * 60 * 1000;
/** Ordini del negozio in attesa di pagamento che un'azienda può avere aperti insieme. */
export const MAX_ORDINI_APERTI = 20;

type OrdineMin = Pick<Order, "id" | "channel" | "status" | "createdAt">;
const aperto = (o: OrdineMin) => o.channel === "negozio" && o.status === "in attesa di pagamento";

/** Ordini del negozio in attesa da più di 30 minuti (scade dal millisecondo dopo). */
export function ordiniScaduti(orders: OrdineMin[], oraMs: number): string[] {
  return orders.filter((o) => aperto(o) && oraMs - new Date(o.createdAt).getTime() > SCADENZA_RISERVA_MS).map((o) => o.id);
}

export function ordiniAperti(orders: OrdineMin[]): number {
  return orders.filter(aperto).length;
}

export type DecisioneOrdine = { ok: true } | { ok: false; stato: 400 | 429; error: string };

/**
 * Si può registrare un ordine per questi annunci? Annunci che non esistono o non sono online sul negozio: 400 e NESSUNA
 * scrittura (nemmeno una riga di registro). Troppi ordini aperti: 429. Gli ordini scaduti vanno rilasciati prima.
 */
export function decidiOrdine(st: { orders: OrdineMin[]; annunci: Pick<Annuncio, "id" | "negozio">[] }, annuncioIds: string[]): DecisioneOrdine {
  const online = new Set(st.annunci.filter((a) => a.negozio?.stato === "online").map((a) => a.id));
  if (!annuncioIds.length || annuncioIds.some((id) => !online.has(id))) return { ok: false, stato: 400, error: "Carrello non valido." };
  if (ordiniAperti(st.orders) >= MAX_ORDINI_APERTI) return { ok: false, stato: 429, error: "Ci sono troppi ordini in attesa di pagamento: riprova tra qualche minuto." };
  return { ok: true };
}

/** L'archivio ha la forma che ordine e pagamento si aspettano: altrimenti meglio non scrivere. */
export function archivioNegozioValido(s: Record<string, unknown> | null): boolean {
  if (!s) return false;
  if (!["vehicles", "parts", "annunci", "orders", "audit"].every((k) => Array.isArray(s[k]))) return false;
  const c = s.counters as { order?: unknown; event?: unknown } | undefined;
  return typeof c?.order === "number" && typeof c?.event === "number";
}

export const PAGAMENTO_NON_ATTIVO = "Pagamento online non ancora attivo";

/** Il pagamento simulato esiste solo sull'azienda demo: altrove non si crea nessun ordine (niente riserva, niente scrittura) e non si paga. */
export function decidiPagamento(demo: boolean): { ok: true } | { ok: false; stato: 403; error: string } {
  return demo ? { ok: true } : { ok: false, stato: 403, error: PAGAMENTO_NON_ATTIVO };
}
