// Pratica di demolizione secondo il flusso RVFU (Registro unico telematico dei veicoli fuori uso,
// DPR 177/2022, obbligatorio dal 7 giugno 2024): presa in carico, Certificato di Rottamazione
// Digitale (CRD), fascicolo digitale, radiazione dal PRA entro 30 giorni dalla consegna.
// Fonti e date in docs/INTEGRAZIONI.md. Il collegamento al RVFU è SIMULATO nel prototipo.
import type { ConferenteTipo, Vehicle } from "./types";

export const CONFERENTI: { value: ConferenteTipo; label: string }[] = [
  { value: "privato", label: "Privato" },
  { value: "concessionaria", label: "Concessionaria" },
  { value: "assicurazione", label: "Compagnia assicurativa" },
  { value: "ente", label: "Ente o forze dell'ordine" },
];

// Documenti per la radiazione (fonte: ACI, "Demolizione di un veicolo", agg. 06/05/2026)
export const DOCUMENTI: { key: string; label: string; for?: ConferenteTipo[] }[] = [
  { key: "targa-ant", label: "Targa anteriore (o denuncia di smarrimento/furto)" },
  { key: "targa-post", label: "Targa posteriore (o denuncia di smarrimento/furto)" },
  { key: "libretto", label: "Carta di circolazione o Documento Unico" },
  { key: "proprieta", label: "Certificato di proprietà o foglio complementare" },
  { key: "identita", label: "Documento d'identità di chi consegna" },
  { key: "delega", label: "Delega del proprietario", for: ["concessionaria", "assicurazione"] },
];

export const docsFor = (v: Vehicle) => DOCUMENTI.filter((d) => !d.for || (v.conferente && d.for.includes(v.conferente.tipo)));

// Con fermo amministrativo la radiazione per demolizione è ammessa con un'attestazione di inutilizzabilità
// (art. 5, c. 8-bis/8-ter, D.Lgs. 209/2003 come modificato dalla L. 14/2026; lettera circolare ACI 9626 del 19/02/2026)
export const ATTESTAZIONE = { key: "inutilizzabilita", label: "Attestazione di inutilizzabilità del veicolo (fermo presente)" };

// Radiazione per demolizione (fonte: ACI, agg. 06/05/2026). I diritti MIT nel flusso RVFU sono da confermare.
export const RADIAZIONE = {
  terminiGiorni: 30, // dalla consegna del veicolo (ACI)
  codicePratica: "C05332", // DU, radiazione per demolizione (C05333 se c'è un provvedimento della PA: esente)
  fascicolo: "Fascicolo digitale da pagare e inoltrare entro le 16:00 del secondo giorno lavorativo",
  costi: [
    { voce: "Imposta di bollo", euro: 32 },
    { voce: "Emolumenti ACI (PRA)", euro: 13.5 },
  ],
  nota: "Diritti Motorizzazione 10,20 € indicati da ACI ma assenti nella circolare RVFU: da confermare",
  conservazioneGiorni: 120, // targhe e documenti si distruggono non prima di 120 giorni dal CRD
};

export type StepState = "fatto" | "attuale" | "dopo";

// Il RVFU identifica il veicolo da targa e telaio: senza telaio verificato non si prende in carico
export const identOk = (v: Vehicle) => /^[A-HJ-NPR-Z0-9]{17}$/.test(v.vin) && v.verification === "verificato";

export function praticaSteps(v: Vehicle) {
  const docs = docsFor(v);
  const docsOk = !!v.conferente?.cf && docs.every((d) => v.documenti?.includes(d.key));
  const preso = !!v.presaInCarico;
  const st = (done: boolean, ready: boolean): StepState => (done ? "fatto" : ready ? "attuale" : "dopo");
  return {
    docs: st(docsOk || preso, true),
    // Dal 20/02/2026 (L. 14/2026) il fermo amministrativo non impedisce la radiazione per demolizione:
    // si registra e si avvisa il proprietario, ma non blocca la presa in carico.
    visura: st(!!v.visura, docsOk || preso),
    presa: st(preso, docsOk && !!v.visura && identOk(v) && (!v.visura.fermo || !!v.documenti?.includes(ATTESTAZIONE.key))),
    radiazione: st(v.radiazione?.stato === "completata", preso),
    docsMissing: docs.filter((d) => !v.documenti?.includes(d.key)),
  };
}

// Visura PRA simulata (nel reale: ACI Visurenet o intermediario via API). La targa demo FA377TP ha un fermo.
export async function simulateVisura(v: Vehicle) {
  await new Promise((r) => setTimeout(r, 900));
  return { at: new Date().toISOString(), fermo: v.plate === "FA377TP", intestatario: v.conferente?.nome ?? "Intestatario da documenti" };
}

export const nextCertNumber = (vehicles: Vehicle[]) => {
  const max = Math.max(4800, ...vehicles.map((v) => Number(v.dossier.number.split("-").pop()) || 0));
  return `CR-2026-${String(max + 1).padStart(6, "0")}`;
};

// Formato base: codice fiscale di persona (16) o partita IVA (11 cifre)
export const cfOk = (x: string) => /^[A-Z0-9]{16}$/i.test(x.trim()) || /^\d{11}$/.test(x.trim());
