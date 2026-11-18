// Ponte eBay Sandbox: chiamate vere alle API di prova di eBay (Italia). Solo server.
//
// Collegamento (OAuth "authorization code grant"): il responsabile tocca "Collega account eBay", accede a eBay
// e acconsente; eBay rimanda all'indirizzo collegato al RuName, che deve essere
//   https://<tunnel del prototipo>/api/ebay/ritorno
// (va scritto nel portale eBay Developers, sotto "User Tokens" → RuName → "auth accepted URL" e "auth declined URL").
// I token restano cifrati in ebay.json (archivio.ts); il browser vede solo lo StatoPonte.
//
// Forme e indirizzi verificati sulle specifiche ufficiali OpenAPI (vedi payload.ts). I punti marcati
// "da verificare in sandbox" non si possono provare senza un conto di prova.
import { randomBytes, timingSafeEqual } from "node:crypto";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { cifra, decifra } from "@/lib/cifratura";
import { PHOTO_DIR } from "@/lib/server-data";
import type { EsitoAllinea, Ponte, RichiestaAllinea, SpedizioneEbay, StatoPonte, VenditaEbay } from "./contratto";
import {
  ALBERO_CATEGORIE, aspettiPerEbay, controllaAspetti, ErroreEbay, fileFoto, inventoryItemBody, LINGUA, magazzinoBody, MARKETPLACE,
  NOMI_POLITICHE, nomiCompat, offerBody, offerUpdateBody, politicaPagamentoBody, politicaResoBody, politicaSpedizioneBody,
  rinominaCompat, statoDaOfferta, traduciErrore, urlConsenso, veicoliEbay, venditeDaOrdini,
  type MetaAspetti, type NomiCompat, type OffertaEbay, type OrdineEbay, type VeicoloEbay,
} from "./payload";
import { aggiornaArchivio, leggiArchivio, type ArchivioEbay, type RuoloPolitica } from "./archivio";

export interface CredSandbox { appId: string; certId: string; ruName: string }

const API = "https://api.sandbox.ebay.com";
const MEDIA = "https://apim.sandbox.ebay.com/commerce/media/v1_beta";
const CONSENSO = "https://auth.sandbox.ebay.com/oauth2/authorize";
const TOKEN = "https://api.sandbox.ebay.com/identity/v1/oauth2/token";
const TRADING = "https://api.sandbox.ebay.com/ws/api.dll";
const VISTA = "https://www.sandbox.ebay.it/itm/";
const SITO_IT = "101";
const LIVELLO_TRADING = "1451"; // X-EBAY-API-COMPATIBILITY-LEVEL: versione recente della Trading API

const SCOPE_UTENTE = [
  "https://api.ebay.com/oauth/api_scope",
  "https://api.ebay.com/oauth/api_scope/sell.inventory",
  "https://api.ebay.com/oauth/api_scope/sell.account",
  "https://api.ebay.com/oauth/api_scope/sell.fulfillment",
];
const SCOPE_APP = ["https://api.ebay.com/oauth/api_scope"];
const MARGINE_TOKEN = 5 * 60_000; // si rinnova quando mancano meno di 5 minuti
const DURATA_STATE = 10 * 60_000;

const NON_COLLEGATO = "Il conto eBay non è collegato. Cosa fare: in Impostazioni → Collegamenti tocca «Collega account eBay».";
const IMPREVISTO = "Errore imprevisto nel collegamento con eBay. Cosa fare: niente, il gestionale riprova da solo tra poco.";

// ── HTTP ──
interface Risposta { status: number; corpo: unknown; headers: Headers }

/** fetch verso eBay: gli errori diventano ErroreEbay in italiano; il testo grezzo va solo nel registro del server. */
async function http(url: string, init: RequestInit, cosa: string, ammessi: number[] = []): Promise<Risposta> {
  let res: Response;
  try {
    res = await fetch(url, { ...init, cache: "no-store", signal: AbortSignal.timeout(30_000) });
  } catch (e) {
    const t = traduciErrore(0, e instanceof Error ? e.message : String(e));
    console.error(`[ebay] ${cosa}: ${t.log}`);
    throw new ErroreEbay(t.messaggio, t.log);
  }
  const testo = await res.text();
  let corpo: unknown = testo;
  try {
    corpo = testo ? JSON.parse(testo) : undefined;
  } catch {
    // risposta non JSON (es. XML della Trading API)
  }
  if (!res.ok && !ammessi.includes(res.status)) {
    const t = traduciErrore(res.status, corpo);
    console.error(`[ebay] ${cosa}: ${t.log}`);
    throw new ErroreEbay(t.messaggio, t.log);
  }
  const avvisi = (corpo as { warnings?: unknown[] } | undefined)?.warnings;
  if (Array.isArray(avvisi) && avvisi.length) console.warn(`[ebay] ${cosa}: avvisi di eBay ${JSON.stringify(avvisi).slice(0, 800)}`);
  return { status: res.status, corpo, headers: res.headers };
}

const form = (v: Record<string, string>) => Object.entries(v).map(([k, x]) => `${k}=${encodeURIComponent(x)}`).join("&");
const basic = (c: CredSandbox) => `Basic ${Buffer.from(`${c.appId}:${c.certId}`).toString("base64")}`;

