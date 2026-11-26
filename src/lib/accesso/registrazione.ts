// Registrazione libera del titolare: controllo dei campi e limite per indirizzo. Nessun accesso a file o database.

export type DatiRegistrazione = {
  azienda: string;
  nome: string;
  email: string;
  password: string;
  telefono: string | null;
  condizioni: true;
  commerciale: boolean;
};

export const PASSWORD_MIN = 10;
// Come Better Auth: oltre non si accetta (creaMembro fa l'hash senza passare dai suoi controlli)
export const PASSWORD_MAX = 128;

const testo = (v: unknown, min: number, max: number): string | null => {
  if (typeof v !== "string") return null;
  const t = v.trim();
  return t.length >= min && t.length <= max ? t : null;
};

// Il nome del titolare finisce nelle email di avviso della prova (non in quella di conferma): niente indirizzi web,
// email o numeri scritti da chi registra. Dopo NFKC i punti larghi diventano "."; un punto (o simile) va bene solo
// seguito da uno spazio o in fondo ("F. Bianchi"), e non tra due parole staccate ("evil . com").
// Il nome dell'azienda non finisce in nessuna email: si fermano solo gli indirizzi evidenti (sigle come "SI.ME. srl" vanno).
const conIndirizzo = (t: string) => /:\/\/|www\.|@/i.test(t);
const nomeConIndirizzo = (t: string) => {
  const n = t.normalize("NFKC").replace(/[\u2024\u3002\uFF0E\uFE52\uFF61]/g, ".");
  return conIndirizzo(n) || /\.(?!\s|$)/u.test(n) || /[\p{L}\p{N}-]{2,}\s+\.\s*\p{L}{2,}/u.test(n);
};

export function validaRegistrazione(corpo: unknown): { ok: DatiRegistrazione } | { errore: string } {
  if (!corpo || typeof corpo !== "object" || Array.isArray(corpo)) return { errore: "Richiesta non valida." };
  const b = corpo as Record<string, unknown>;
  const azienda = testo(b.azienda, 2, 80);
  if (!azienda) return { errore: "Scrivi il nome dell'azienda (da 2 a 80 caratteri)." };
  if (conIndirizzo(azienda)) return { errore: "Il nome dell'azienda non può contenere indirizzi web o email." };
  const nome = testo(b.nome, 1, 100);
  if (!nome) return { errore: "Scrivi nome e cognome del titolare." };
  if (/\p{N}/u.test(nome) || nomeConIndirizzo(nome)) return { errore: "Nel nome del titolare scrivi solo nome e cognome, senza numeri o indirizzi." };
  const email = typeof b.email === "string" ? b.email.trim().toLowerCase() : "";
  if (email.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return { errore: "Scrivi un'email valida." };
  const password = typeof b.password === "string" ? b.password : "";
  if (password.length < PASSWORD_MIN) return { errore: "La password deve avere almeno 10 caratteri." };
  if (password.length > PASSWORD_MAX) return { errore: "La password può avere al massimo 128 caratteri." };
  // Facoltativo: vuoto o assente è null; se c'è, solo cifre, spazi e + (da 6 a 20 caratteri), con almeno 6 cifre
  let telefono: string | null = null;
  if (b.telefono !== undefined && b.telefono !== null) {
    const t = typeof b.telefono === "string" ? b.telefono.trim() : null;
    if (t === null || (t && (!/^[0-9 +]{6,20}$/.test(t) || t.replace(/\D/g, "").length < 6))) return { errore: "Scrivi un numero di telefono valido o lascia vuoto." };
    telefono = t || null;
  }
  if (b.condizioni !== true) return { errore: "Per registrarti devi accettare le condizioni del servizio." };
  return { ok: { azienda, nome, email, password, telefono, condizioni: true, commerciale: b.commerciale === true } };
}

// Al massimo 3 registrazioni all'ora per indirizzo (ipCliente: x-real-ip su Vercel, altrimenti cf-connecting-ip).
// Senza indirizzo (localhost, rete interna) un contatore comune. Conta le richieste con i campi validi (un errore di
// battitura non consuma un tentativo). In memoria: un solo processo Node (docs/ACCESSO.md).
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
