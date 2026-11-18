// Corpi delle chiamate a eBay e letture delle risposte. Modulo puro: solo import di tipi, nessuna rete.
// Lo usa il ponte Sandbox (sandbox.ts). Forme dei campi verificate sulle specifiche ufficiali OpenAPI di eBay
// (developer.ebay.com/develop/api/spec/inventory_api.json, account_api_v1.json, taxonomy_api.json,
// fulfillment_api.json, media_api.json), scaricate il 18/11/2026.
import type { Condition, Gpsr, VeicoloCompat } from "../types";
import type { RichiestaAllinea, SpedizioneEbay, VenditaEbay } from "./contratto";

export const MARKETPLACE = "EBAY_IT";
export const VALUTA = "EUR";
export const LINGUA = "it-IT";
export const ALBERO_CATEGORIE = "101";
const MAX_TITOLO = 80;
const MAX_FOTO = 24;

/** Errore già tradotto in italiano semplice: il messaggio si può mostrare all'operatore. */
export class ErroreEbay extends Error {
  readonly log: string;
  constructor(messaggio: string, log = "") {
    super(messaggio);
    this.name = "ErroreEbay";
    this.log = log;
  }
}

// ── Condizione ──
// Ricambi usati su eBay Italia: "Usato" (3000 = USED_EXCELLENT) o "Per ricambi o non funzionante" (7000).
// Le lettere A, B, C restano nella descrizione della condizione. Copia di CONDITIONS di catalog.ts
// (un test controlla che coincidano): il modulo puro non può importarla.
const CONDIZIONI: Record<Condition, { label: string; hint: string }> = {
  A: { label: "Come nuovo", hint: "Nessun segno, perfettamente funzionante" },
  B: { label: "Buono", hint: "Segni d'uso lievi, funzionante" },
  C: { label: "Usurato", hint: "Usura visibile o piccoli difetti" },
  D: { label: "Da revisionare", hint: "Per ricambio o rigenerazione" },
};

export function conditionFor(c: Condition): string {
  return c === "D" ? "FOR_PARTS_OR_NOT_WORKING" : "USED_EXCELLENT";
}

function conditionDescription(c: Condition): string {
  return `Condizione ${c} (${CONDIZIONI[c].label}): ${CONDIZIONI[c].hint}.`;
}

// ── Caratteristiche ──
const LATI: Record<string, string> = { anteriore: "Anteriore", posteriore: "Posteriore", sx: "Sinistra", sinistro: "Sinistra", sinistra: "Sinistra", dx: "Destra", destro: "Destra", destra: "Destra" };

/** Lato dell'app ("Anteriore dx") → valori in stile eBay per "Posizionamento sul veicolo" (["Anteriore", "Destra"]). */
export function posizionamento(lato: string): string[] {
  const parole = lato.split(/[\s,]+/).filter(Boolean);
  const out = parole.map((p) => LATI[p.toLowerCase()] ?? p);
  return out.length ? out : [lato];
}

/** Caratteristiche dell'annuncio → aspects di eBay (ogni valore è un elenco). Vuote tolte. */
export function aspettiPerEbay(c: Record<string, string>): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const [k, v] of Object.entries(c)) {
    const val = v.trim();
    if (!val) continue;
    out[k] = k === "Posizionamento sul veicolo" ? posizionamento(val) : [val];
  }
  return out;
}

export interface MetaAspetti {
  aspects?: { localizedAspectName?: string; aspectConstraint?: { aspectRequired?: boolean; aspectMode?: string }; aspectValues?: { localizedValue?: string }[] }[];
}

/**
 * Confronta le caratteristiche con quelle della categoria (getItemAspectsForCategory): le obbligatorie mancanti e i
 * valori che eBay non riconosce (caratteristiche a scelta chiusa) diventano avvisi; i valori non riconosciuti non si mandano.
 */
