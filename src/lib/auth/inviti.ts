import type { BetterAuthPlugin } from "better-auth";

// Plugin minimo: la tabella dei codici invito per la registrazione (finché Stripe è in prova).
// Si salva solo l'impronta del codice (sha256), mai il codice. Nessun endpoint: le scritture sono in piattaforma/inviti.ts.
export const invitiPlugin = {
  id: "inviti",
  schema: {
    invito: {
      modelName: "invito",
      fields: {
        codiceHash: { type: "string", required: true, unique: true },
        nota: { type: "string", required: true },
        creatoDa: { type: "string", required: true, references: { model: "user", field: "id", onDelete: "cascade" } },
        creato: { type: "date", required: true },
        scade: { type: "date", required: true },
        usatoDa: { type: "string", required: false, references: { model: "organization", field: "id", onDelete: "set null" } },
        usato: { type: "date", required: false },
      },
    },
  },
} satisfies BetterAuthPlugin;
