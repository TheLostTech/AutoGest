import type { BetterAuthPlugin } from "better-auth";
import { createAuthMiddleware } from "better-auth/api";

// Percorsi che creano una sessione dopo un secondo fattore riuscito (codice TOTP o codice di riserva).
const VERIFICA_DUE_FATTORI = new Set(["/two-factor/verify-totp", "/two-factor/verify-backup-code"]);

// Plugin minimo: la tabella degli ingressi di assistenza del super admin e tre campi facoltativi
// sulla sessione: tipoAccesso ("pin"), dispositivoId e dueFattoriVerificato.
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
        // true solo per le sessioni create da una verifica del secondo fattore andata a buon fine.
        dueFattoriVerificato: { type: "boolean", required: false, defaultValue: false, input: false },
      },
    },
  },
  hooks: {
    after: [
      {
        matcher: (context) => VERIFICA_DUE_FATTORI.has(context.path ?? ""),
        handler: createAuthMiddleware(async (ctx) => {
          // newSession c'è solo se la verifica è riuscita e ha creato una sessione (accesso con codice, oppure
          // prima conferma del codice che attiva il 2FA e sostituisce la sessione). Se la verifica fallisce è null.
          const nuova = ctx.context.newSession;
          if (!nuova) return;
          await ctx.context.internalAdapter.updateSession(nuova.session.token, { dueFattoriVerificato: true });

          // Attivazione del 2FA (c'era già una sessione, che il plugin ha sostituito): chiude tutte le altre
          // sessioni dell'utente, che non hanno passato il secondo fattore.
          if (ctx.context.session) {
            const altre = await ctx.context.adapter.findMany<{ token: string }>({
              model: "session",
              where: [{ field: "userId", value: nuova.user.id }],
            });
            for (const s of altre) {
              if (s.token !== nuova.session.token) await ctx.context.internalAdapter.deleteSession(s.token);
            }
          }
        }),
      },
    ],
  },
} satisfies BetterAuthPlugin;
