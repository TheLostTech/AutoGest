import { toNextJsHandler } from "better-auth/next-js";
import { auth } from "@/lib/auth/server";
import { conCookieSecure } from "@/lib/auth/cookie-secure";
import { percorsoAuthPermesso } from "@/lib/auth/percorsi-auth";

const gestori = toNextJsHandler(auth);

// Dal browser si raggiungono solo gli endpoint di Better Auth che l'app usa davvero (elenco in percorsi-auth.ts).
// Tutto il resto risponde 404: le azioni del plugin admin (crea utente, cambia password, banna, ...) le fa solo l'area
// Piattaforma (/api/piattaforma/*) sul server con il registro dell'azienda; niente cambio nome o email dal profilo,
// niente "lascia l'organizzazione", inviti, ecc.
const nonTrovato = () => Response.json({ error: "Non trovato." }, { status: 404, headers: { "Cache-Control": "no-store" } });

export async function GET(request: Request) {
  if (!percorsoAuthPermesso("GET", new URL(request.url).pathname)) return nonTrovato();
  return conCookieSecure(request, await gestori.GET(request));
}

export async function POST(request: Request) {
  if (!percorsoAuthPermesso("POST", new URL(request.url).pathname)) return nonTrovato();
  return conCookieSecure(request, await gestori.POST(request));
}
