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
export function percorsoDaSicuro(da: string | null | undefined): string {
  if (!da || !da.startsWith("/") || da.startsWith("//") || da.startsWith("/\\")) return "/";
  return da;
}
