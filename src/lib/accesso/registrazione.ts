// Registrazione del titolare su invito: controllo dei campi e limite per indirizzo. Nessun accesso a file o database.
import { formatoCodice } from "./inviti-regole";

export type DatiRegistrazione = { azienda: string; nome: string; email: string; password: string; invito: string; condizioni: true };

export const PASSWORD_MIN = 10;
// Come Better Auth: oltre non si accetta (creaMembro fa l'hash senza passare dai suoi controlli)
export const PASSWORD_MAX = 128;

const testo = (v: unknown, min: number, max: number): string | null => {
  if (typeof v !== "string") return null;
  const t = v.trim();
  return t.length >= min && t.length <= max ? t : null;
};

export function validaRegistrazione(corpo: unknown): { ok: DatiRegistrazione } | { errore: string } {
  if (!corpo || typeof corpo !== "object" || Array.isArray(corpo)) return { errore: "Richiesta non valida." };
  const b = corpo as Record<string, unknown>;
  const azienda = testo(b.azienda, 2, 80);
  if (!azienda) return { errore: "Scrivi il nome dell'azienda (da 2 a 80 caratteri)." };
  const nome = testo(b.nome, 1, 100);
  if (!nome) return { errore: "Scrivi nome e cognome del titolare." };
  const email = typeof b.email === "string" ? b.email.trim().toLowerCase() : "";
  if (email.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return { errore: "Scrivi un'email valida." };
  const password = typeof b.password === "string" ? b.password : "";
  if (password.length < PASSWORD_MIN) return { errore: "La password deve avere almeno 10 caratteri." };
  if (password.length > PASSWORD_MAX) return { errore: "La password può avere al massimo 128 caratteri." };
  if (b.condizioni !== true) return { errore: "Per registrarti devi accettare le condizioni del servizio." };
  const invito = typeof b.invito === "string" ? formatoCodice(b.invito) : null;
  if (!invito) return { errore: "Codice invito non valido" };
  return { ok: { azienda, nome, email, password, invito, condizioni: true } };
}

// Al massimo 3 registrazioni all'ora per indirizzo (ipCliente: x-real-ip su Vercel, altrimenti cf-connecting-ip).
// Senza indirizzo (localhost, rete interna) un contatore comune. Conta ogni richiesta all'arrivo. In memoria: un solo processo Node (docs/ACCESSO.md).
export const REGISTRAZIONI_MAX = 3;
export const REGISTRAZIONI_FINESTRA_MS = 60 * 60_000;

const g = globalThis as typeof globalThis & { __registrazioni?: Map<string, number[]> };
const conti = (g.__registrazioni ??= new Map<string, number[]>());

const vive = (tempi: number[], ora: number) => tempi.filter((t) => ora - t < REGISTRAZIONI_FINESTRA_MS && t <= ora);

export function registrazioneConsentita(ip: string | null, ora: number): boolean {
  // Ogni tanto si dimenticano gli indirizzi fermi da più di un'ora
  if (conti.size > 1000) for (const [k, t] of conti) if (!vive(t, ora).length) conti.delete(k);
  const k = ip?.trim() ? `ip:${ip.trim()}` : "comune";
  const tempi = vive(conti.get(k) ?? [], ora);
  if (tempi.length >= REGISTRAZIONI_MAX) {
    conti.set(k, tempi);
    return false;
  }
  tempi.push(ora);
  conti.set(k, tempi);
  return true;
}