export function controllaAspetti(aspetti: Record<string, string[]>, meta: MetaAspetti): { aspetti: Record<string, string[]>; avvisi: string[] } {
  const avvisi: string[] = [];
  const out: Record<string, string[]> = { ...aspetti };
  const lower = (s: string) => s.trim().toLowerCase();
  for (const a of meta.aspects ?? []) {
    const nome = a.localizedAspectName;
    if (!nome) continue;
    const chiave = Object.keys(out).find((k) => lower(k) === lower(nome));
    if (!chiave) {
      if (a.aspectConstraint?.aspectRequired) avvisi.push(`eBay chiede la caratteristica «${nome}», che manca nell'annuncio.`);
      continue;
    }
    if (a.aspectConstraint?.aspectMode !== "SELECTION_ONLY" || !a.aspectValues?.length) continue;
    const ammessi = new Map(a.aspectValues.flatMap((v) => (v.localizedValue ? [[lower(v.localizedValue), v.localizedValue] as const] : [])));
    const buoni: string[] = [];
    for (const v of out[chiave]) {
      const giusto = ammessi.get(lower(v));
      if (giusto) buoni.push(giusto);
      else avvisi.push(`eBay non riconosce «${v}» per «${nome}»: non è stato mandato.`);
    }
    if (buoni.length) out[chiave] = buoni;
    else delete out[chiave];
  }
  return { aspetti: out, avvisi };
}

// ── Testo ──
const escapeHtml = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const descrizioneHtml = (s: string) => escapeHtml(s.trim()).replace(/\r?\n/g, "<br>");
const titolo = (s: string) => s.trim().slice(0, MAX_TITOLO);

// ── Articolo (createOrReplaceInventoryItem) ──
/**
 * Corpo di PUT /sell/inventory/v1/inventory_item/{sku} (header Content-Language: it-IT).
 * La quantità 0 resta: con "esaurito" attivo l'annuncio rimane online, nascosto, e torna in vendita da solo.
 * `aspetti`: caratteristiche già controllate con controllaAspetti; se manca si usano quelle della richiesta.
 */
export function inventoryItemBody(r: RichiestaAllinea, fotoEps: string[], aspetti?: Record<string, string[]>): object {
  return {
    availability: { shipToLocationAvailability: { quantity: r.quantita } },
    condition: conditionFor(r.condizione),
    conditionDescription: conditionDescription(r.condizione),
    product: {
      title: titolo(r.titolo),
      description: descrizioneHtml(r.descrizione),
      aspects: aspetti ?? aspettiPerEbay(r.caratteristiche),
      imageUrls: fotoEps.slice(0, MAX_FOTO),
    },
  };
}

// ── GPSR ──
const PAESI: Record<string, string> = {
  italia: "IT", germania: "DE", francia: "FR", spagna: "ES", "paesi bassi": "NL", olanda: "NL", belgio: "BE", austria: "AT",
  svezia: "SE", "repubblica ceca": "CZ", polonia: "PL", portogallo: "PT", romania: "RO", slovacchia: "SK", ungheria: "HU",
  "regno unito": "GB", giappone: "JP", "corea del sud": "KR", "stati uniti": "US", cina: "CN",
};
const codicePaese = (p: string) => (/^[a-z]{2}$/i.test(p.trim()) ? p.trim().toUpperCase() : PAESI[p.trim().toLowerCase()] ?? p.trim());

// Nell'Inventory API i dati GPSR stanno nell'offerta (EbayOfferDetailsWithKeys.regulatory), non in product:
// lo schema Product non ha il campo regulatory.
function regulatory(g: Gpsr): object | undefined {
  if (g.tipo === "esente") return undefined;
  if (g.tipo === "da confermare") throw new ErroreEbay("Mancano i dati di sicurezza del prodotto (GPSR). Cosa fare: conferma il GPSR nell'annuncio e riprova.");
  const p = g.produttore;
  return {
    manufacturer: {
      companyName: p.ragioneSociale.slice(0, 100),
      addressLine1: p.indirizzo.slice(0, 180),
      city: p.citta.slice(0, 64),
      postalCode: p.cap.slice(0, 9),
      country: codicePaese(p.paese),
      ...(p.email ? { email: p.email.slice(0, 180) } : {}),
      ...(p.sito ? { contactUrl: p.sito.slice(0, 250) } : {}),
    },
  };
}

