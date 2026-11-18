import { toNextJsHandler } from "better-auth/next-js";
import { auth } from "@/lib/auth/server";
import { conCookieSecure } from "@/lib/auth/cookie-secure";

const gestori = toNextJsHandler(auth);

// Le azioni del plugin admin (crea utente, cambia password, banna, ...) non si raggiungono via HTTP:
// le fa solo l'area Piattaforma (/api/piattaforma/*), sul server, con il registro dell'azienda.
function adminDaHttp(request: Request): boolean {
  const p = new URL(request.url).pathname.replace(/\/+$/, "").toLowerCase();
  return p === "/api/auth/admin" || p.startsWith("/api/auth/admin/");
}

const nonTrovato = () => Response.json({ error: "Non trovato." }, { status: 404, headers: { "Cache-Control": "no-store" } });

export async function GET(request: Request) {
  if (adminDaHttp(request)) return nonTrovato();
  return conCookieSecure(request, await gestori.GET(request));
}

export async function POST(request: Request) {
  if (adminDaHttp(request)) return nonTrovato();
  return conCookieSecure(request, await gestori.POST(request));
}
