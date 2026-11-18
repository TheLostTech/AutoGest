import { mkdirSync } from "node:fs";
import Database from "better-sqlite3";
import { betterAuth } from "better-auth";
import { nextCookies } from "better-auth/next-js";
import { admin, organization, twoFactor } from "better-auth/plugins";
import { DATA_DIR, DB_FILE } from "@/lib/server-data";
import { assistenzaPlugin } from "./assistenza";
import { pinDispositivo } from "./pin-dispositivo";
import { acAzienda, acPiattaforma, ruoliAzienda, ruoliPiattaforma } from "./permessi";

// Il segreto viene da BETTER_AUTH_SECRET (obbligatorio con `next start`; in sviluppo Better Auth usa
// un valore di prova). Non si scrive mai qui.
// Il cookie "Secure" si decide per richiesta: qui è spento e lo accende la route (vedi cookie-secure.ts)
// quando la richiesta arriva in HTTPS, così `localhost` continua a funzionare.
// La cartella dati può non esistere ancora (primo avvio, DATI_DIR nuova): SQLite non la crea da solo.
mkdirSync(DATA_DIR, { recursive: true });

export const auth = betterAuth({
  database: new Database(DB_FILE),
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