// ── Offerta (createOffer / updateOffer) ──
/** Corpo di POST /sell/inventory/v1/offer. Per updateOffer (PUT /offer/{id}) si tolgono sku, marketplaceId e format. */
export function offerBody(
  r: RichiestaAllinea,
  categoriaId: string,
  politiche: { pagamento: string; reso: string; spedizione: string },
  location: string,
): object {
  const reg = regulatory(r.gpsr);
  return {
    sku: r.sku,
    marketplaceId: MARKETPLACE,
    format: "FIXED_PRICE",
    listingDuration: "GTC",
    availableQuantity: r.quantita,
    categoryId: categoriaId,
    listingDescription: descrizioneHtml(r.descrizione),
    listingPolicies: { fulfillmentPolicyId: politiche.spedizione, paymentPolicyId: politiche.pagamento, returnPolicyId: politiche.reso },
    merchantLocationKey: location,
    pricingSummary: { price: { value: r.prezzo.toFixed(2), currency: VALUTA } },
    ...(reg ? { regulatory: reg } : {}),
  };
}

export function offerUpdateBody(o: object): object {
  const rest: Record<string, unknown> = { ...o };
  delete rest.sku;
  delete rest.marketplaceId;
  delete rest.format;
  return rest;
}

// ── Compatibilità (createOrReplaceProductCompatibility) ──
export type VeicoloEbay = { make: string; model: string; year?: string; engine?: string };

function anniDi(v: VeicoloCompat, annoCorrente: number): (number | undefined)[] {
  if (v.anno !== undefined) return [v.anno];
  const m = v.anni?.match(/^\s*(\d{4})\s*[–—-]\s*(\d{4})?\s*$/);
  if (m) {
    const da = Number(m[1]);
    const a = Math.min(m[2] ? Number(m[2]) : annoCorrente, da + 40);
    return Array.from({ length: Math.max(0, a - da + 1) }, (_, i) => da + i);
  }
  const solo = v.anni?.match(/^\s*(\d{4})\s*$/);
  return solo ? [Number(solo[1])] : [undefined];
}

/** Un veicolo eBay per ogni anno: "2009–2012" diventa 2009, 2010, 2011, 2012; "2012–" arriva all'anno in corso. */
export function veicoliEbay(compat: VeicoloCompat[], annoCorrente = new Date().getFullYear()): VeicoloEbay[] {
  const out: VeicoloEbay[] = [];
  const visti = new Set<string>();
  for (const v of compat) {
    for (const anno of anniDi(v, annoCorrente)) {
      const e: VeicoloEbay = { make: v.marca, model: v.modello, ...(anno ? { year: String(anno) } : {}), ...(v.motore ? { engine: v.motore } : {}) };
      const k = JSON.stringify([e.make, e.model, e.year ?? "", e.engine ?? ""]);
      if (visti.has(k)) continue;
      visti.add(k);
      out.push(e);
    }
  }
  return out;
}

export interface NomiCompat { make: string; model: string; year: string; engine?: string }
const NOMI_BASE: NomiCompat = { make: "make", model: "model", year: "year", engine: "engine" };

/** Corpo di PUT /inventory_item/{sku}/product_compatibility con i nomi generici make, model, year, engine. */
export function compatibilityBody(r: RichiestaAllinea, annoCorrente = new Date().getFullYear()): object {
  return rinominaCompat(veicoliEbay(r.compatibilita, annoCorrente), NOMI_BASE);
}

/** Lo stesso corpo con i nomi delle proprietà di eBay Italia (da getCompatibilityProperties). */
export function rinominaCompat(veicoli: VeicoloEbay[], nomi: NomiCompat): { compatibleProducts: { compatibilityProperties: { name: string; value: string }[] }[] } {
  return {
    compatibleProducts: veicoli.map((v) => ({
      compatibilityProperties: [
        { name: nomi.make, value: v.make },
        { name: nomi.model, value: v.model },
        ...(v.year ? [{ name: nomi.year, value: v.year }] : []),
        ...(v.engine && nomi.engine ? [{ name: nomi.engine, value: v.engine }] : []),
      ],
    })),
  };
}

