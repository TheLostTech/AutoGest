// Pratica di demolizione: documenti, visura al PRA, presa in carico, radiazione.
// Modelli, documenti richiesti e termini sono DIMOSTRATIVI: vanno verificati sulla normativa
// e sulle procedure ufficiali (portale ministeriale, Registro Unico Telematico, ACI) prima dell'uso reale.
import type { ConferenteTipo, Vehicle } from "./types";

export const CONFERENTI: { value: ConferenteTipo; label: string }[] = [
  { value: "privato", label: "Privato" },
  { value: "concessionaria", label: "Concessionaria" },
  { value: "assicurazione", label: "Compagnia assicurativa" },
  { value: "ente", label: "Ente o forze dell'ordine" },
];

export const DOCUMENTI: { key: string; label: string; for?: ConferenteTipo[] }[] = [
  { key: "libretto", label: "Carta di circolazione" },
  { key: "proprieta", label: "Certificato di proprietà" },
  { key: "identita", label: "Documento d'identità di chi conferisce" },
  { key: "targa-ant", label: "Targa anteriore" },
  { key: "targa-post", label: "Targa posteriore" },
  { key: "delega", label: "Delega del proprietario", for: ["concessionaria", "assicurazione"] },
];

export const docsFor = (v: Vehicle) => DOCUMENTI.filter((d) => !d.for || (v.conferente && d.for.includes(v.conferente.tipo)));

export type StepState = "fatto" | "attuale" | "bloccato" | "dopo";

export function praticaSteps(v: Vehicle) {
  const docs = docsFor(v);
  const docsOk = !!v.conferente && docs.every((d) => v.documenti?.includes(d.key));
  const visuraOk = !!v.visura && !v.visura.fermo;
  const preso = !!v.presaInCarico;
  const radiato = v.radiazione?.stato === "completata";
  const st = (done: boolean, ready: boolean, blocked = false): StepState => (done ? "fatto" : blocked ? "bloccato" : ready ? "attuale" : "dopo");
  return {
    docs: st(docsOk, true),
    visura: st(visuraOk, docsOk, !!v.visura?.fermo),
    presa: st(preso, docsOk && visuraOk),
    radiazione: st(radiato, preso),
    docsMissing: docs.filter((d) => !v.documenti?.includes(d.key)),
  };
}

// Visura PRA simulata: la targa demo FA377TP risulta con fermo amministrativo
export async function simulateVisura(v: Vehicle) {
  await new Promise((r) => setTimeout(r, 900));
  return { at: new Date().toISOString(), fermo: v.plate === "FA377TP", intestatario: v.conferente?.nome ?? "Intestatario da documenti" };
}

export const nextCertNumber = (vehicles: Vehicle[]) => {
  const max = Math.max(4800, ...vehicles.map((v) => Number(v.dossier.number.split("-").pop()) || 0));
  return `CR-2026-${String(max + 1).padStart(6, "0")}`;
};