// ── Token ──
interface RispostaToken { access_token?: string; expires_in?: number; refresh_token?: string; refresh_token_expires_in?: number }

async function chiediToken(c: CredSandbox, corpo: Record<string, string>, cosa: string): Promise<RispostaToken> {
  const r = await http(TOKEN, { method: "POST", headers: { Authorization: basic(c), "Content-Type": "application/x-www-form-urlencoded" }, body: form(corpo) }, cosa);
  const t = r.corpo as RispostaToken;
  if (!t?.access_token) throw new ErroreEbay("eBay non ha dato il permesso di accesso. Cosa fare: in Impostazioni → Collegamenti tocca «Collega account eBay».", "risposta token senza access_token");
  return t;
}

const traMs = (s: number | undefined, predefinito: number) => new Date(Date.now() + (s ?? predefinito) * 1000).toISOString();

let rinnovo: Promise<string> | undefined;

async function rinnova(c: CredSandbox): Promise<string> {
  const a = await leggiArchivio();
  if (!a.token || a.conto !== c.appId) throw new ErroreEbay(NON_COLLEGATO);
  if (Date.parse(a.token.refreshScade) <= Date.now()) {
    throw new ErroreEbay("Il collegamento con eBay è scaduto (dura circa 18 mesi). Cosa fare: in Impostazioni → Collegamenti tocca «Collega account eBay».");
  }
  const refresh = (await decifra(a.token.refresh)).toString("utf8");
  const t = await chiediToken(c, { grant_type: "refresh_token", refresh_token: refresh, scope: SCOPE_UTENTE.join(" ") }, "rinnovo del token");
  const access = await cifra(Buffer.from(t.access_token!, "utf8"));
  await aggiornaArchivio((x) => {
    if (x.token) x.token = { ...x.token, access, scade: traMs(t.expires_in, 7200) };
  });
  return t.access_token!;
}

/** Token del conto collegato; si rinnova da solo quando mancano meno di 5 minuti (o se `forza`). */
async function tokenUtente(c: CredSandbox, forza = false): Promise<string> {
  const a = await leggiArchivio();
  if (!a.token || a.conto !== c.appId) throw new ErroreEbay(NON_COLLEGATO);
  if (!forza && Date.parse(a.token.scade) - Date.now() > MARGINE_TOKEN) {
    try {
      return (await decifra(a.token.access)).toString("utf8");
    } catch {
      // token illeggibile (chiave cambiata): si prova a rinnovarlo
    }
  }
  rinnovo ??= rinnova(c).finally(() => (rinnovo = undefined));
  return rinnovo;
}

let tokenApp: { token: string; scade: number; conto: string } | undefined;

/** Token dell'applicazione (client credentials) per la Taxonomy API. Solo in memoria. */
async function tokenApplicazione(c: CredSandbox): Promise<string> {
  if (tokenApp && tokenApp.conto === c.appId && tokenApp.scade - Date.now() > MARGINE_TOKEN) return tokenApp.token;
  const t = await chiediToken(c, { grant_type: "client_credentials", scope: SCOPE_APP.join(" ") }, "token dell'applicazione");
  tokenApp = { token: t.access_token!, scade: Date.now() + (t.expires_in ?? 7200) * 1000, conto: c.appId };
  return tokenApp.token;
}

// ── Chiamate alle API REST ──
interface Opz { corpo?: unknown; ammessi?: number[]; base?: string }

/** API "Sell" con il token del conto; con 401 rinnova il token una volta e riprova. */
async function sell(c: CredSandbox, metodo: string, percorso: string, cosa: string, o: Opz = {}): Promise<Risposta> {
  const prova = async (token: string) => {
    const headers: Record<string, string> = {
      Authorization: `Bearer ${token}`, Accept: "application/json", "Accept-Language": LINGUA, "X-EBAY-C-MARKETPLACE-ID": MARKETPLACE,
    };
    if (o.corpo !== undefined) {
      headers["Content-Type"] = "application/json";
      headers["Content-Language"] = LINGUA;
    }
    return http(`${o.base ?? API}${percorso}`, { method: metodo, headers, body: o.corpo === undefined ? undefined : JSON.stringify(o.corpo) }, cosa, [401, ...(o.ammessi ?? [])]);
  };
  let r = await prova(await tokenUtente(c));
  if (r.status === 401) r = await prova(await tokenUtente(c, true));
  if (r.status === 401) {
    const t = traduciErrore(401, r.corpo);
    console.error(`[ebay] ${cosa}: ${t.log}`);
    throw new ErroreEbay(t.messaggio, t.log);
  }
  return r;
}

async function tassonomia(c: CredSandbox, percorso: string, cosa: string): Promise<unknown> {
  const r = await http(`${API}/commerce/taxonomy/v1/category_tree/${ALBERO_CATEGORIE}${percorso}`, {
    headers: { Authorization: `Bearer ${await tokenApplicazione(c)}`, Accept: "application/json", "Accept-Language": LINGUA },
  }, cosa);
  return r.corpo;
}