/** Trova i nomi di marca, modello, anno e motore tra le proprietà della categoria. */
export function nomiCompat(props: { name?: string; localizedName?: string }[]): NomiCompat | undefined {
  const nomi = props.map((p) => p.name ?? "").filter(Boolean);
  const trova = (re: RegExp) => nomi.find((n) => re.test(n));
  const make = trova(/^make$/i) ?? trova(/make|marca/i);
  const model = trova(/^model$/i) ?? trova(/model/i);
  const year = trova(/^year$/i) ?? trova(/year|anno/i);
  const engine = trova(/^engine$/i) ?? trova(/engine|motore/i);
  if (!make || !model || !year) return undefined;
  return { make, model, year, ...(engine ? { engine } : {}) };
}

// ── Foto ──
/** Foto del gestionale → file sul server. Solo nomi generati dall'app: niente percorsi verso altre cartelle. */
export function fileFoto(url: string): { cartella: "foto" | "public"; nome: string; tipo: string } | undefined {
  const f = url.match(/^\/api\/foto\/([a-z0-9]+\.jpg)$/);
  if (f) return { cartella: "foto", nome: f[1], tipo: "image/jpeg" };
  const r = url.match(/^\/(renders\/[a-z0-9-]+\.(png|jpe?g|webp))$/);
  if (r) return { cartella: "public", nome: r[1], tipo: r[2] === "png" ? "image/png" : r[2] === "webp" ? "image/webp" : "image/jpeg" };
  return undefined;
}

// ── Offerte esistenti ──
export interface OffertaEbay { offerId?: string; status?: string; listing?: { listingId?: string; listingStatus?: string } }

/** PUBLISHED con annuncio finito (ENDED, EBAY_ENDED, INACTIVE) vale "chiusa": eBay l'ha chiuso, si può ripubblicare. */
export function statoDaOfferta(o: OffertaEbay | undefined): "pubblicata" | "chiusa" | "non pubblicata" {
  if (!o || o.status !== "PUBLISHED") return "non pubblicata";
  const s = o.listing?.listingStatus;
  return s === "ENDED" || s === "EBAY_ENDED" || s === "INACTIVE" ? "chiusa" : "pubblicata";
}

// ── Vendite (getOrders) ──
export interface OrdineEbay {
  orderId?: string;
  creationDate?: string;
  buyer?: { username?: string };
  cancelStatus?: { cancelState?: string };
  lineItems?: { lineItemId?: string; sku?: string; quantity?: number; lineItemCost?: { value?: string } }[];
}

/** Una vendita per ogni riga d'ordine con SKU degli annunci (A-…). Con più righe l'id è "ordine/riga", così resta unico. */
export function venditeDaOrdini(ordini: OrdineEbay[]): VenditaEbay[] {
  const out: VenditaEbay[] = [];
  for (const o of ordini) {
    if (!o.orderId || o.cancelStatus?.cancelState === "CANCELED") continue;
    const righe = (o.lineItems ?? []).filter((l) => typeof l.sku === "string" && l.sku.startsWith("A-") && (l.quantity ?? 0) > 0);
    for (const l of righe) {
      const q = l.quantity!;
      const totale = Number(l.lineItemCost?.value ?? 0);
      out.push({
        orderId: righe.length === 1 ? o.orderId : `${o.orderId}/${l.lineItemId}`,
        sku: l.sku!,
        quantita: q,
        prezzoUnitario: Math.round((totale / q) * 100) / 100,
        acquirente: o.buyer?.username ?? "Acquirente eBay",
        at: o.creationDate ?? new Date().toISOString(),
      });
    }
  }
  return out;
}

// ── Politiche di base (solo Sandbox: si creano se il conto di prova non ne ha) ──
const CATEGORIE_NORMALI = [{ name: "ALL_EXCLUDING_MOTORS_VEHICLES" }];
const euro = (v: number) => ({ value: v.toFixed(2), currency: VALUTA });

export const NOMI_POLITICHE: Record<SpedizioneEbay, string> = { corriere: "Corriere", voluminoso: "Corriere voluminoso", ritiro: "Solo ritiro in sede" };

