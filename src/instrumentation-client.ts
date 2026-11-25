// Si esegue nel browser prima che la pagina diventi interattiva (Next: instrumentation-client).
// BotID di Vercel: aggiunge la verifica alle richieste di registrazione, che la route controlla con checkBotId.
// In sviluppo initBotId non carica nulla (README di botid).
import { initBotId } from "botid/client/core";

try {
  initBotId({ protect: [{ path: "/api/registrazione", method: "POST" }] });
} catch (e) {
  // Senza BotID la registrazione in produzione risponde 403: l'errore resta nella console, la pagina funziona
  console.error("BotID non avviato", e);
}
