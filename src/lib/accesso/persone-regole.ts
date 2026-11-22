// Regole delle persone dell'azienda: controllo dei campi per creare e modificare un accesso e il vincolo
// del responsabile. Pure, senza database: le usano le route della Piattaforma e quelle del titolare (Persone).
import type { Role } from "../types.ts";
import { pinValido } from "./pin.ts";
import { RUOLI, ruoliDaStringa } from "./ruoli.ts";

export const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
/** Al titolare un'email già usata (anche da un'altra azienda) non si conferma: messaggio generico. */
export const EMAIL_USATA = "Non è stato possibile usare questa email.";
export const SERVE_PASSWORD = "Serve l'accesso con email e password.";
export const ALTRA_AZIENDA = "Questa persona lavora anche per un'altra azienda: chiedi all'assistenza.";

/**
 * Creare o modificare un accesso solo da una sessione con email e password (come registrare i dispositivi):
 * con il PIN di 4 cifre di un dispositivo condiviso si legge l'elenco, ma non si danno password o ruoli.
 */
export function scritturaPersoneNegata(tipo: "password" | "pin"): string | null {
  return tipo === "password" ? null : SERVE_PASSWORD;
}

/**
 * Password, email, PIN e sospensione valgono per tutto l'utente, non solo per questa azienda: se la persona è
 * membro anche di altre aziende li cambia solo l'assistenza. I ruoli sono di questa azienda e restano permessi.
 */
export function cambiNegatiAltraAzienda(cambi: ModificheIn, altreAziende: number): string | null {
  if (altreAziende === 0) return null;
  const tuttoLUtente = cambi.password !== undefined || cambi.email !== undefined || cambi.pin !== undefined || cambi.attivo !== undefined;
  return tuttoLUtente ? ALTRA_AZIENDA : null;
}

/** Il vincolo di cambioRuoliPermesso, detto al titolare. */
export const SERVE_RESPONSABILE = "L'azienda deve avere almeno un responsabile attivo: prima dai il ruolo Responsabile a un'altra persona.";
// Come Better Auth: oltre non si accetta (creaMembro fa l'hash senza passare dai suoi controlli)
const PASSWORD_MAX = 128;

const testo = (v: unknown, min: number, max: number): string | null => {
  if (typeof v !== "string") return null;
  const t = v.trim();
  return t.length >= min && t.length <= max ? t : null;
};

/** Ruoli del corpo: almeno uno, tutti validi (niente valori sconosciuti scartati in silenzio). */
export function ruoliDaCorpo(v: unknown): Role[] | null {
  if (!Array.isArray(v) || v.length === 0 || !v.every((r) => typeof r === "string")) return null;
  const r = ruoliDaStringa((v as string[]).join(","));
  return r.length === new Set(v as string[]).size ? r : null;
}

export type MembroRuoli = { userId: string; ruoli: Role[]; sospeso: boolean };

const responsabiliAttivi = (membri: MembroRuoli[]) => membri.filter((m) => !m.sospeso && m.ruoli.includes("responsabile")).length;

/**
 * Il cambio di ruoli (o la sospensione, con `sospeso: true`) di `userId` si può fare? No se così l'azienda resta
 * senza un responsabile non sospeso. Un'azienda che già non ne ha uno non peggiora: lì ogni cambio vale.
 */
export function cambioRuoliPermesso(membri: MembroRuoli[], userId: string, nuoviRuoli: Role[], sospeso?: boolean): boolean {
  const dopo = membri.map((m) => (m.userId === userId ? { ...m, ruoli: nuoviRuoli, sospeso: sospeso ?? m.sospeso } : m));
  return responsabiliAttivi(dopo) > 0 || responsabiliAttivi(membri) === 0;
}

export type NuovoMembroIn = { nome: string; ruoli: Role[]; email?: string; password?: string; pin?: string };

/** Corpo della creazione: nome, ruoli e il modo d'accesso (email + password e/o PIN). */
export function nuovoMembroDaCorpo(corpo: Record<string, unknown>, passwordMin: number): { dati: NuovoMembroIn } | { errore: string } {
  const nome = testo(corpo.nome, 2, 80);
  if (!nome) return { errore: "Scrivi il nome della persona (da 2 a 80 caratteri)." };
  const ruoli = ruoliDaCorpo(corpo.ruoli);
  if (!ruoli) return { errore: `Scegli almeno un ruolo tra: ${RUOLI.join(", ")}.` };

  // Modo d'accesso: email + password (da qualunque dispositivo) e/o PIN (solo dai dispositivi dell'azienda)
  const email = typeof corpo.email === "string" ? corpo.email.trim().toLowerCase() : "";
  const password = typeof corpo.password === "string" ? corpo.password : "";
  const pin = typeof corpo.pin === "string" ? corpo.pin : "";
  const conEmail = !!email || !!password;
  if (conEmail && (!EMAIL.test(email) || email.endsWith("@pin.invalid") || password.length < passwordMin || password.length > PASSWORD_MAX)) {
    return { errore: `Per l'accesso con email servono un'email valida e una password di almeno ${passwordMin} caratteri.` };
  }
  if (pin && !pinValido(pin)) return { errore: "Il PIN è di 4 cifre." };
  if (!conEmail && !pin) return { errore: "Scegli come entra: email e password, PIN, o tutti e due." };
  return { dati: { nome, ruoli, ...(conEmail ? { email, password } : {}), ...(pin ? { pin } : {}) } };
}

/** `email` serve solo a chi entra col PIN e riceve la sua prima password. */
export type ModificheIn = { ruoli?: Role[]; pin?: string; password?: string; email?: string; attivo?: boolean };

/** Corpo della modifica: ruoli, nuovo PIN, nuova password (con l'email per chi non l'ha), attivo o sospeso. */
export function modificheDaCorpo(corpo: Record<string, unknown>, passwordMin: number): { cambi: ModificheIn } | { errore: string } {
  const cambi: ModificheIn = {};
  if (corpo.ruoli !== undefined) {
    const r = ruoliDaCorpo(corpo.ruoli);
    if (!r) return { errore: "Scegli almeno un ruolo valido." };
    cambi.ruoli = r;
  }
  if (corpo.pin !== undefined) {
    if (typeof corpo.pin !== "string" || !pinValido(corpo.pin)) return { errore: "Il PIN è di 4 cifre." };
    cambi.pin = corpo.pin;
  }
  if (corpo.password !== undefined) {
    if (typeof corpo.password !== "string" || corpo.password.length < passwordMin || corpo.password.length > PASSWORD_MAX) {
      return { errore: `La password deve avere almeno ${passwordMin} caratteri.` };
    }
    cambi.password = corpo.password;
  }
  if (corpo.attivo !== undefined) {
    if (typeof corpo.attivo !== "boolean") return { errore: "Richiesta non valida." };
    cambi.attivo = corpo.attivo;
  }
  const email = typeof corpo.email === "string" && corpo.email.trim() ? corpo.email.trim().toLowerCase() : "";
  if (email) {
    if (!EMAIL.test(email) || email.endsWith("@pin.invalid")) return { errore: "Email non valida." };
    cambi.email = email;
  }
  if (!cambi.ruoli && cambi.pin === undefined && cambi.password === undefined && cambi.attivo === undefined) return { errore: "Niente da modificare." };
  return { cambi };
}
