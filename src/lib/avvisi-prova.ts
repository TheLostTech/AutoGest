// Avvisi di fine prova: quando mandarli e chi può far partire il giro giornaliero. Puro: niente disco né rete.
import { timingSafeEqual } from "node:crypto";
import { oraProva, type Abbonamento } from "./abbonamento.ts";

const GIORNO_MS = 86_400_000;
export const GIORNI_AVVISO = 3;

export type Avviso = "scadenza" | "finita";

/** Giorni interi che mancano alla fine della prova (per eccesso, come il conto alla rovescia); null se non è in prova. */
export function giorniAllaFine(a: Abbonamento, ora: number): number | null {
  if (a.stato !== "nuovo" || a.fineProva === null) return null;
  const mancano = a.fineProva - oraProva(a, ora);
  return mancano > 0 ? Math.ceil(mancano / GIORNO_MS) : null;
}

/** "scadenza": in prova con 3 giorni o meno e avviso non ancora mandato. "finita": prova partita e finita, avviso non ancora mandato. */
export function avvisoDaMandare(a: Abbonamento, ora: number): Avviso | null {
  if (a.stato !== "nuovo" || a.fineProva === null) return null;
  const giorni = giorniAllaFine(a, ora);
  if (giorni === null) return a.avvisi.finita ? null : "finita";
  return giorni <= GIORNI_AVVISO && !a.avvisi.scadenza ? "scadenza" : null;
}

/** Intestazione Authorization di Vercel ("Bearer <CRON_SECRET>"), confronto a tempo costante. Segreto assente o corto (meno di 16 caratteri): mai valido. */
export function segretoValido(intestazione: string | null, segreto: string | undefined): boolean {
  if (!segreto || segreto.length < 16 || !intestazione) return false;
  const atteso = Buffer.from(`Bearer ${segreto}`);
  const dato = Buffer.from(intestazione);
  return dato.length === atteso.length && timingSafeEqual(dato, atteso);
}
