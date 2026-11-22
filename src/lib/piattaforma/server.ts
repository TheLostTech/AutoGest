import type { AuthContext } from "better-auth";
import { auth } from "@/lib/auth/server";
import { aggiungiEventi, type NuovoEvento } from "@/lib/archivio-azienda";
import { altroSito, richiestaDellApp } from "@/lib/collegamenti-server";
import { rispostaNonPronta } from "@/lib/accesso/pronta";
import { idAziendaValido } from "@/lib/accesso/id-azienda";

// Funzioni comuni delle route /api/piattaforma/*: tutte per il super admin, mai per le aziende.

const NO_STORE = { "Cache-Control": "no-store" };

export function errore(stato: number, messaggio: string, motivo?: string): Response {
  return Response.json({ error: messaggio, ...(motivo ? { motivo } : {}) }, { status: stato, headers: NO_STORE });
}

export function ok(dati: unknown = { ok: true }, stato = 200): Response {
  return Response.json(dati, { status: stato, headers: NO_STORE });
}

/**
 * Richieste che cambiano qualcosa: devono partire da questo sito. JSON: Origin + corpo JSON (come le altre API).
 * Senza corpo JSON (caricamento di file, DELETE): Origin obbligatorio e uguale al sito.
 */
export function daAltroSito(req: Request, json: boolean): Response | null {
  const buona = json ? richiestaDellApp(req) : !!req.headers.get("origin") && !altroSito(req);
  return buona ? null : errore(403, "Richiesta non consentita.", "altro-sito");
}

export async function leggiJson(req: Request): Promise<Record<string, unknown> | null> {
  try {
    const b = await req.json();
    return b && typeof b === "object" && !Array.isArray(b) ? (b as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

export const contesto = () => auth.$context as unknown as Promise<AuthContext>;
export type Contesto = AuthContext;

export function testo(v: unknown, min: number, max: number): string | null {
  if (typeof v !== "string") return null;
  const t = v.trim();
  return t.length >= min && t.length <= max ? t : null;
}

export function eSuperadmin(role: string | null | undefined): boolean {
  return (role ?? "").split(",").map((r) => r.trim()).includes("superadmin");
}

/** Sessione con password di un super admin, anche prima del codice dal telefono (serve alla pagina Sicurezza). */
export async function superadminBase(req: Request) {
  const nonPronta = rispostaNonPronta();
  if (nonPronta) return { risposta: nonPronta };
  const dati = await auth.api.getSession({ headers: req.headers, query: { disableCookieCache: true, disableRefresh: true } });
  if (!dati) return { risposta: errore(401, "Accedi per continuare.", "nessuna-sessione") };
  const { session, user } = dati;
  const s = session as typeof session & { tipoAccesso?: string | null; impersonatedBy?: string | null; dueFattoriVerificato?: boolean | null; activeOrganizationId?: string | null };
  const u = user as typeof user & { role?: string | null; twoFactorEnabled?: boolean | null };
  if (s.impersonatedBy) return { risposta: errore(403, "Questo tipo di accesso non è consentito.", "impersonazione") };
  if (s.tipoAccesso === "pin" || !eSuperadmin(u.role)) return { risposta: errore(403, "Area riservata.", "non-superadmin") };
  return {
    sessione: {
      token: session.token,
      utente: { id: user.id, nome: user.name, email: user.email },
      dueFattoriAttivo: u.twoFactorEnabled === true,
      dueFattoriVerificato: s.dueFattoriVerificato === true,
      aziendaAttiva: s.activeOrganizationId ?? null,
    },
  };
}

/** Il token della sessione corrente (dopo superadminDaRichiesta, che ha già deciso se può passare). */
export async function tokenSessione(req: Request): Promise<string | null> {
  const dati = await auth.api.getSession({ headers: req.headers, query: { disableCookieCache: true, disableRefresh: true } });
  return dati?.session.token ?? null;
}

export async function aziendaEsiste(id: unknown): Promise<{ id: string; name: string } | null> {
  if (typeof id !== "string" || !idAziendaValido(id)) return null;
  const c = await contesto();
  return c.adapter.findOne<{ id: string; name: string }>({ model: "organization", where: [{ field: "id", value: id }] });
}

// Chi ha fatto l'azione, nel registro dell'azienda: il super admin, dal dispositivo "Piattaforma".
export function firma(nome: string): Pick<NuovoEvento, "user" | "role" | "device"> {
  return { user: `${nome} (assistenza)`, role: "sistema", device: "Piattaforma" };
}

export const AVVISO_REGISTRO = "La modifica è stata fatta, ma non sono riuscito a scriverla nel registro attività dell'azienda.";

/** Una riga nel registro attività. Best-effort: un guasto non annulla la modifica già fatta, ma restituisce false (le route mettono `avviso` nella risposta). */
export async function registra(aziendaId: string, nome: string, e: Omit<NuovoEvento, "user" | "role" | "device">): Promise<boolean> {
  try {
    await aggiungiEventi(aziendaId, [{ ...firma(nome), ...e }]);
    return true;
  } catch (err) {
    console.error("Registro attività non aggiornato", aziendaId, err);
    return false;
  }
}

/** Come registra, ma il guasto si propaga: per le azioni che senza traccia non devono avvenire (ingresso per assistenza). */
export async function registraObbligatorio(aziendaId: string, nome: string, e: Omit<NuovoEvento, "user" | "role" | "device">): Promise<void> {
  await aggiungiEventi(aziendaId, [{ ...firma(nome), ...e }]);
}

/** Chiude tutte le sessioni di un utente (cambio ruoli, password o PIN, disattivazione). */
export async function chiudiSessioni(c: Contesto, userId: string): Promise<void> {
  const righe = await c.adapter.findMany<{ token: string }>({ model: "session", where: [{ field: "userId", value: userId }] });
  for (const s of righe) await c.internalAdapter.deleteSession(s.token);
}