const enc = encodeURIComponent;

// ── Politiche e magazzino ──
interface Opzione { id: string; nome: string; ritiro?: boolean }
export interface OpzioniEbay { pagamento: Opzione[]; reso: Opzione[]; spedizione: Opzione[]; magazzini: Opzione[] }

async function leggiOpzioni(c: CredSandbox, tollera = false): Promise<OpzioniEbay> {
  const leggi = async <T>(percorso: string, cosa: string, prendi: (x: unknown) => T[]): Promise<T[]> => {
    try {
      return prendi((await sell(c, "GET", percorso, cosa)).corpo);
    } catch (e) {
      // Un conto di prova senza adesione alle politiche risponde con errore: vale come "nessuna politica"
      if (tollera && e instanceof ErroreEbay) return [];
      throw e;
    }
  };
  const q = `?marketplace_id=${MARKETPLACE}`;
  const [spedizione, pagamento, reso, magazzini] = await Promise.all([
    leggi(`/sell/account/v1/fulfillment_policy${q}`, "politiche di spedizione", (x) =>
      ((x as { fulfillmentPolicies?: { fulfillmentPolicyId: string; name: string; localPickup?: boolean }[] })?.fulfillmentPolicies ?? [])
        .map((p) => ({ id: p.fulfillmentPolicyId, nome: p.name, ritiro: !!p.localPickup }))),
    leggi(`/sell/account/v1/payment_policy${q}`, "politiche di pagamento", (x) =>
      ((x as { paymentPolicies?: { paymentPolicyId: string; name: string }[] })?.paymentPolicies ?? []).map((p) => ({ id: p.paymentPolicyId, nome: p.name }))),
    leggi(`/sell/account/v1/return_policy${q}`, "politiche di reso", (x) =>
      ((x as { returnPolicies?: { returnPolicyId: string; name: string }[] })?.returnPolicies ?? []).map((p) => ({ id: p.returnPolicyId, nome: p.name }))),
    leggi(`/sell/inventory/v1/location?limit=100`, "magazzini", (x) =>
      ((x as { locations?: { merchantLocationKey: string; name?: string; merchantLocationStatus?: string }[] })?.locations ?? [])
        .filter((l) => l.merchantLocationStatus !== "DISABLED").map((l) => ({ id: l.merchantLocationKey, nome: l.name || l.merchantLocationKey }))),
  ]);
  return { spedizione, pagamento, reso, magazzini };
}

/**
 * Solo Sandbox: crea politiche e magazzino di base se il conto di prova non ne ha. Questo ponte gira solo
 * con l'ambiente Sandbox (scegliPonte in server.ts); un futuro ponte di produzione non deve chiamarla.
 */
async function creaPredefiniti(c: CredSandbox, o: OpzioniEbay): Promise<boolean> {
  const mancaPolitica = !o.pagamento.length || !o.reso.length || !o.spedizione.length;
  if (!mancaPolitica && o.magazzini.length) return false;
  if (mancaPolitica) {
    // Da verificare in sandbox: l'adesione alle politiche (SELLING_POLICY_MANAGEMENT) può richiedere qualche minuto
    await sell(c, "POST", "/sell/account/v1/program/opt_in", "adesione alle politiche", { corpo: { programType: "SELLING_POLICY_MANAGEMENT" }, ammessi: [400, 409] });
  }
  if (!o.pagamento.length) await sell(c, "POST", "/sell/account/v1/payment_policy", "politica di pagamento", { corpo: politicaPagamentoBody() });
  if (!o.reso.length) await sell(c, "POST", "/sell/account/v1/return_policy", "politica di reso", { corpo: politicaResoBody() });
  if (!o.spedizione.length) {
    for (const t of ["corriere", "voluminoso", "ritiro"] as const) {
      await sell(c, "POST", "/sell/account/v1/fulfillment_policy", `politica «${NOMI_POLITICHE[t]}»`, { corpo: politicaSpedizioneBody(t) });
    }
  }
  if (!o.magazzini.length) await sell(c, "POST", "/sell/inventory/v1/location/sede", "magazzino", { corpo: magazzinoBody() });
  return true;
}

function scegli(o: OpzioniEbay, a: ArchivioEbay): Pick<ArchivioEbay, "politiche" | "magazzino"> {
  const valida = (lista: Opzione[], s?: { id: string }) => (s ? lista.find((x) => x.id === s.id) : undefined);
  const perNome = (lista: Opzione[], nome: string) => lista.find((x) => x.nome.trim().toLowerCase() === nome.toLowerCase());
  const togli = (x?: Opzione) => (x ? { id: x.id, nome: x.nome } : undefined);
  const corriere = valida(o.spedizione, a.politiche.corriere) ?? perNome(o.spedizione, NOMI_POLITICHE.corriere) ?? o.spedizione.find((x) => !x.ritiro) ?? o.spedizione[0];
  return {
    politiche: {
      pagamento: togli(valida(o.pagamento, a.politiche.pagamento) ?? o.pagamento[0]),
      reso: togli(valida(o.reso, a.politiche.reso) ?? o.reso[0]),
      corriere: togli(corriere),
      voluminoso: togli(valida(o.spedizione, a.politiche.voluminoso) ?? perNome(o.spedizione, NOMI_POLITICHE.voluminoso) ?? corriere),
      ritiro: togli(valida(o.spedizione, a.politiche.ritiro) ?? perNome(o.spedizione, NOMI_POLITICHE.ritiro) ?? o.spedizione.find((x) => x.ritiro)),
    },
    magazzino: togli(valida(o.magazzini, a.magazzino) ?? o.magazzini.find((x) => x.id === "sede") ?? o.magazzini[0]),
  };
}

