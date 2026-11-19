// Moduli a pagamento: il Magazzino è la base, Accettazione, Ambiente e Vendite si aggiungono.
// Qui si decide in un punto solo a quale modulo appartiene ogni pagina. Modulo puro: niente import di codice.
import type { Order, SalesDoc } from "./types";

export type Modulo = "magazzino" | "accettazione" | "ambiente" | "vendite";

export interface StatoModulo {
  id: Modulo;
  attivo: boolean;
  cambiatoAt?: string;
  cambiatoDa?: string;
}

export const ORDINE_MODULI: Modulo[] = ["magazzino", "accettazione", "ambiente", "vendite"];

export const MODULI: Record<Modulo, { nome: string; frase: string; punti: string[] }> = {
  magazzino: {
    nome: "Magazzino",
    frase: "Dal veicolo al ricambio venduto online: smontaggio, catalogo, scaffali e pubblicazione.",
    punti: [
      "Scheda veicolo con lettura della targa e conferma del telaio",
      "Smontaggio dal telefono, etichette, ubicazioni e inventario",
      "Pubblicazione su eBay e negozio online con un tocco",
      "Ordini online con scontrino, fattura e resi",
    ],
  },
  accettazione: {
    nome: "Accettazione",
    frase: "La pratica di demolizione dall'ingresso alla radiazione dal PRA, con i collegamenti ufficiali.",
    punti: [
      "Chi consegna e documenti ritirati",
      "Visura PRA e controllo del fermo amministrativo",
      "Presa in carico nel RVFU e certificato di rottamazione",
      "Radiazione e fascicolo del veicolo",
    ],
  },
  ambiente: {
    nome: "Ambiente",
    frase: "Il registro rifiuti si scrive da solo dalla bonifica e dalle uscite, e si trasmette al RENTRI.",
    punti: [
      "Bonifica con materiali tolti e pesi",
      "Registro di carico e scarico e periodo RENTRI",
      "Formulari e soggetti di trasporto e destino",
      "Limiti dell'autorizzazione sempre sotto controllo",
    ],
  },
  vendite: {
    nome: "Vendite",
    frase: "Il banco in sede: vendita, preventivi, documenti fiscali e listini per tipo di cliente.",
    punti: [
      "Vendita al banco con scontrino o fattura",
      "Preventivi da richiamare e convertire",
      "Resi e note di credito",
      "Listini e clienti, con l'elenco completo dei documenti",
    ],
  },
};

// Prefissi per segmenti; "*" vale qualsiasi segmento. Tutto il resto è Magazzino (la base).
const PERCORSI: [string, Modulo][] = [
  ["/certificato", "accettazione"],
  ["/ambiente", "ambiente"],
  ["/veicoli/*/bonifica", "ambiente"],
  ["/vendite", "vendite"],
  ["/listini", "vendite"],
];

const segmenti = (p: string) => p.split("/").filter(Boolean);

