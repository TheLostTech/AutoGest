import { PART_TYPES } from "./catalog";
import type { PartType } from "./types";

// Ricerca tollerante, per chi scrive dal telefono in piazzale:
// maiuscole, accenti e doppie non contano ("bobbina" trova "Bobina"), le parole vanno in qualsiasi ordine,
// e singolare e plurale si equivalgono ("freni" trova "Disco freno").
const base = (s: string) =>
  s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/([a-z])\1+/g, "$1"); // solo le lettere: le cifre doppie dei codici restano

const testo = (s: string) => base(s).replace(/[^a-z0-9]+/g, " ").trim();
const compatto = (s: string) => base(s).replace(/[^a-z0-9]/g, "");

// La vocale finale delle parole si toglie: "freni" e "freno" diventano "fren"
const parole = (q: string) =>
  testo(q)
    .split(" ")
    .filter(Boolean)
    .map((w) => (w.length >= 4 && !/\d/.test(w) && /[aeiou]$/.test(w) ? w.slice(0, -1) : w));

type Campo = string | undefined | null;

// Vero se ogni parola cercata compare in uno dei campi; per i codici vale anche il testo senza spazi e trattini (EK482 = EK 482)
export function corrisponde(q: string, campi: Campo[]): boolean {
  const ws = parole(q);
  if (ws.length === 0) return true;
  const pieni = campi.filter((c): c is string => !!c);
  const t = pieni.map(testo).join(" ");
  if (ws.every((w) => t.includes(w))) return true;
  const c = compatto(q);
  return c.length >= 2 && pieni.some((x) => compatto(x).includes(c));
}

// Tipologie che corrispondono, cercando nel nome e nella categoria.
// Prima quelle il cui nome comincia con la prima parola, poi quelle che la contengono nel nome, poi quelle trovate per categoria.
export function cercaTipologie(q: string, tipi: PartType[] = PART_TYPES): PartType[] {
  const ws = parole(q);
  if (ws.length === 0) return [];
  const peso = (t: PartType) => {
    const n = testo(t.name);
    if (n.startsWith(ws[0])) return 0;
    if (ws.every((w) => n.includes(w))) return 1;
    return 2;
  };
  return tipi
    .filter((t) => corrisponde(q, [t.name, t.category]))
    .map((t) => [peso(t), t] as const)
    .sort((a, b) => a[0] - b[0] || a[1].name.localeCompare(b[1].name, "it"))
    .map(([, t]) => t);
}

// Categorie il cui nome corrisponde ("freni", "motore")
export function cercaCategorie(q: string, categorie: string[]): string[] {
  return parole(q).length === 0 ? [] : categorie.filter((c) => corrisponde(q, [c]));
}
