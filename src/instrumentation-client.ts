// Si esegue nel browser prima che la pagina diventi interattiva (Next: instrumentation-client).
// BotID di Vercel: aggiunge la verifica alle richieste di registrazione, che la route controlla con checkBotId.
// Solo su Vercel: PIAZZALE_BOTID lo scrive next.config al momento della build, altrove nessuno script di BotID.
// In sviluppo initBotId comunque non carica nulla (README di botid).
import { initBotId } from "botid/client/core";

if (process.env.PIAZZALE_BOTID === "1") {
  try {
    initBotId({ protect: [{ path: "/api/registrazione", method: "POST" }] });
  } catch (e) {
    // Senza BotID la registrazione su Vercel risponde 403: l'errore resta nella console, la pagina funziona
    console.error("BotID non avviato", e);
  }
}
