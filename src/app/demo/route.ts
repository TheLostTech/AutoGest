// Demo pubblica: "Apri la demo" dalla landing entra senza credenziali nell'azienda demo, come la responsabile.
// Solo con DEMO_PUBBLICA=1 (la vetrina online, dove i dati stanno in una cartella temporanea e si azzerano da soli):
// sul server di un'azienda vera questa porta resta chiusa e manda all'accesso normale.
// La password di Sara non esce mai dal server: si legge da credenziali-demo.json e si usa qui per aprire la sessione.
import { readFile } from "node:fs/promises";
import path from "node:path";
import type { AuthContext } from "better-auth";
import { auth } from "@/lib/auth/server";
import { conCookieSecure } from "@/lib/auth/cookie-secure";
import { UTENTI_DEMO } from "@/lib/accesso/demo-utenti";
import { demoPubblica } from "@/lib/accesso/demo-pubblica";
import { percorsoDaSicuro } from "@/lib/accesso/percorsi";
import { DATA_DIR } from "@/lib/server-data";

const RESPONSABILE = UTENTI_DEMO.find((u) => u.email && u.ruoli.includes("responsabile"));

const eDemo = (metadata: unknown): boolean => {
  try {
    const m = typeof metadata === "string" ? JSON.parse(metadata) : metadata;
    return typeof m === "object" && m !== null && (m as { demo?: unknown }).demo === true;
  } catch {
    return false;
  }
};

// Niente redirect in caso di errore: /accesso in demo pubblica rimanda qui, e si girerebbe in tondo.
const nonPronta = () =>
  new Response(
    "<!doctype html><meta charset=utf-8><title>Demo non pronta</title><body style=\"font:18px system-ui;padding:40px\"><p>La demo si sta preparando. Riprova tra qualche secondo.</p><p><a href=\"/demo\">Riprova</a> · <a href=\"/scopri\">Torna alla presentazione</a></p>",
    { status: 503, headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store", "Retry-After": "5" } },
  );

export async function GET(req: Request) {
  const u = new URL(req.url);
  const da = percorsoDaSicuro(u.searchParams.get("da"));
  if (!demoPubblica() || !RESPONSABILE?.email) {
    return Response.redirect(new URL(`/accesso?da=${encodeURIComponent(da)}`, u), 303);
  }

  let password: string | undefined;
  try {
    const cred = JSON.parse(await readFile(path.join(DATA_DIR, "credenziali-demo.json"), "utf8")) as Record<string, { password?: string }>;
    password = cred[RESPONSABILE.nome]?.password;
  } catch {}
  if (!password) return nonPronta();

  const c = (await auth.$context) as unknown as AuthContext;
  const aziende = await c.adapter.findMany<{ id: string; metadata?: unknown }>({ model: "organization" });
  const demo = aziende.find((o) => eDemo(o.metadata));
  if (!demo) return nonPronta();

  let entrata: { headers: Headers; response: { token: string } };
  try {
    entrata = await auth.api.signInEmail({ body: { email: RESPONSABILE.email, password }, headers: req.headers, returnHeaders: true });
  } catch (e) {
    console.error("[demo] accesso della demo pubblica non riuscito:", e);
    return nonPronta();
  }
  await c.internalAdapter.updateSession(entrata.response.token, { activeOrganizationId: demo.id });

  const headers = new Headers({ Location: new URL(da, u).toString(), "Cache-Control": "no-store" });
  for (const cookie of entrata.headers.getSetCookie()) headers.append("set-cookie", cookie);
  return conCookieSecure(req, new Response(null, { status: 303, headers }));
}
