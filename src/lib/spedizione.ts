import type { Part } from "./types";

// I tipi spedibili di serie lo sono sempre; quelli ingombranti solo se alla creazione si è scelto di spedirli.
export function isShippable(p: Pick<Part, "spedibile">, typeShippable: boolean): boolean {
  return typeShippable || p.spedibile === true;
}

// La domanda "Si può spedire?" si fa solo per i tipi non spedibili di serie.
export function asksShipping(typeShippable: boolean): boolean {
  return !typeShippable;
}
