// Controllo a mano del corpo di POST /api/ebay/allinea: solo i campi del contratto, con i tipi giusti
// e con dimensioni massime (eBay accetta al più 24 foto; SKU fino a 50 caratteri).
import type { RichiestaAllinea } from "./contratto";

type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => typeof v === "object" && v !== null && !Array.isArray(v);
const str = (v: unknown, max = CORTO): v is string => typeof v === "string" && v.length <= max;
const num = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const soloCampi = (o: Obj, ammessi: string[]) => Object.keys(o).every((k) => ammessi.includes(k));
const strOpz = (v: unknown, max = CORTO) => v === undefined || str(v, max);

const CORTO = 200;
export const LIMITI = {
  sku: 50,
  titolo: 200, // il titolo dell'app è già entro 80; il ponte lo taglia comunque a 80
  descrizione: 50_000,
  foto: 24,
  url: 500,
  caratteristiche: 40,
  compatibilita: 200,
} as const;

function gpsrValido(g: unknown): boolean {
  if (!isObj(g)) return false;
  if (g.tipo === "esente" || g.tipo === "da confermare") return soloCampi(g, ["tipo"]);
  if (g.tipo !== "produttore" || !soloCampi(g, ["tipo", "produttore"]) || !isObj(g.produttore)) return false;
  const p = g.produttore;
  return soloCampi(p, ["ragioneSociale", "indirizzo", "citta", "cap", "paese", "email", "sito"])
    && ["ragioneSociale", "indirizzo", "citta", "cap", "paese"].every((k) => str(p[k])) && strOpz(p.email) && strOpz(p.sito, LIMITI.url);
}

function compatValida(c: unknown): boolean {
  return isObj(c) && soloCampi(c, ["marca", "modello", "anno", "anni", "motore"])
    && str(c.marca) && str(c.modello) && (c.anno === undefined || num(c.anno)) && strOpz(c.anni) && strOpz(c.motore);
}

function caratteristicheValide(c: unknown): boolean {
  if (!isObj(c)) return false;
  const voci = Object.entries(c);
  return voci.length <= LIMITI.caratteristiche && voci.every(([k, v]) => k.length <= CORTO && str(v));
}

export function validaRichiesta(b: unknown): RichiestaAllinea | undefined {
  if (!isObj(b)) return undefined;
  const campi = ["sku", "attivo", "quantita", "prezzo", "titolo", "descrizione", "categoriaQuery", "categoriaId",
    "condizione", "caratteristiche", "foto", "compatibilita", "spedizione", "gpsr"];
  if (!soloCampi(b, campi)) return undefined;
  const ok =
    str(b.sku, LIMITI.sku) && b.sku !== "" && typeof b.attivo === "boolean"
    && num(b.quantita) && Number.isInteger(b.quantita) && b.quantita >= 0 && b.quantita <= 10_000
    && num(b.prezzo) && b.prezzo > 0 && b.prezzo < 1_000_000
    && str(b.titolo, LIMITI.titolo) && str(b.descrizione, LIMITI.descrizione) && str(b.categoriaQuery) && strOpz(b.categoriaId, 20)
    && (b.condizione === "A" || b.condizione === "B" || b.condizione === "C" || b.condizione === "D")
    && caratteristicheValide(b.caratteristiche)
    && Array.isArray(b.foto) && b.foto.length <= LIMITI.foto && b.foto.every((f) => str(f, LIMITI.url))
    && Array.isArray(b.compatibilita) && b.compatibilita.length <= LIMITI.compatibilita && b.compatibilita.every(compatValida)
    && (b.spedizione === "corriere" || b.spedizione === "voluminoso" || b.spedizione === "ritiro")
    && gpsrValido(b.gpsr);
  return ok ? (b as unknown as RichiestaAllinea) : undefined;
}
