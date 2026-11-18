import { mkdirSync } from "node:fs";
import Database from "better-sqlite3";
import { betterAuth } from "better-auth";
import { nextCookies } from "better-auth/next-js";
import { admin, organization, twoFactor } from "better-auth/plugins";
import { DATA_DIR, DB_FILE } from "@/lib/server-data";
import { assistenzaPlugin } from "./assistenza";
import { segretoAccesso } from "./segreto";
import { pinDispositivo } from "./pin-dispositivo";
import { acAzienda, acPiattaforma, ruoliAzienda, ruoliPiattaforma } from "./permessi";

// Il segreto viene da BETTER_AUTH_SECRET o, se manca, da un file generato nella cartella dati (segreto.ts):
// mai il valore di prova di Better Auth, nemmeno con `next dev`. Non si scrive mai qui.
// Il cookie "Secure" si decide per richiesta: qui è spento e lo accende la route (vedi cookie-secure.ts)
// quando la richiesta arriva in HTTPS, così `localhost` continua a funzionare.
// La cartella dati può non esistere ancora (primo avvio, DATI_DIR nuova): SQLite non la crea da solo.
mkdirSync(DATA_DIR, { recursive: true });

// Tentativi di accesso: Better Auth limita le richieste solo in produzione; qui sempre, anche con `next dev` sul tunnel.
// Per indirizzo IP (x-forwarded-for con un solo valore); senza un IP affidabile tutte le richieste condividono un contatore
// per percorso, che è più severo. In memoria: un solo processo Node.
const AL_MINUTO = (max: number) => ({ window: 60, max });

export const auth = betterAuth({
  database: new Database(DB_FILE),
  secret: segretoAccesso(),
  rateLimit: {
    enabled: true,
    storage: "memory",
    window: 10,
    max: 100,
    customRules: {
      "/sign-in/*": AL_MINUTO(5),
      "/two-factor/*": AL_MINUTO(5),
      // Più tablet dello stesso piazzale escono dallo stesso indirizzo: un po' di margine (i PIN hanno già i loro blocchi)
      "/pin-dispositivo/entra": AL_MINUTO(10),
      "/pin-dispositivo/registra": AL_MINUTO(5),
      "/pin-dispositivo/sblocca": AL_MINUTO(10),
    },
  },
  emailAndPassword: { enabled: true, disableSignUp: true },
  advanced: { useSecureCookies: false },
  trustedOrigins: process.env.INDIRIZZO_GESTIONALE ? [process.env.INDIRIZZO_GESTIONALE] : [],
  plugins: [
    organization({ ac: acAzienda, roles: ruoliAzienda, allowUserToCreateOrganization: false }),
    admin({ ac: acPiattaforma, roles: ruoliPiattaforma, adminRoles: ["superadmin"], defaultRole: "user" }),
    twoFactor({ issuer: "Autodemolizione 4.0" }),
    assistenzaPlugin,
    pinDispositivo(),
    nextCookies(),
  ],
});
