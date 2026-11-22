import type { Role } from "../types.ts";

// I sei ruoli dell'azienda, nell'ordine in cui compaiono nelle liste.
export const RUOLI: readonly Role[] = ["accettazione", "smontatore", "magazziniere", "responsabile", "vendite", "consulente"];

export const RUOLO_LABEL: Record<Role, string> = {
  accettazione: "Accettazione",
  smontatore: "Smontatore",
  magazziniere: "Magazziniere",
  responsabile: "Responsabile",
  vendite: "Vendite",
  consulente: "Consulente ambientale",
};

// "vendite, accettazione,boh" -> ["accettazione", "vendite"]: scarta i valori sconosciuti e i doppioni.
export function ruoliDaStringa(s: string | null | undefined): Role[] {
  if (!s) return [];
  const voci = new Set(s.split(",").map((v) => v.trim()));
  return RUOLI.filter((r) => voci.has(r));
}

export function ruoliAStringa(r: Role[]): string {
  return ruoliDaStringa(r.join(",")).join(",");
}
