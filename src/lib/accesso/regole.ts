import type { Role } from "../types.ts";
import { RUOLI, ruoliDaStringa } from "./ruoli.ts";

// Sessione da PIN: scade dopo 5 minuti senza richieste e comunque dopo 10 ore dall'inizio.
export const PIN_INATTIVITA_MS = 300_000;
export const PIN_TURNO_MS = 36_000_000;
// Ingresso di assistenza del super admin: 2 ore.
export const ASSISTENZA_MS = 7_200_000;

export type SessioneVista = {
  userId: string;
  nome: string;
  ruoloPiattaforma: string | null;
  dueFattori: boolean;
  aziendaAttiva: string | null;
  tipo: "password" | "pin";
  creata: number;
  ultimaAttivita: number;
  dispositivo?: { id: string; nome: string };
};

export type AssistenzaVista = { id: string; organizationId: string; motivo: string; scade: number; fine?: number };
export type AziendaVista = { id: string; nome: string; demo: boolean };

export type Accesso = {
  utente: { id: string; nome: string };
  azienda: AziendaVista;
  ruoli: Role[];
  superadmin: boolean;
  tipo: "password" | "pin";
  dispositivo?: { id: string; nome: string };
  assistenza?: { id: string; motivo: string; scade: string };
};

export type Negato = {
  negato: 401 | 403;
  motivo: "nessuna-sessione" | "sessione-scaduta" | "nessuna-azienda" | "non-membro" | "assistenza-scaduta" | "due-fattori";
};

type Input = {
  sessione: SessioneVista | null;
  azienda: AziendaVista | null;
  ruoliMembro: string | null;
  assistenza: AssistenzaVista | null;
  ora: number;
};

// La regola unica: chi può usare quale azienda. Pura, senza accesso a database.
export function decidiAccesso(i: Input): Accesso | Negato {
  const { sessione, azienda, ora } = i;
  if (!sessione) return { negato: 401, motivo: "nessuna-sessione" };

  if (sessione.tipo === "pin" && (ora - sessione.ultimaAttivita > PIN_INATTIVITA_MS || ora - sessione.creata > PIN_TURNO_MS)) {
    return { negato: 401, motivo: "sessione-scaduta" };
  }

  // L'azienda deve essere quella attiva della sessione: mai una diversa.
  if (!sessione.aziendaAttiva || !azienda || azienda.id !== sessione.aziendaAttiva) {
    return { negato: 403, motivo: "nessuna-azienda" };
  }

  const superadmin = sessione.ruoloPiattaforma === "superadmin";
  // Il super admin senza codice dal telefono non entra in nessuna azienda, nemmeno se ne è membro.
  if (superadmin && !sessione.dueFattori) return { negato: 403, motivo: "due-fattori" };

  const base = {
    utente: { id: sessione.userId, nome: sessione.nome },
    azienda,
    superadmin,
    tipo: sessione.tipo,
    ...(sessione.dispositivo ? { dispositivo: sessione.dispositivo } : {}),
  };

  const ruoli = ruoliDaStringa(i.ruoliMembro);
  if (ruoli.length > 0) return { ...base, ruoli };

  if (!superadmin) return { negato: 403, motivo: "non-membro" };

  const a = i.assistenza;
  if (a && a.organizationId === azienda.id && a.fine === undefined && a.scade > ora) {
    return { ...base, ruoli: [...RUOLI], assistenza: { id: a.id, motivo: a.motivo, scade: new Date(a.scade).toISOString() } };
  }
  return { negato: 403, motivo: "assistenza-scaduta" };
}
