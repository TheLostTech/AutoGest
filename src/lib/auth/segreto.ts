import { randomBytes } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { DATA_DIR } from "@/lib/server-data";

// Segreto di Better Auth (firma dei cookie di sessione, cifratura dei codici del secondo fattore).
// Da BETTER_AUTH_SECRET se c'è; altrimenti un valore casuale generato al primo avvio nel file .segreto-accesso della
// cartella dati, leggibile solo dal proprietario (come .chiave-collegamenti). Mai il valore di prova di Better Auth,
// che è pubblico: con quello chiunque potrebbe firmare un cookie di sessione valido.
// Nel prodotto vero il segreto va in un archivio di segreti, non accanto ai dati.
export const FILE_SEGRETO = path.join(DATA_DIR, ".segreto-accesso");
// Il valore di prova di Better Auth: serve solo a ricifrare i codici del secondo fattore salvati con quello (avvio.ts)
export const SEGRETO_DI_PROVA = "better-auth-secret-12345678901234567890";

export function segretoAccesso(): string {
  const env = process.env.BETTER_AUTH_SECRET?.trim();
  if (env) return env;
  try {
    const v = readFileSync(FILE_SEGRETO, "utf8").trim();
    if (v.length >= 32) return v;
    throw new Error(`${FILE_SEGRETO} è troppo corto: cancellalo per generarne uno nuovo (le sessioni aperte si chiudono).`);
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code !== "ENOENT") throw e;
  }
  mkdirSync(DATA_DIR, { recursive: true });
  const nuovo = randomBytes(32).toString("base64url");
  try {
    // wx: se un altro processo l'ha appena scritto, si usa il suo
    writeFileSync(FILE_SEGRETO, nuovo, { mode: 0o600, flag: "wx" });
    return nuovo;
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code !== "EEXIST") throw e;
    return readFileSync(FILE_SEGRETO, "utf8").trim();
  }
}
