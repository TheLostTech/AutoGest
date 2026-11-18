import type { BetterAuthPlugin } from "better-auth";

// Plugin minimo: la tabella degli ingressi di assistenza del super admin e due campi facoltativi
// sulla sessione (usati dall'accesso con PIN: tipoAccesso = "pin", dispositivoId).
// Nessun endpoint: le scritture le fanno le funzioni server dei task successivi.
export const assistenzaPlugin = {
  id: "assistenza",
  schema: {
    assistenza: {
      modelName: "assistenza",
      fields: {
        userId: { type: "string", required: true, references: { model: "user", field: "id", onDelete: "cascade" }, index: true },
        organizationId: { type: "string", required: true, references: { model: "organization", field: "id", onDelete: "cascade" }, index: true },
        motivo: { type: "string", required: true },
        inizio: { type: "date", required: true },
        scade: { type: "date", required: true },
        fine: { type: "date", required: false },
      },
    },
    session: {
      fields: {
        tipoAccesso: { type: "string", required: false, input: false },
        dispositivoId: { type: "string", required: false, input: false },
      },
    },
  },
} satisfies BetterAuthPlugin;
