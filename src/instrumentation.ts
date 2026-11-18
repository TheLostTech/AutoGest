// Si esegue una volta all'avvio del server (solo runtime Node): prepara tabelle, azienda demo e super admin.
// Mai errori fatali: se qualcosa non va, il server resta acceso e le API rispondono 503.
export async function register() {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;
  try {
    const { avviaPiattaforma } = await import("@/lib/accesso/avvio");
    await avviaPiattaforma();
  } catch (e) {
    console.error("[avvio] avvio della piattaforma non riuscito:", e);
    try {
      const { segnaPiattaformaNonPronta } = await import("@/lib/accesso/pronta");
      segnaPiattaformaNonPronta(true);
    } catch {}
  }
}
