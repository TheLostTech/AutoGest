type Ambiente = Record<string, string | undefined>;

function senzaBarraFinale(u: string): string {
  return u.replace(/\/+$/, "");
}

// Indirizzo pubblico dell'app, per i link nelle email e per Better Auth: BETTER_AUTH_URL se c'è; su Vercel
// l'indirizzo del ramo (VERCEL_BRANCH_URL) o del deploy (VERCEL_URL), che arrivano senza "https://"; altrimenti null
// (locale: l'indirizzo si deduce dalla richiesta).
export function indirizzoPubblico(env: Ambiente = process.env): string | null {
  const esplicito = env.BETTER_AUTH_URL?.trim();
  if (esplicito) return senzaBarraFinale(esplicito);
  if (env.VERCEL) {
    const host = (env.VERCEL_BRANCH_URL || env.VERCEL_URL)?.trim();
    if (host) return `https://${host}`;
  }
  return null;
}

// Altri indirizzi dello stesso deploy su Vercel (deploy, ramo, produzione): fidati come origine delle richieste.
export function originiVercel(env: Ambiente = process.env): string[] {
  if (!env.VERCEL) return [];
  const host = [env.VERCEL_URL, env.VERCEL_BRANCH_URL, env.VERCEL_PROJECT_PRODUCTION_URL]
    .map((h) => h?.trim())
    .filter((h): h is string => !!h);
  return [...new Set(host.map((h) => `https://${h}`))];
}
