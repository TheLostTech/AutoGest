// Pagine che si aprono senza accesso. Puro: lo usano il proxy, il caricamento del client e la sincronizzazione.
const PUBBLICI = ["/accesso", "/negozio", "/ebay-simulato", "/scopri", "/news"];
const FILE_PUBBLICI = ["/robots.txt", "/sitemap.xml", "/favicon.ico"];

export function percorsoPubblico(percorso: string): boolean {
  if (FILE_PUBBLICI.includes(percorso)) return true;
  return PUBBLICI.some((p) => percorso === p || percorso.startsWith(p + "/"));
}

// L'API decide da sola (risponde 401): il proxy lascia passare tutto /api.
export function percorsoApi(percorso: string): boolean {
  return percorso === "/api" || percorso.startsWith("/api/");
}

// "Dopo l'accesso torna qui": solo percorsi interni, mai indirizzi esterni.
// Si risolve con il parser degli URL (come fa il browser) e si accetta solo se resta sullo stesso sito.
export function percorsoDaSicuro(da: string | null | undefined): string {
  if (!da || !da.startsWith("/")) return "/";
  // Tabulazioni, a capo e altri caratteri di controllo vengono tolti dal parser: "/\t/x" diventerebbe "//x". Anche "\".
  if (/[\u0000-\u001f\u007f\\]/.test(da)) return "/";
  // Stesso discorso per le forme codificate (%09, %0a, %5c): meglio non seguirle.
  if (/%(?:[01][0-9a-f]|7f|5c)/i.test(da)) return "/";
  try {
    const u = new URL(da, "http://x");
    if (u.origin !== "http://x") return "/";
    const p = u.pathname + u.search + u.hash;
    // Dopo la normalizzazione non deve poter diventare un indirizzo "//host"
    return p.startsWith("//") ? "/" : p;
  } catch {
    return "/";
  }
}

// Area del super admin: serve l'accesso (lo chiede il proxy) ma non carica i dati di nessuna azienda.
export function percorsoPiattaforma(percorso: string): boolean {
  return percorso === "/piattaforma" || percorso.startsWith("/piattaforma/");
}
