// Controllo dei robot sulla registrazione (BotID di Vercel). Chi chiama passa checkBotId: qui solo la decisione.
// BotID funziona solo su Vercel. Lì, se risponde "robot" o non risponde, si rifiuta (meglio una registrazione persa
// che i robot). Fuori da Vercel: in sviluppo e nelle prove si salta; in produzione si rifiuta, salvo la rinuncia
// esplicita PIAZZALE_SENZA_BOTID=1 (scripts/piazzale-test.sh, presentazione.sh). Vedi docs/ACCESSO.md.
type Ambiente = Record<string, string | undefined>;

export async function registrazioneDaRobot(controlla: () => Promise<{ isBot: boolean }>, env: Ambiente = process.env): Promise<boolean> {
  if (env.VERCEL === "1") {
    try {
      return (await controlla()).isBot;
    } catch (e) {
      console.error("Controllo dei robot non riuscito", e);
      return true;
    }
  }
  if (env.NODE_ENV !== "production") {
    console.info("Registrazione: controllo dei robot saltato fuori da Vercel (sviluppo)");
    return false;
  }
  if (env.PIAZZALE_SENZA_BOTID === "1") {
    console.warn("Registrazione: controllo dei robot spento da PIAZZALE_SENZA_BOTID=1 (resta il limite per indirizzo)");
    return false;
  }
  console.error(
    "Registrazione rifiutata: in produzione fuori da Vercel serve BotID oppure la rinuncia esplicita PIAZZALE_SENZA_BOTID=1",
  );
  return true;
}