/** Legge politiche e magazzini; se mancano li crea (Sandbox) e sceglie quelli di serie dove non c'è una scelta. */
async function prepara(c: CredSandbox): Promise<void> {
  let o = await leggiOpzioni(c, true);
  if (await creaPredefiniti(c, o)) o = await leggiOpzioni(c);
  const a = await leggiArchivio();
  const s = scegli(o, a);
  await aggiornaArchivio((x) => {
    x.politiche = s.politiche;
    x.magazzino = s.magazzino;
  });
}

// ── "Esaurito": annunci a zero pezzi restano attivi (Trading API, SetUserPreferences) ──
async function attivaEsaurito(c: CredSandbox): Promise<void> {
  const xml = `<?xml version="1.0" encoding="utf-8"?>
<SetUserPreferencesRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <OutOfStockControlPreference>true</OutOfStockControlPreference>
</SetUserPreferencesRequest>`;
  const r = await http(TRADING, {
    method: "POST",
    headers: {
      "Content-Type": "text/xml", "X-EBAY-API-SITEID": SITO_IT, "X-EBAY-API-COMPATIBILITY-LEVEL": LIVELLO_TRADING,
      "X-EBAY-API-CALL-NAME": "SetUserPreferences", "X-EBAY-API-IAF-TOKEN": await tokenUtente(c),
    },
    body: xml,
  }, "attivazione di «esaurito»");
  const testo = String(r.corpo ?? "");
  const ack = testo.match(/<Ack>(\w+)<\/Ack>/)?.[1];
  if (ack !== "Success" && ack !== "Warning") {
    const codice = testo.match(/<ErrorCode>(\d+)<\/ErrorCode>/)?.[1];
    const log = `SetUserPreferences ${ack} [${codice}] ${testo.match(/<LongMessage>([^<]*)<\/LongMessage>/)?.[1] ?? ""}`;
    console.error(`[ebay] ${log}`);
    throw new ErroreEbay(`eBay non ha attivato «esaurito»${codice ? ` (codice ${codice})` : ""}. Cosa fare: in Impostazioni → Collegamenti tocca di nuovo «Collega account eBay».`, log);
  }
  await aggiornaArchivio((x) => {
    x.esauritoAttivo = true;
  });
}

// ── Collegamento ──
/** Indirizzo della pagina di consenso di eBay, con un `state` casuale salvato per 10 minuti. */
export async function avviaCollegamento(c: CredSandbox): Promise<string> {
  const state = randomBytes(24).toString("base64url");
  await aggiornaArchivio((x) => {
    x.state = { valore: state, scade: new Date(Date.now() + DURATA_STATE).toISOString() };
  });
  return urlConsenso(CONSENSO, c.appId, c.ruName, SCOPE_UTENTE, state);
}

const uguali = (a: string, b: string) => {
  const x = Buffer.from(a);
  const y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
};

/**
 * Ritorno dal consenso: controlla lo state, scambia il codice, salva i token cifrati, attiva "esaurito",
 * legge (o crea, in Sandbox) politiche e magazzino. Restituisce un messaggio in italiano se qualcosa non va.
 */
export async function completaCollegamento(c: CredSandbox, code: string, state: string): Promise<{ ok: true } | { ok: false; messaggio: string }> {
  const atteso = await aggiornaArchivio((x) => {
    const s = x.state;
    delete x.state; // un solo uso
    return s;
  });
  // Senza codice (consenso rifiutato su eBay) non si scambia niente: basta dirlo
  if (!code) return { ok: false, messaggio: "Il collegamento su eBay non è stato autorizzato. Cosa fare: tocca di nuovo «Collega account eBay» e acconsenti." };
  if (!atteso || Date.parse(atteso.scade) < Date.now() || !state || !uguali(atteso.valore, state)) {
    return { ok: false, messaggio: "Il ritorno da eBay non corrisponde a una richiesta partita da qui. Cosa fare: tocca di nuovo «Collega account eBay»." };
  }
  try {
    const t = await chiediToken(c, { grant_type: "authorization_code", code, redirect_uri: c.ruName }, "scambio del codice");
    if (!t.refresh_token) throw new ErroreEbay("eBay non ha dato il permesso di rinnovo. Cosa fare: tocca di nuovo «Collega account eBay».", "risposta senza refresh_token");
    const access = await cifra(Buffer.from(t.access_token!, "utf8"));
    const refresh = await cifra(Buffer.from(t.refresh_token, "utf8"));
    await aggiornaArchivio((x) => {
      x.conto = c.appId;
      x.token = { access, scade: traMs(t.expires_in, 7200), refresh, refreshScade: traMs(t.refresh_token_expires_in, 47_304_000) };
      x.esauritoAttivo = false;
      delete x.errore;
    });
    await attivaEsaurito(c);
    await prepara(c);
    return { ok: true };
  } catch (e) {
    const messaggio = e instanceof ErroreEbay ? e.message : IMPREVISTO;
    if (!(e instanceof ErroreEbay)) console.error("[ebay] collegamento", e);
    await aggiornaArchivio((x) => {
      x.errore = messaggio;
    });
    return { ok: false, messaggio };
  }
}

