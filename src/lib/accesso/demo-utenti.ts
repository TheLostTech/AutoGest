// Utenti dell'azienda demo, creati al primo avvio (avvio.ts). Sono dati di prova: valgono solo per la demo.
// Questi valori non vanno mai mostrati nell'interfaccia, scritti nei log o ripetuti nei documenti.
import type { Role } from "../types.ts";

export type UtenteDemo = { nome: string; ruoli: Role[]; pin?: string; email?: string; password?: string };

export const DOMINIO_DEMO = "demo.autodemolizione.test";

export const UTENTI_DEMO: UtenteDemo[] = [
  { nome: "Giulia", ruoli: ["accettazione"], pin: "4821" },
  { nome: "Marco", ruoli: ["smontatore"], pin: "7305" },
  { nome: "Luca", ruoli: ["smontatore", "accettazione"], pin: "1936" },
  { nome: "Paolo", ruoli: ["magazziniere"], pin: "5648" },
  { nome: "Sara", ruoli: ["responsabile"], email: `sara@${DOMINIO_DEMO}`, password: "Demo-Sara-2026", pin: "2579" },
  { nome: "Anna", ruoli: ["vendite"], pin: "8412" },
  { nome: "Laura", ruoli: ["consulente"], email: `laura@${DOMINIO_DEMO}`, password: "Demo-Laura-2026" },
];