/** Modulo a cui appartiene un percorso: vince il prefisso più lungo, il resto è Magazzino */
export function moduloDi(percorso: string): Modulo {
  const s = segmenti(percorso.split(/[?#]/)[0]);
  let best: { len: number; m: Modulo } | undefined;
  for (const [prefisso, m] of PERCORSI) {
    const p = segmenti(prefisso);
    if (p.length > s.length || !p.every((x, i) => x === "*" || x === s[i])) continue;
    if (!best || p.length > best.len) best = { len: p.length, m };
  }
  return best?.m ?? "magazzino";
}

/**
 * Modulo di un documento di vendita: quelli degli ordini online (scontrino, fattura, nota di credito del reso)
 * sono del Magazzino; preventivi, documenti del banco e documenti senza ordine sono di Vendite.
 */
export function moduloDoc(d: Pick<SalesDoc, "type" | "orderId">, orders: Pick<Order, "id" | "channel">[]): Modulo {
  if (d.type === "preventivo" || !d.orderId) return "vendite";
  const o = orders.find((x) => x.id === d.orderId);
  return o && o.channel !== "banco" ? "magazzino" : "vendite";
}

/**
 * Coda "Oggi" senza le voci dei moduli spenti. Le voci della pratica sono dell'Accettazione anche se portano
 * alla scheda veicolo; la bonifica senza Ambiente resta (scadenza di legge) e porta alla scheda, dove si segna.
 */
export function filtraAgenda<T extends { kind: string; href: string }>(items: T[], moduli: Set<Modulo>): T[] {
  return items.flatMap((it) => {
    const m: Modulo = it.kind === "pratica" ? "accettazione" : moduloDi(it.href);
    if (moduli.has(m)) return [it];
    const bonifica = it.href.match(/^\/veicoli\/([^/?#]+)\/bonifica/);
    return bonifica ? [{ ...it, href: `/veicoli/${bonifica[1]}#bonifica` }] : [];
  });
}

/** Dove si gestisce un ordine: quelli online nel Magazzino, quelli del banco in Vendite */
export const hrefOrdine = (o: Pick<Order, "channel">) => (o.channel === "banco" ? "/vendite" : "/ordini");

/** "Vendi" dalla scansione: un pezzo di un ordine si preleva sempre; la vendita al banco solo con Vendite */
export const azioneVendi = (haOrdine: boolean, moduli: Set<Modulo>): "ordine" | "banco" | "bloccato" =>
  haOrdine ? "ordine" : moduli.has("vendite") ? "banco" : "bloccato";

/**
 * Ordine al banco ancora in attesa che tiene riservato il pezzo quando il modulo Vendite è spento:
 * dalla scheda ricambio (base) si può annullare per liberare il pezzo.
 */
export function ordineBancoDaLiberare<O extends Pick<Order, "id" | "channel" | "status" | "partIds">>(partId: string, orders: O[], moduli: Set<Modulo>): O | undefined {
  if (moduli.has("vendite")) return undefined;
  return orders.find((o) => o.channel === "banco" && o.status === "in attesa di pagamento" && o.partIds.includes(partId));
}

/** Moduli attivi: senza stato salvato (o modulo non elencato) è attivo; il Magazzino sempre */
export function moduliAttivi(stato: StatoModulo[] | undefined): Set<Modulo> {
  const spenti = new Set((stato ?? []).filter((x) => !x.attivo).map((x) => x.id));
  return new Set(ORDINE_MODULI.filter((m) => m === "magazzino" || !spenti.has(m)));
}

export const attivo = (moduli: Set<Modulo>, m: Modulo) => moduli.has(m);

/**
 * Schede della barra inferiore: restano quelle aperte; al posto di una chiusa entra la prima di `ricambi`
 * aperta e non già presente, altrimenti la scheda sparisce. Chi lavora sul campo non ha lucchetti sotto il pollice.
 */
export function tabsAttive<T extends { area?: string; href?: string }>(tabs: T[], ricambi: T[], aperta: (t: T) => boolean): T[] {
  const chiave = (t: T) => t.area ?? t.href ?? "";
  const presenti = new Set(tabs.filter(aperta).map(chiave));
  const out: T[] = [];
  for (const t of tabs) {
    if (aperta(t)) {
      out.push(t);
      continue;
    }
    const sost = ricambi.find((r) => aperta(r) && !presenti.has(chiave(r)));
    if (sost) {
      presenti.add(chiave(sost));
      out.push(sost);
    }
  }
  return out;
}

// Numero a cui arrivano le richieste d'attivazione: da sostituire con quello vero di Alessandro
export const WHATSAPP_ATTIVAZIONE = "390000000000";

export function linkAttivazione(azienda: string, m: Modulo): string {
  const testo = `Ciao, sono ${azienda} su AutoLost: vorrei attivare il modulo ${MODULI[m].nome}.`;
  return `https://wa.me/${WHATSAPP_ATTIVAZIONE}?text=${encodeURIComponent(testo)}`;
}

/** Moduli attivi letti dall'archivio sul server (state.json); forma non valida = tutti attivi */
export function moduliDaArchivio(raw: unknown): Set<Modulo> {
  const lista = (raw as { state?: { moduli?: unknown } } | null)?.state?.moduli;
  if (!Array.isArray(lista)) return moduliAttivi(undefined);
  const validi = lista.every((x) => x && typeof x === "object" && ORDINE_MODULI.includes((x as StatoModulo).id) && typeof (x as StatoModulo).attivo === "boolean");
  return moduliAttivi(validi ? (lista as StatoModulo[]) : undefined);
}
