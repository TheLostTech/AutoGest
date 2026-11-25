// Controllo dei robot sulla registrazione (BotID di Vercel). Chi chiama passa checkBotId: qui solo la decisione.
// BotID funziona solo su Vercel. Lì, se risponde "robot" o non risponde, si rifiuta (meglio una registrazione persa
// che i robot). Fuori da Vercel (next dev, next start sul Mac, scripts/piazzale-test.sh, presentazione.sh) si salta
// con una riga nel log: il limite di 3 registrazioni all'ora per indirizzo è già passato.
export async function registrazioneDaRobot(
  controlla: () => Promise<{ isBot: boolean }>,
  suVercel: boolean = process.env.VERCEL === "1",
): Promise<boolean> {
  if (!suVercel) {
    console.info("Registrazione: controllo dei robot saltato fuori da Vercel");
    return false;
  }
  try {
    return (await controlla()).isBot;
  } catch (e) {
    console.error("Controllo dei robot non riuscito", e);
    return true;
  }
}