/** Scollega il conto: toglie token e scelte (l'annuncio già su eBay resta lì). */
export async function scollega(): Promise<void> {
  await aggiornaArchivio((x) => {
    delete x.token;
    delete x.conto;
    delete x.state;
    delete x.errore;
    x.esauritoAttivo = undefined;
    x.politiche = {};
    delete x.magazzino;
  });
}

/** Politiche e magazzini del conto, con le scelte attuali (per la pagina Collegamenti). Nessun segreto. */
export async function politicheConScelte(c: CredSandbox): Promise<{ opzioni: OpzioniEbay; scelte: ArchivioEbay["politiche"]; magazzino?: { id: string; nome: string } }> {
  const opzioni = await leggiOpzioni(c);
  const a = await leggiArchivio();
  return { opzioni, scelte: a.politiche, magazzino: a.magazzino };
}

const RUOLI: RuoloPolitica[] = ["pagamento", "reso", "corriere", "voluminoso", "ritiro"];

/** Salva le scelte: ogni id deve esistere tra le politiche del conto, del tipo giusto. */
export async function salvaScelte(c: CredSandbox, b: unknown): Promise<{ ok: true } | { ok: false; messaggio: string }> {
  if (typeof b !== "object" || b === null) return { ok: false, messaggio: "Scelte non valide" };
  const v = b as Record<string, unknown>;
  const o = await leggiOpzioni(c);
  const lista = (r: RuoloPolitica) => (r === "pagamento" ? o.pagamento : r === "reso" ? o.reso : o.spedizione);
  const politiche: ArchivioEbay["politiche"] = {};
  for (const r of RUOLI) {
    if (v[r] === undefined || v[r] === "") continue;
    const x = lista(r).find((p) => p.id === v[r]);
    if (!x) return { ok: false, messaggio: "Una politica scelta non esiste più su eBay: ricarica la pagina." };
    politiche[r] = { id: x.id, nome: x.nome };
  }
  let magazzino: { id: string; nome: string } | undefined;
  if (typeof v.magazzino === "string" && v.magazzino) {
    const m = o.magazzini.find((x) => x.id === v.magazzino);
    if (!m) return { ok: false, messaggio: "Il magazzino scelto non esiste più su eBay: ricarica la pagina." };
    magazzino = { id: m.id, nome: m.nome };
  }
  await aggiornaArchivio((x) => {
    x.politiche = { ...x.politiche, ...politiche };
    if (magazzino) x.magazzino = magazzino;
  });
  return { ok: true };
}

// ── Allineamento di un annuncio ──
async function offertaPer(c: CredSandbox, sku: string): Promise<OffertaEbay & { format?: string; marketplaceId?: string } | undefined> {
  // Senza offerte eBay risponde 404 (errore 25713): vale come "nessuna offerta"
  const r = await sell(c, "GET", `/sell/inventory/v1/offer?sku=${enc(sku)}`, "lettura dell'offerta", { ammessi: [404] });
  if (r.status === 404) return undefined;
  const offerte = ((r.corpo as { offers?: (OffertaEbay & { format?: string; marketplaceId?: string })[] })?.offers ?? []);
  return offerte.find((x) => x.format === "FIXED_PRICE" && x.marketplaceId === MARKETPLACE) ?? offerte.find((x) => x.format === "FIXED_PRICE");
}

async function categoriaPer(c: CredSandbox, r: RichiestaAllinea, a: ArchivioEbay): Promise<{ id: string; nome?: string }> {
  if (r.categoriaId) return { id: r.categoriaId, nome: Object.values(a.categorie).find((x) => x.id === r.categoriaId)?.nome };
  const q = r.categoriaQuery.trim();
  if (!q) throw new ErroreEbay("Manca la parola per cercare la categoria eBay. Cosa fare: scegli la categoria nell'annuncio.");
  const chiave = q.toLowerCase();
  if (a.categorie[chiave]) return a.categorie[chiave];
  const corpo = (await tassonomia(c, `/get_category_suggestions?q=${enc(q)}`, "ricerca della categoria")) as { categorySuggestions?: { category?: { categoryId?: string; categoryName?: string } }[] };
  const cat = corpo?.categorySuggestions?.find((s) => s.category?.categoryId)?.category;
  if (!cat?.categoryId) throw new ErroreEbay(`eBay non trova una categoria per «${q.slice(0, 60)}». Cosa fare: scegli la categoria nell'annuncio.`);
  const trovata = { id: cat.categoryId, nome: cat.categoryName ?? cat.categoryId };
  await aggiornaArchivio((x) => {
    x.categorie[chiave] = trovata;
  });
  return trovata;
}

