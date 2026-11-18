// Utenti dell'azienda demo, creati una sola volta nella prima preparazione dell'azienda (avvio.ts).
// Qui ci sono solo nomi, ruoli e modo d'accesso: password e PIN si generano a caso al primo avvio e si scrivono
// in DATI_DIR/credenziali-demo.json (permessi 0600). Mai nel codice, nei log, nell'interfaccia o nei documenti.
import type { Role } from "../types.ts";

export type UtenteDemo = { nome: string; ruoli: Role[]; conPin?: boolean; email?: string };

export const DOMINIO_DEMO = "demo.autodemolizione.test";

export const UTENTI_DEMO: UtenteDemo[] = [
  { nome: "Giulia", ruoli: ["accettazione"], conPin: true },
  { nome: "Marco", ruoli: ["smontatore"], conPin: true },
  { nome: "Luca", ruoli: ["smontatore", "accettazione"], conPin: true },
  { nome: "Paolo", ruoli: ["magazziniere"], conPin: true },
  { nome: "Sara", ruoli: ["responsabile"], email: `sara@${DOMINIO_DEMO}`, conPin: true },
  { nome: "Anna", ruoli: ["vendite"], conPin: true },
  { nome: "Laura", ruoli: ["consulente"], email: `laura@${DOMINIO_DEMO}` },
];
