import { depositoDisco } from "./disco";
import type { Deposito } from "./tipi";

const CHIAVI = ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "DATABASE_URL"] as const;

/** Con le tre variabili di Supabase si usa Supabase, senza nessuna si usa il disco; una parte sola è un errore. */
export function sceltaDeposito(env: Record<string, string | undefined>): "disco" | "supabase" {
  const presenti = CHIAVI.filter((k) => !!env[k]).length;
  if (presenti === 0) return "disco";
  if (presenti === CHIAVI.length) return "supabase";
  throw new Error("Configurazione Supabase incompleta: servono SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY e DATABASE_URL");
}

// Un solo deposito per processo, sulla globalThis: le route di Next possono avere ognuna la propria copia del modulo.
const g = globalThis as typeof globalThis & { __deposito?: Deposito };

export function deposito(): Deposito {
  if (g.__deposito) return g.__deposito;
  if (sceltaDeposito(process.env) === "supabase") throw new Error("Deposito Supabase non ancora disponibile");
  return (g.__deposito = depositoDisco());
}
