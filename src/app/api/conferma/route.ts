// Conferma dell'email del titolare registrato, dalla pagina /conferma: il gettone dell'email più la password scelta
// alla registrazione. Così chi rifà una registrazione in sospeso con la stessa email e un'altra password non si fa
// confermare l'account dal vero titolare che apre il link (la sua password non è quella). Pubblica, senza sessione.
// Il gettone è quello firmato da Better Auth (stesso segreto): si verifica la firma, non basta leggerlo. La password
// conta nel blocco per account dell'accesso (10 sbagliate in 15 minuti → 15 minuti fermo). Poi la verifica vera la fa
// Better Auth (afterEmailVerification: partono i 15 giorni, si chiudono le altre sessioni) e si entra già nell'azienda.
import { verifyJWT } from "better-auth/crypto";
import { rispostaNonPronta } from "@/lib/accesso/pronta";
import { LINK_NON_VALIDO, PASSWORD_SBAGLIATA, richiestaConferma } from "@/lib/accesso/conferma";
import { conCookieSecure } from "@/lib/auth/cookie-secure";
import { auth } from "@/lib/auth/server";
import { verificaConBlocco } from "@/lib/auth/tentativi-account";
import { contesto, daAltroSito, errore, leggiJson, ok } from "@/lib/piattaforma/server";

type Gettone = { email?: unknown; userId?: unknown; updateTo?: unknown; requestType?: unknown };

export async function POST(req: Request) {
  const nonPronta = await rispostaNonPronta();
  if (nonPronta) return nonPronta;
  const x = daAltroSito(req, true);
  if (x) return x;
  const dati = richiestaConferma(await leggiJson(req));
  if (!dati) return errore(400, LINK_NON_VALIDO);
  const c = await contesto();

  // Solo il gettone di conferma dell'email (non quelli del cambio email), firmato con il nostro segreto e non scaduto
  const g = await verifyJWT<Gettone>(dati.token, c.secret);
  if (!g || typeof g.email !== "string" || typeof g.userId !== "string" || g.updateTo !== undefined || g.requestType !== undefined) {
    return errore(400, LINK_NON_VALIDO);
  }
  const u = await c.internalAdapter.findUserByEmail(g.email, { includeAccounts: true });
  // Utente tolto o sostituito da una nuova registrazione con la stessa email: il link vecchio non vale più
  if (!u || u.user.id !== g.userId) return errore(400, LINK_NON_VALIDO);
  if (u.user.emailVerified) return errore(409, "Questa email è già confermata: accedi con email e password.");

  const hash = u.accounts.find((a) => a.providerId === "credential")?.password;
  const esito = await verificaConBlocco(c, u.user.id, async () => !!hash && (await c.password.verify({ hash, password: dati.password })));
  if (esito === "bloccato") return errore(429, "Troppi tentativi: riprova tra 15 minuti.");
  if (esito === "sbagliata") return errore(401, PASSWORD_SBAGLIATA);

  try {
    await auth.api.verifyEmail({ query: { token: dati.token } });
  } catch (e) {
    console.error("Conferma dell'email non riuscita", u.user.id, e instanceof Error ? e.message : e);
    return errore(500, "Non è stato possibile confermare l'email adesso. Riprova tra qualche minuto.");
  }

  // Email confermata: si entra, già nell'azienda del titolare (come fa la pagina di accesso dopo l'accesso)
  let entrata: { headers: Headers; response: { token: string } };
  try {
    entrata = await auth.api.signInEmail({ body: { email: g.email, password: dati.password }, headers: req.headers, returnHeaders: true });
  } catch (e) {
    console.error("Email confermata, accesso automatico non riuscito", u.user.id, e instanceof Error ? e.message : e);
    return ok({ ok: true, accesso: false });
  }
  const membri = await c.adapter.findMany<{ organizationId: string }>({ model: "member", where: [{ field: "userId", value: u.user.id }] });
  if (membri[0]) await c.internalAdapter.updateSession(entrata.response.token, { activeOrganizationId: membri[0].organizationId });
  const risposta = ok({ ok: true });
  for (const cookie of entrata.headers.getSetCookie()) risposta.headers.append("set-cookie", cookie);
  return conCookieSecure(req, risposta);
}
