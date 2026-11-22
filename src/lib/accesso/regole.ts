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
  dueFattori: boolean; // true solo se QUESTA sessione ha superato il secondo fattore
  impersonata: boolean;
  aziendaAttiva: string | null;
  tipo: "password" | "pin";
  creata: number;
  ultimaAttivita: number;
  // Solo sessioni da PIN: il dispositivo esiste, non è revocato ed è dell'azienda attiva. Altrimenti assente.
  dispositivo?: { id: string; nome: string };
  // Il browser è un dispositivo condiviso dell'azienda (cookie del dispositivo valido): anche una sessione con
  // password (es. il responsabile che sblocca il tablet) ha il blocco dopo 5 minuti e il turno di 10 ore.
  dispositivoCondiviso?: boolean;
};

export type AssistenzaVista = { id: string; organizationId: string; motivo: string; scade: number; fine?: number };
export type AziendaVista = { id: string; nome: string; demo: boolean; registrata: boolean };

export type Accesso = {
  utente: { id: string; nome: string };
  azienda: AziendaVista;
  ruoli: Role[];
  superadmin: boolean;
  tipo: "password" | "pin";
  dispositivo?: { id: string; nome: string };
  assistenza?: { id: string; motivo: string; scade: string };
  // Sessione con password su un dispositivo condiviso: il browser applica il blocco di inattività come col PIN
  dispositivoCondiviso?: true;
};

// La scheda del browser dice con quale azienda è partita (intestazione x-azienda). Se la sessione nel frattempo è
// passata a un'altra azienda (ingresso di assistenza in un'altra scheda), la richiesta si rifiuta con 409:
// la scheda vecchia non deve leggere né scrivere i dati dell'azienda nuova. L'azienda la decide sempre la sessione;
// l'intestazione può solo far rifiutare una richiesta, mai farne passare una.
export const INTESTAZIONE_AZIENDA = "x-azienda";
export const MOTIVO_AZIENDA_CAMBIATA = "azienda-cambiata";

export function aziendaCambiata(intestazione: string | null | undefined, aziendaSessione: string | null | undefined): boolean {
  if (intestazione === null || intestazione === undefined) return false;
  const v = intestazione.trim();
  // Intestazione presente ma vuota: la scheda non ha un'azienda fissata, non c'è nulla da confrontare
  if (!v) return false;
  return v !== (aziendaSessione ?? "");
}

export type Negato = {
  negato: 401 | 403;
  motivo: "nessuna-sessione" | "sessione-scaduta" | "nessuna-azienda" | "non-membro" | "assistenza-scaduta" | "due-fattori" | "impersonazione" | "dispositivo-revocato";
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

  // Le sessioni create con "impersonate" non entrano mai: aggirerebbero assistenza e secondo fattore.
  if (sessione.impersonata) return { negato: 403, motivo: "impersonazione" };

  // Sessione da PIN, o qualunque sessione su un dispositivo condiviso: 5 minuti senza attività, 10 ore al massimo.
  const aTempo = sessione.tipo === "pin" || sessione.dispositivoCondiviso === true;
  if (aTempo && (ora - sessione.ultimaAttivita > PIN_INATTIVITA_MS || ora - sessione.creata > PIN_TURNO_MS)) {
    return { negato: 401, motivo: "sessione-scaduta" };
  }

  // Una sessione da PIN vale solo con il suo dispositivo ancora registrato (non revocato) e della stessa azienda:
  // chi la carica lascia `dispositivo` vuoto in tutti gli altri casi.
  if (sessione.tipo === "pin" && !sessione.dispositivo) return { negato: 401, motivo: "dispositivo-revocato" };

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
    ...(sessione.tipo === "password" && sessione.dispositivoCondiviso ? { dispositivoCondiviso: true as const } : {}),
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