/** Corpo di POST /sell/account/v1/fulfillment_policy. Costi di esempio: si cambiano poi su eBay. */
export function politicaSpedizioneBody(tipo: SpedizioneEbay): object {
  const comune = { name: NOMI_POLITICHE[tipo], marketplaceId: MARKETPLACE, categoryTypes: CATEGORIE_NORMALI, handlingTime: { value: 2, unit: "DAY" } };
  if (tipo === "ritiro") {
    // Da verificare in sandbox: per il "solo ritiro" eBay Italia vuole il servizio IT_Pickup con localPickup
    return { ...comune, localPickup: true, shippingOptions: [{ optionType: "DOMESTIC", costType: "FLAT_RATE", shippingServices: [{ shippingServiceCode: "IT_Pickup", shippingCost: euro(0), sortOrder: 1 }] }] };
  }
  const costo = tipo === "voluminoso" ? 45 : 12;
  return { ...comune, shippingOptions: [{ optionType: "DOMESTIC", costType: "FLAT_RATE", shippingServices: [{ shippingServiceCode: "IT_ExpressCourier", shippingCost: euro(costo), sortOrder: 1 }] }] };
}

/** Corpo di POST /sell/account/v1/payment_policy: i pagamenti li gestisce eBay. */
export function politicaPagamentoBody(): object {
  return { name: "Pagamento", marketplaceId: MARKETPLACE, categoryTypes: CATEGORIE_NORMALI, immediatePay: true };
}

/** Corpo di POST /sell/account/v1/return_policy: reso entro 14 giorni, spese a carico dell'acquirente. */
export function politicaResoBody(): object {
  return {
    name: "Reso 14 giorni", marketplaceId: MARKETPLACE, categoryTypes: CATEGORIE_NORMALI,
    returnsAccepted: true, returnPeriod: { value: 14, unit: "DAY" }, returnShippingCostPayer: "BUYER", refundMethod: "MONEY_BACK",
  };
}

/** Corpo di POST /sell/inventory/v1/location/{merchantLocationKey}. Indirizzo di esempio: si cambia poi su eBay. */
export function magazzinoBody(): object {
  return { name: "Sede", merchantLocationStatus: "ENABLED", locationTypes: ["WAREHOUSE"], location: { address: { city: "Roma", stateOrProvince: "RM", postalCode: "00118", country: "IT" } } };
}

// ── OAuth ──
/** Pagina di consenso di eBay. redirect_uri è il RuName (non un indirizzo): eBay rimanda all'indirizzo collegato al RuName. */
export function urlConsenso(base: string, appId: string, ruName: string, scope: string[], state: string): string {
  const q = [["client_id", appId], ["redirect_uri", ruName], ["response_type", "code"], ["scope", scope.join(" ")], ["state", state]];
  return `${base}?${q.map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&")}`;
}

// ── Errori ──
interface ErroreRest { errorId?: number; message?: string; longMessage?: string; parameters?: { name?: string; value?: string }[] }

const COSA: Record<string, string> = {
  riprova: "niente, il gestionale riprova da solo tra poco.",
  annuncio: "controlla l'annuncio nel gestionale e salvalo di nuovo.",
  politiche: "in Impostazioni → Collegamenti controlla le politiche eBay scelte.",
  ricollega: "in Impostazioni → Collegamenti tocca «Collega account eBay».",
};

