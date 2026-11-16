import type { DocType } from "./types";

export const DOC_LABEL: Record<DocType, string> = {
  preventivo: "Preventivo",
  "documento commerciale": "Scontrino",
  fattura: "Fattura",
  "nota di credito": "Nota di credito",
};

// Prezzi IVA inclusa: scorporo dimostrativo al 22%, regime IVA da validare con il commercialista
export const VAT = 0.22;
export const splitVat = (gross: number) => {
  const net = Math.round((gross / (1 + VAT)) * 100) / 100;
  return { net, vat: Math.round((gross - net) * 100) / 100 };
};
