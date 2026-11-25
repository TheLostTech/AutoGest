// Controllo dei robot sulla registrazione (BotID di Vercel). Chi chiama passa checkBotId: qui solo la decisione.
// Fuori da Vercel checkBotId lancia un errore: in produzione si rifiuta (meglio una registrazione persa che i robot),
// in sviluppo e nelle prove si lascia passare. In sviluppo BotID stesso risponde "persona" (README del pacchetto).
export async function registrazioneDaRobot(
  controlla: () => Promise<{ isBot: boolean }>,
  produzione: boolean = process.env.NODE_ENV === "production",
): Promise<boolean> {
  try {
    return (await controlla()).isBot;
  } catch (e) {
    console.error("Controllo dei robot non riuscito", e);
    return produzione;
  }
}
