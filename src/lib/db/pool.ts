// Connessione a Postgres (Supabase) per Better Auth e per il deposito, quando il deposito è Supabase. Solo server.
// TLS sempre verificato, mai `rejectUnauthorized: false`: il certificato pubblico di Supabase sta in supabase-ca.crt
// (pannello di Supabase, Database Settings → SSL Configuration; è pubblico e si versiona). Senza TLS solo in locale.
// Il file arriva nelle funzioni di Vercel grazie a outputFileTracingIncludes in next.config.ts.
import { readFileSync } from "node:fs";
import path from "node:path";
import { Pool, type PoolConfig } from "pg";
import { parse } from "pg-connection-string";

export const FILE_CA = path.join(/*turbopackIgnore: true*/ process.cwd(), "src", "lib", "db", "supabase-ca.crt");
const LOCALE = new Set(["localhost", "127.0.0.1", "::1"]);
// Parametri dell'indirizzo che pg userebbe al posto di `ssl` qui sotto (sslmode=no-verify spegne la verifica)
const PARAMETRO_SSL = /^(ssl.*|uselibpqcompat)$/i;
// Un database che non risponde non deve tenere ferma una richiesta: 5 secondi per avere una connessione.
// I limiti dentro il database (istruzione e transazione lasciata aperta: 15 secondi) non si passano qui come
// parametri d'avvio (options / statement_timeout di pg): con il pooler di Supabase in modalità transazione la
// connessione al server è condivisa tra i client e i parametri d'avvio del singolo client non valgono. Si mettono
// con set_config(..., true), cioè SET LOCAL, all'inizio di ogni transazione del deposito (deposito/supabase.ts).
export const ATTESA_CONNESSIONE_MS = 5000;

export function opzioniPool(url: string, fileCa: string = FILE_CA): PoolConfig {
  let u: URL;
  try {
    u = new URL(url);
  } catch {
    // L'errore di URL porta con sé l'indirizzo intero, password compresa: nei log non deve finire
    throw new Error("DATABASE_URL non valido");
  }
  const tolti = [...u.searchParams.keys()].filter((k) => PARAMETRO_SSL.test(k));
  for (const k of tolti) u.searchParams.delete(k);
  // Se non c'era nulla da togliere l'indirizzo resta com'era (nessuna ricodifica della password)
  const connectionString = tolti.length ? u.toString() : url;
  // Locale o no si decide sull'host che pg userà davvero: lo legge con questo stesso parse, e un ?host= nell'indirizzo
  // vince sul nome dopo la @ (postgresql://localhost/db?host=remoto va su remoto, quindi con il TLS)
  if (LOCALE.has(parse(connectionString).host ?? "")) return { connectionString, max: 3, connectionTimeoutMillis: ATTESA_CONNESSIONE_MS, ssl: false };
  let ca: string;
  try {
    ca = readFileSync(fileCa, "utf8");
  } catch {
    throw new Error("Certificato CA di Supabase mancante: src/lib/db/supabase-ca.crt");
  }
  return { connectionString, max: 3, connectionTimeoutMillis: ATTESA_CONNESSIONE_MS, ssl: { ca } };
}

// Un solo pool per processo, sulla globalThis: le route di Next possono avere ognuna la propria copia del modulo.
const g = globalThis as typeof globalThis & { __poolPostgres?: Pool };

export function pool(): Pool {
  if (g.__poolPostgres) return g.__poolPostgres;
  const url = process.env.DATABASE_URL;
  if (!url) throw new Error("DATABASE_URL mancante");
  const p = new Pool(opzioniPool(url));
  // Una connessione inattiva che cade (riavvio del database, rete) non deve spegnere il server: il pool ne apre un'altra
  p.on("error", (e) => console.error("[db] connessione al database persa:", e.message));
  return (g.__poolPostgres = p);
}
