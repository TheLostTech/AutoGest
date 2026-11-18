// Si esegue una volta all'avvio del server (solo runtime Node): prepara tabelle, azienda demo e super admin.
export async function register() {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;
  const { avviaPiattaforma } = await import("@/lib/accesso/avvio");
  await avviaPiattaforma();
}
