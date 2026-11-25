// Senza il modulo Accettazione la pratica si fa altrove: per il registro rifiuti servono comunque chi ha
// consegnato il veicolo (produttore) e il certificato di rottamazione. Modulo puro.

import type { Bonifica, Vehicle, WasteMove } from "./types";

/** La bonifica completa si registra se manca o se era stata solo segnata senza il modulo Ambiente */
export const bonificaRegistrabile = (b?: Bonifica) => !b || !!b.semplice;

/**
 * Stato dei dati per il registro: completo quando il carico del veicolo è numerato; con i dati scritti ma
 * il carico ancora in bozza manca la pesata (o un altro dato del registro).
 */
export function statoDatiRegistro(v: Vehicle, moves: WasteMove[]): "completo" | "manca-pesata" | "da-compilare" {
  const carico = moves.find((m) => m.origin === v.id && m.causale === "T*");
  if (carico?.numero !== undefined) return "completo";
  const scritti = !!(v.conferente?.nome && v.conferente.cf && v.dossier.number && v.presaInCarico);
  return carico && scritti ? "manca-pesata" : "da-compilare";
}

export interface DatiRegistro {
  nome: string;
  cf: string; // codice fiscale o partita IVA
  numero: string; // numero del certificato di rottamazione
  data: string; // AAAA-MM-GG
}

export const normCf = (cf: string) => cf.replace(/\s/g, "").toUpperCase();

export function datiRegistroErrori(d: DatiRegistro, ora = new Date()): string[] {
  const out: string[] = [];
  if (!d.nome.trim()) out.push("Scrivi chi ha consegnato il veicolo");
  if (!/^(IT)?\d{11}$|^[A-Z0-9]{16}$/.test(normCf(d.cf))) out.push("Codice fiscale (16 caratteri) o partita IVA (11 cifre) non valido");
  if (!d.numero.trim()) out.push("Scrivi il numero del certificato di rottamazione");
  const t = /^\d{4}-\d{2}-\d{2}$/.test(d.data) ? new Date(`${d.data}T00:00:00`).getTime() : NaN;
  if (!Number.isFinite(t) || t > ora.getTime()) out.push("Data del certificato non valida");
  return out;
}
