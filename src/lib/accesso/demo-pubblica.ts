// Vetrina online: con DEMO_PUBBLICA=1 "Apri la demo" entra senza credenziali nell'azienda demo (src/app/demo/route.ts)
// e la pagina di accesso rimanda lì. Mai sul server di un'azienda vera.
export function demoPubblica(): boolean {
  return process.env.DEMO_PUBBLICA === "1";
}