const GIORNO = 24 * 3600_000;
const cacheAspetti = new Map<string, { meta: MetaAspetti; at: number }>();

async function aspettiCategoria(c: CredSandbox, categoria: string): Promise<MetaAspetti> {
  const x = cacheAspetti.get(categoria);
  if (x && Date.now() - x.at < GIORNO) return x.meta;
  const meta = (await tassonomia(c, `/get_item_aspects_for_category?category_id=${enc(categoria)}`, "caratteristiche della categoria")) as MetaAspetti;
  cacheAspetti.set(categoria, { meta, at: Date.now() });
  return meta;
}

/** Carica su eBay (createImageFromFile) le foto non ancora caricate; una volta per file. */
async function caricaFoto(c: CredSandbox, foto: string[], a: ArchivioEbay, avvisi: string[]): Promise<string[]> {
  const out: string[] = [];
  for (const url of foto.slice(0, 24)) {
    const gia = a.foto[url];
    if (gia && (!gia.scade || Date.parse(gia.scade) - Date.now() > GIORNO)) {
      out.push(gia.url);
      continue;
    }
    const f = fileFoto(url);
    if (!f) {
      avvisi.push("Una foto non è del gestionale e non è stata mandata a eBay.");
      continue;
    }
    const cartella = f.cartella === "foto" ? PHOTO_DIR : path.join(/*turbopackIgnore: true*/ process.cwd(), "public");
    let dati: Buffer;
    try {
      dati = await readFile(path.join(cartella, f.nome));
    } catch {
      avvisi.push("Una foto non si trova più sul server e non è stata mandata a eBay.");
      continue;
    }
    const caricata = await caricaUna(c, dati, f.tipo, path.basename(f.nome));
    out.push(caricata.url);
    await aggiornaArchivio((x) => {
      x.foto[url] = caricata;
    });
  }
  return out;
}

/** POST multipart con il campo "image"; eBay risponde 201 con imageUrl (e l'id nell'header Location). */
async function caricaUna(c: CredSandbox, dati: Buffer, tipo: string, nome: string): Promise<{ url: string; scade?: string }> {
  const prova = async (token: string) => {
    const fd = new FormData();
    fd.append("image", new Blob([new Uint8Array(dati)], { type: tipo }), nome);
    // Content-Type multipart/form-data con il boundary lo mette fetch
    return http(`${MEDIA}/image/create_image_from_file`, { method: "POST", headers: { Authorization: `Bearer ${token}`, Accept: "application/json" }, body: fd }, "caricamento di una foto", [401]);
  };
  let r = await prova(await tokenUtente(c));
  if (r.status === 401) r = await prova(await tokenUtente(c, true));
  if (r.status === 401) throw new ErroreEbay(traduciErrore(401, r.corpo).messaggio);
  let img = r.corpo as { imageUrl?: string; expirationDate?: string } | undefined;
  if (!img?.imageUrl) {
    // Da verificare in sandbox: se il corpo è vuoto, l'URL si legge con getImage dall'id nell'header Location
    const id = r.headers.get("location")?.split("/").pop();
    if (id) img = (await sell(c, "GET", `/image/${enc(id)}`, "lettura di una foto", { base: MEDIA })).corpo as typeof img;
  }
  if (!img?.imageUrl) throw new ErroreEbay("eBay non ha restituito l'indirizzo di una foto. Cosa fare: niente, il gestionale riprova da solo tra poco.");
  return { url: img.imageUrl, scade: img.expirationDate };
}

const norm = (s: string) => s.toLowerCase().replace(/[\s._-]+/g, "");
const cacheValori = new Map<string, { valori: string[]; at: number }>();

async function valoriCompat(c: CredSandbox, categoria: string, prop: string, filtro: [string, string][]): Promise<string[]> {
  const f = filtro.map(([n, v]) => `${n}:${v.replace(/,/g, "\\,")}`).join(",");
  const k = JSON.stringify([categoria, prop, f]);
  const x = cacheValori.get(k);
  if (x && Date.now() - x.at < GIORNO) return x.valori;
  const corpo = (await tassonomia(c, `/get_compatibility_property_values?category_id=${enc(categoria)}&compatibility_property=${enc(prop)}${f ? `&filter=${enc(f)}` : ""}`, "valori dei veicoli")) as { compatibilityPropertyValues?: { value?: string }[] };
  const valori = (corpo?.compatibilityPropertyValues ?? []).flatMap((v) => (v.value ? [v.value] : []));
  cacheValori.set(k, { valori, at: Date.now() });
  return valori;
}

/**
 * Veicoli compatibili tradotti con i valori di eBay Italia (getCompatibilityPropertyValues): marca, modello e anno devono
 * esistere; il motore, se eBay non lo riconosce, si toglie. I veicoli non trovati diventano avvisi.
 */
