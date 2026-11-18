// Better Auth decide l'attributo "Secure" dei cookie una volta sola, all'avvio. Noi lo vogliamo solo
// quando la richiesta arriva in HTTPS (tunnel), non su localhost: lo aggiungiamo qui, per richiesta.
export function arrivaInHttps(request: Request): boolean {
  const inoltrato = request.headers.get("x-forwarded-proto")?.split(",")[0]?.trim().toLowerCase();
  if (inoltrato) return inoltrato === "https";
  try {
    return new URL(request.url).protocol === "https:";
  } catch {
    return false;
  }
}

export function conCookieSecure(request: Request, risposta: Response): Response {
  if (!arrivaInHttps(request)) return risposta;
  const cookie = risposta.headers.getSetCookie();
  if (cookie.length === 0) return risposta;
  const headers = new Headers(risposta.headers);
  headers.delete("set-cookie");
  for (const c of cookie) headers.append("set-cookie", /;\s*secure\b/i.test(c) ? c : `${c}; Secure`);
  return new Response(risposta.body, { status: risposta.status, statusText: risposta.statusText, headers });
}
