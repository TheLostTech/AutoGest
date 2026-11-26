import { NextResponse, type NextRequest } from "next/server";
import { getSessionCookie } from "better-auth/cookies";
import { percorsoApi, percorsoPubblico } from "./lib/accesso/percorsi";
import { demoPubblica } from "./lib/accesso/demo-pubblica";

// Controllo ottimistico: guarda solo se c'è il cookie di sessione. La decisione vera (azienda, ruoli, scadenze)
// la prende ogni route con accessoDaRichiesta; le API senza cookie rispondono 401 da sole.
export function proxy(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  if (percorsoApi(pathname) || percorsoPubblico(pathname)) return NextResponse.next();
  if (getSessionCookie(req)) return NextResponse.next();
  const url = req.nextUrl.clone();
  // Chi apre miopiazzale.it senza accesso vede la presentazione (anche Google), non la pagina di accesso
  if (pathname === "/" && !demoPubblica()) {
    url.pathname = "/scopri";
    return NextResponse.redirect(url);
  }
  // Vetrina online: senza sessione si entra (o si rientra) nella demo, senza passare dalla pagina di accesso
  url.pathname = demoPubblica() ? "/demo" : "/accesso";
  url.search = "";
  url.searchParams.set("da", pathname + search);
  return NextResponse.redirect(url);
}

export const config = {
  // Esclusi i file statici e le immagini di Next
  matcher: ["/((?!_next/static|_next/image|.*\\.(?:png|jpg|jpeg|gif|svg|webp|ico|wasm|txt|xml|json|js|css|woff2?)$).*)"],
};