async function mandaCompatibilita(c: CredSandbox, r: RichiestaAllinea, categoria: string, avvisi: string[]): Promise<void> {
  const veicoli = veicoliEbay(r.compatibilita).slice(0, 100);
  if (!veicoli.length) return;
  const props = (await tassonomia(c, `/get_compatibility_properties?category_id=${enc(categoria)}`, "proprietà dei veicoli").catch(() => undefined)) as { compatibilityProperties?: { name?: string; localizedName?: string }[] } | undefined;
  const nomi: NomiCompat | undefined = nomiCompat(props?.compatibilityProperties ?? []);
  if (!nomi) {
    avvisi.push("La categoria eBay non accetta i veicoli compatibili: l'annuncio esce senza.");
    return;
  }
  const trova = (lista: string[], v: string) => lista.find((x) => norm(x) === norm(v));
  const trovati: VeicoloEbay[] = [];
  const persi = new Set<string>();
  const senzaMotore = new Set<string>();
  for (const v of veicoli) {
    const nome = `${v.make} ${v.model}${v.year ? ` ${v.year}` : ""}`;
    const make = trova(await valoriCompat(c, categoria, nomi.make, []), v.make);
    const model = make && trova(await valoriCompat(c, categoria, nomi.model, [[nomi.make, make]]), v.model);
    const year = model && v.year ? trova(await valoriCompat(c, categoria, nomi.year, [[nomi.make, make], [nomi.model, model]]), v.year) : undefined;
    if (!make || !model || (v.year && !year)) {
      persi.add(nome);
      continue;
    }
    let engine: string | undefined;
    if (v.engine && nomi.engine) {
      const filtro: [string, string][] = [[nomi.make, make], [nomi.model, model], ...(year ? [[nomi.year, year] as [string, string]] : [])];
      engine = trova(await valoriCompat(c, categoria, nomi.engine, filtro), v.engine);
      if (!engine) senzaMotore.add(`${v.make} ${v.model} (${v.engine})`);
    }
    trovati.push({ make, model, ...(year ? { year } : {}), ...(engine ? { engine } : {}) });
  }
  for (const p of persi) avvisi.push(`Veicolo non trovato nell'elenco di eBay: ${p}. Non è tra i compatibili.`);
  for (const m of senzaMotore) avvisi.push(`Motore non riconosciuto da eBay per ${m}: compatibilità senza motore.`);
  if (!trovati.length) return;
  await sell(c, "PUT", `/sell/inventory/v1/inventory_item/${enc(r.sku)}/product_compatibility`, "veicoli compatibili", { corpo: rinominaCompat(trovati, nomi) });
}

const link = (listingId?: string) => (listingId ? `${VISTA}${enc(listingId)}` : undefined);