const ERRORI: Record<number, [string, keyof typeof COSA]> = {
  25001: ["eBay ha un problema temporaneo.", "riprova"],
  25025: ["eBay stava già aggiornando questo annuncio.", "riprova"],
  25003: ["eBay non accetta il prezzo.", "annuncio"],
  25004: ["eBay non accetta la quantità.", "annuncio"],
  25005: ["eBay non accetta la categoria.", "annuncio"],
  25007: ["eBay non accetta la politica di spedizione.", "politiche"],
  25008: ["eBay non accetta la politica di pagamento.", "politiche"],
  25009: ["eBay non accetta la politica di reso.", "politiche"],
  25035: ["Una politica scelta non esiste più su eBay.", "politiche"],
  25036: ["Una politica scelta è del tipo sbagliato.", "politiche"],
  25123: ["Per i ricambi eBay chiede un reso di almeno 30 giorni con spedizione a carico del venditore.", "politiche"],
  25012: ["eBay non trova il magazzino.", "politiche"],
  25900: ["eBay non trova il magazzino.", "politiche"],
  25901: ["Manca il magazzino.", "politiche"],
  25014: ["eBay non accetta le foto.", "annuncio"],
  25015: ["eBay non accetta le foto.", "annuncio"],
  25086: ["eBay non accetta le foto.", "annuncio"],
  25501: ["eBay non accetta le foto.", "annuncio"],
  25021: ["eBay non accetta la condizione per questa categoria.", "annuncio"],
  25030: ["eBay non accetta la condizione per questa categoria.", "annuncio"],
  25023: ["eBay non accetta i veicoli compatibili.", "annuncio"],
  25739: ["Troppi veicoli compatibili per eBay.", "annuncio"],
  25029: ["Manca un dato obbligatorio per questa categoria.", "annuncio"],
  25801: ["Manca un dato obbligatorio.", "annuncio"],
  25002: ["eBay ha rifiutato un dato dell'annuncio.", "annuncio"],
  25016: ["eBay ha rifiutato un dato dell'annuncio.", "annuncio"],
  25022: ["eBay ha rifiutato una caratteristica.", "annuncio"],
  25110: ["Dati del produttore (GPSR) incompleti.", "annuncio"],
  25111: ["Dati del produttore (GPSR) incompleti.", "annuncio"],
  25115: ["Il produttore (GPSR) deve avere sede nell'Unione europea.", "annuncio"],
  25118: ["Manca un contatto del produttore (GPSR).", "annuncio"],
  25026: ["Il conto eBay ha raggiunto i limiti di vendita: chiedi a eBay di alzarli.", "annuncio"],
  25096: ["eBay ha sospeso l'annuncio: controlla la posta del conto eBay.", "annuncio"],
  25097: ["eBay ha sospeso l'annuncio: controlla la posta del conto eBay.", "annuncio"],
  25713: ["eBay non trova l'offerta.", "riprova"],
  25710: ["eBay non trova l'annuncio.", "riprova"],
};

// Solo nomi di campo semplici (es. "Numero ricambio produttore"): niente codici, token o HTML nel messaggio
const nomeSicuro = (v?: string) => (v && /^[\p{L}\p{N} .,'()/-]{1,60}$/u.test(v) ? v : undefined);

/** Risposta di errore di eBay → frase in italiano con "Cosa fare"; il testo grezzo resta in `log` (solo per il server). */
export function traduciErrore(status: number, corpo: unknown): { messaggio: string; log: string } {
  const c = (typeof corpo === "object" && corpo !== null ? corpo : {}) as { errors?: ErroreRest[]; error?: string; error_description?: string };
  const errori = Array.isArray(c.errors) ? c.errors : [];
  const log = `HTTP ${status} ${errori.length ? errori.map((e) => `[${e.errorId}] ${e.message ?? ""} ${e.longMessage ?? ""}`).join(" | ") : JSON.stringify(corpo).slice(0, 500)}`;
  const frase = (cosa: string, extra: keyof typeof COSA) => ({ messaggio: `${cosa} Cosa fare: ${COSA[extra]}`, log });
  if (status === 401 || c.error === "invalid_grant" || c.error === "invalid_token") return frase("eBay non riconosce più il collegamento con il conto.", "ricollega");
  if (status === 403) return frase("eBay non permette questa operazione al conto collegato.", "ricollega");
  if (status === 429) return frase("Troppe richieste a eBay in poco tempo.", "riprova");
  const e = errori[0];
  if (e?.errorId && ERRORI[e.errorId]) {
    const [cosa, fare] = ERRORI[e.errorId];
    const campo = nomeSicuro(e.parameters?.find((p) => nomeSicuro(p.value))?.value);
    return frase(campo && fare === "annuncio" ? `${cosa.replace(/\.$/, "")}: «${campo}».` : cosa, fare);
  }
  if (status >= 500 || status === 0) return frase("eBay non risponde o ha un problema temporaneo.", "riprova");
  return {
    messaggio: `eBay ha rifiutato la richiesta${e?.errorId ? ` (codice ${e.errorId})` : ""}. Cosa fare: ${COSA.annuncio} Se si ripete, chiedi assistenza indicando il codice.`,
    log,
  };
}
