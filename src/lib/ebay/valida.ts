// Controllo a mano del corpo di POST /api/ebay/allinea: solo i campi del contratto, con i tipi giusti.
import type { RichiestaAllinea } from "./contratto";

type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => typeof v === "object" && v !== null && !Array.isArray(v);
const str = (v: unknown): v is string => typeof v === "string";
const num = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const soloCampi = (o: Obj, ammessi: string[]) => Object.keys(o).every((k) => ammessi.includes(k));
const strOpz = (v: unknown) => v === undefined || str(v);

function gpsrValido(g: unknown): boolean {
  if (!isObj(g)) return false;
  if (g.tipo === "esente" || g.tipo === "da confermare") return soloCampi(g, ["tipo"]);
  if (g.tipo !== "produttore" || !soloCampi(g, ["tipo", "produttore"]) || !isObj(g.produttore)) return false;
  const p = g.produttore;
  return soloCampi(p, ["ragioneSociale", "indirizzo", "citta", "cap", "paese", "email", "sito"])
    && ["ragioneSociale", "indirizzo", "citta", "cap", "paese"].every((k) => str(p[k])) && strOpz(p.email) && strOpz(p.sito);
}

function compatValida(c: unknown): boolean {
  return isObj(c) && soloCampi(c, ["marca", "modello", "anno", "anni", "motore"])
    && str(c.marca) && str(c.modello) && (c.anno === undefined || num(c.anno)) && strOpz(c.anni) && strOpz(c.motore);
}

export function validaRichiesta(b: unknown): RichiestaAllinea | undefined {
  if (!isObj(b)) return undefined;
  const campi = ["sku", "attivo", "quantita", "prezzo", "titolo", "descrizione", "categoriaQuery", "categoriaId",
    "condizione", "caratteristiche", "foto", "compatibilita", "spedizione", "gpsr"];
  if (!soloCampi(b, campi)) return undefined;
  const ok =
    str(b.sku) && b.sku !== "" && typeof b.attivo === "boolean"
    && num(b.quantita) && Number.isInteger(b.quantita) && b.quantita >= 0
    && num(b.prezzo) && b.prezzo > 0
    && str(b.titolo) && str(b.descrizione) && str(b.categoriaQuery) && strOpz(b.categoriaId)
    && (b.condizione === "A" || b.condizione === "B" || b.condizione === "C" || b.condizione === "D")
    && isObj(b.caratteristiche) && Object.values(b.caratteristiche).every(str)
    && Array.isArray(b.foto) && b.foto.every(str)
    && Array.isArray(b.compatibilita) && b.compatibilita.every(compatValida)
    && (b.spedizione === "corriere" || b.spedizione === "voluminoso" || b.spedizione === "ritiro")
    && gpsrValido(b.gpsr);
  return ok ? (b as unknown as RichiestaAllinea) : undefined;
}