async function allineaSandbox(c: CredSandbox, r: RichiestaAllinea): Promise<EsitoAllinea> {
  const avvisi: string[] = [];
  const offerta = await offertaPer(c, r.sku);
  let a = await leggiArchivio();
  const statoOff = statoDaOfferta(offerta);
  const listingPrima = offerta?.listing?.listingId ?? a.pubblicati[r.sku];

  // Ritiro: basta togliere l'annuncio, il resto non serve
  if (!r.attivo) {
    if (offerta?.offerId && statoOff === "pubblicata") {
      await sell(c, "POST", `/sell/inventory/v1/offer/${enc(offerta.offerId)}/withdraw`, "ritiro dell'annuncio");
    }
    await aggiornaArchivio((x) => {
      x.ritirati[r.sku] = true;
    });
    return { stato: "ritirato", listingId: listingPrima, url: link(listingPrima), avvisi };
  }

  // Annuncio chiuso da eBay (dopo molto tempo a zero pezzi) e non ritirato da noi: a zero resta chiuso, con pezzi si ripubblica
  const chiusoDaEbay = statoOff === "chiusa" || (statoOff === "non pubblicata" && !!listingPrima && !a.ritirati[r.sku]);
  if (chiusoDaEbay && r.quantita === 0) return { stato: "chiuso da eBay", listingId: listingPrima, url: link(listingPrima), avvisi };

  if (r.gpsr.tipo === "da confermare") throw new ErroreEbay("Mancano i dati di sicurezza del prodotto (GPSR). Cosa fare: conferma il GPSR nell'annuncio e riprova.");

  // Politiche e magazzino: se manca qualcosa si rilegge (e in Sandbox si crea)
  if (!a.politiche.pagamento || !a.politiche.reso || !a.politiche[r.spedizione] || !a.magazzino) {
    await prepara(c);
    a = await leggiArchivio();
  }
  const sped = a.politiche[r.spedizione];
  if (!a.politiche.pagamento || !a.politiche.reso || !sped || !a.magazzino) {
    const manca = !sped ? `la politica «${NOMI_POLITICHE[r.spedizione as SpedizioneEbay]}»` : !a.magazzino ? "il magazzino" : "una politica di pagamento o di reso";
    throw new ErroreEbay(`Su eBay manca ${manca}. Cosa fare: in Impostazioni → Collegamenti scegli le politiche eBay.`);
  }

  const categoria = await categoriaPer(c, r, a);
  let aspetti = aspettiPerEbay(r.caratteristiche);
  try {
    const controllo = controllaAspetti(aspetti, await aspettiCategoria(c, categoria.id));
    aspetti = controllo.aspetti;
    avvisi.push(...controllo.avvisi);
  } catch (e) {
    if (!(e instanceof ErroreEbay)) throw e;
    avvisi.push("Non riesco a leggere da eBay le caratteristiche della categoria: mandate senza controllo.");
  }

  const foto = await caricaFoto(c, r.foto, a, avvisi);
  if (!foto.length) avvisi.push("Nessuna foto: eBay chiede almeno una foto per pubblicare.");

  await sell(c, "PUT", `/sell/inventory/v1/inventory_item/${enc(r.sku)}`, "salvataggio dell'articolo", { corpo: inventoryItemBody(r, foto, aspetti) });

  try {
    await mandaCompatibilita(c, r, categoria.id, avvisi);
  } catch (e) {
    if (!(e instanceof ErroreEbay)) throw e;
    avvisi.push(`Veicoli compatibili non mandati: ${e.message}`);
  }

  const corpo = offerBody(r, categoria.id, { pagamento: a.politiche.pagamento.id, reso: a.politiche.reso.id, spedizione: sped.id }, a.magazzino.id);
  let offerId = offerta?.offerId;
  if (!offerId) {
    offerId = ((await sell(c, "POST", "/sell/inventory/v1/offer", "creazione dell'offerta", { corpo })).corpo as { offerId?: string })?.offerId;
    if (!offerId) throw new ErroreEbay("eBay non ha restituito il numero dell'offerta. Cosa fare: niente, il gestionale riprova da solo tra poco.");
  } else {
    // updateOffer sostituisce tutta l'offerta; su un'offerta pubblicata aggiorna l'annuncio online
    await sell(c, "PUT", `/sell/inventory/v1/offer/${enc(offerId)}`, "aggiornamento dell'offerta", { corpo: offerUpdateBody(corpo) });
  }

  let listingId = statoOff === "pubblicata" ? offerta?.listing?.listingId : undefined;
  if (statoOff !== "pubblicata" && r.quantita > 0) {
    // Da verificare in sandbox: publishOffer su un annuncio finito (ENDED) lo rimette online con un nuovo numero
    listingId = ((await sell(c, "POST", `/sell/inventory/v1/offer/${enc(offerId)}/publish`, "pubblicazione dell'annuncio")).corpo as { listingId?: string })?.listingId;
  }
  await aggiornaArchivio((x) => {
    if (listingId) x.pubblicati[r.sku] = listingId;
    delete x.ritirati[r.sku];
  });
  if (r.quantita === 0 && listingId && !a.esauritoAttivo) {
    avvisi.push("Su eBay «esaurito» non risulta attivo: a zero pezzi eBay potrebbe chiudere l'annuncio. Cosa fare: ricollega il conto eBay.");
  }
  return {
    stato: listingId && r.quantita > 0 ? "online" : "esaurito",
    listingId,
    url: link(listingId),
    categoria: categoria.nome ? { id: categoria.id, nome: categoria.nome } : undefined,
    avvisi,
  };
}

// ── Vendite ──
async function venditeSandbox(c: CredSandbox, da: string): Promise<VenditaEbay[]> {
  // getOrders restituisce al più due anni di ordini
  const inizio = new Date(Math.max(Date.parse(da), Date.now() - 2 * 365 * GIORNO + GIORNO)).toISOString();
  const ordini: OrdineEbay[] = [];
  const LIMITE = 200;
  for (let offset = 0, pagine = 0; pagine < 20; pagine++, offset += LIMITE) {
    const q = `filter=${enc(`creationdate:[${inizio}..]`)}&limit=${LIMITE}&offset=${offset}`;
    const corpo = (await sell(c, "GET", `/sell/fulfillment/v1/order?${q}`, "lettura degli ordini")).corpo as { orders?: OrdineEbay[]; total?: number };
    ordini.push(...(corpo?.orders ?? []));
    if (!corpo?.orders?.length || offset + LIMITE >= (corpo.total ?? 0)) break;
  }
  await aggiornaArchivio((x) => {
    x.ultimoControllo = new Date().toISOString();
  });
  return venditeDaOrdini(ordini);
}

export function creaPonteSandbox(cred: CredSandbox): Ponte {
  return {
    async allinea(r: RichiestaAllinea): Promise<EsitoAllinea> {
      try {
        return await allineaSandbox(cred, r);
      } catch (e) {
        if (e instanceof ErroreEbay) return { stato: "errore", avvisi: [], errore: e.message };
        console.error("[ebay] allinea", e);
        return { stato: "errore", avvisi: [], errore: IMPREVISTO };
      }
    },
    vendite: (da: string) => venditeSandbox(cred, da),
    async stato(): Promise<StatoPonte> {
      const a = await leggiArchivio();
      const collegato = !!a.token && a.conto === cred.appId && Date.parse(a.token.refreshScade) > Date.now();
      const p = a.politiche;
      return {
        modo: "Sandbox",
        collegato,
        esauritoAttivo: collegato ? !!a.esauritoAttivo : undefined,
        politiche: { pagamento: p.pagamento, reso: p.reso, corriere: p.corriere, voluminoso: p.voluminoso, ritiro: p.ritiro },
        errore: a.errore,
      };
    },
  };
}
