import { auth } from "@/lib/auth/server";
import { richiestaPassiva } from "./attivita";
import type { Role } from "@/lib/types";
import {
  decidiAccesso,
  type Accesso,
  type AssistenzaVista,
  type AziendaVista,
  type Negato,
  type SessioneVista,
} from "./regole";

const PIN_AGGIORNA_OGNI_MS = 60_000;

const MESSAGGI: Record<Negato["motivo"], string> = {
  "nessuna-sessione": "Accedi per continuare.",
  "sessione-scaduta": "Sessione scaduta: accedi di nuovo.",
  "nessuna-azienda": "Scegli prima un'azienda.",
  "non-membro": "Non hai accesso a questa azienda.",
  "assistenza-scaduta": "L'ingresso di assistenza non è attivo.",
  "due-fattori": "Serve il codice dal telefono per entrare in un'azienda.",
  impersonazione: "Questo tipo di accesso non è consentito.",
  "dispositivo-revocato": "Questo dispositivo non è più registrato: accedi con email e password.",
};

function negata(stato: 401 | 403, motivo: Negato["motivo"]): Response {
  return Response.json({ error: MESSAGGI[motivo], motivo }, { status: stato, headers: { "Cache-Control": "no-store" } });
}

function ms(d: unknown): number {
  return d instanceof Date ? d.getTime() : new Date(d as string | number).getTime();
}

function eSuperadmin(role: string | null | undefined): boolean {
  return (role ?? "").split(",").map((r) => r.trim()).includes("superadmin");
}

// Lettura autorevole dal database: il cookie cache di Better Auth viene escluso, così una sessione
// revocata o un utente bannito si vedono subito. disableRefresh: Better Auth non deve riscrivere updatedAt
// prima del controllo di inattività del PIN: l'unico a scriverlo, su questa strada, è l'aggiornamento più sotto.
async function leggiSessione(req: Request) {
  return auth.api.getSession({ headers: req.headers, query: { disableCookieCache: true, disableRefresh: true } });
}

// metadata è salvata come stringa JSON: demo solo se è un oggetto con demo === true.
function aziendaVista(o: { id: string; name: string; metadata?: unknown } | null): AziendaVista | null {
  if (!o) return null;
  let demo = false;
  try {
    const m = typeof o.metadata === "string" ? JSON.parse(o.metadata) : o.metadata;
    demo = typeof m === "object" && m !== null && (m as { demo?: unknown }).demo === true;
  } catch {
    demo = false;
  }
  return { id: o.id, nome: o.name, demo };
}

export async function accessoDaRichiesta(req: Request, opzioni: { attivitaAlle?: number } = {}): Promise<Accesso | Response> {
  const dati = await leggiSessione(req);
  const ora = Date.now();
  if (!dati) return negata(401, "nessuna-sessione");

  const { session, user } = dati;
  const extra = session as typeof session & {
    activeOrganizationId?: string | null;
    tipoAccesso?: string | null;
    dispositivoId?: string | null;
    impersonatedBy?: string | null;
    dueFattoriVerificato?: boolean | null;
  };
  const u = user as typeof user & { role?: string | null; twoFactorEnabled?: boolean | null };

  const vista: SessioneVista = {
    userId: user.id,
    nome: user.name,
    ruoloPiattaforma: eSuperadmin(u.role) ? "superadmin" : (u.role ?? null),
    // Il secondo fattore vale per la SESSIONE (campo scritto dall'hook in assistenza.ts), non per l'utente.
    dueFattori: u.twoFactorEnabled === true && extra.dueFattoriVerificato === true,
    impersonata: !!extra.impersonatedBy,
    aziendaAttiva: extra.activeOrganizationId ?? null,
    tipo: extra.tipoAccesso === "pin" ? "pin" : "password",
    creata: ms(session.createdAt),
    ultimaAttivita: ms(session.updatedAt),
  };

  const ctx = await auth.$context;

  // Sessione da PIN: il dispositivo deve esistere, non essere revocato ed essere dell'azienda attiva.
  // Altrimenti `dispositivo` resta vuoto e la regola nega con "dispositivo-revocato".
  if (vista.tipo === "pin" && extra.dispositivoId) {
    const d = await ctx.adapter.findOne<{ id: string; nome: string; organizationId: string; revocato?: unknown }>({
      model: "dispositivo",
      where: [{ field: "id", value: extra.dispositivoId }],
    });
    if (d && !d.revocato && d.organizationId === vista.aziendaAttiva) vista.dispositivo = { id: d.id, nome: d.nome };
  }

  let azienda: AziendaVista | null = null;
  let ruoliMembro: string | null = null;
  let assistenza: AssistenzaVista | null = null;

  if (vista.aziendaAttiva) {
    const org = await ctx.adapter.findOne<{ id: string; name: string; metadata?: unknown }>({
      model: "organization",
      where: [{ field: "id", value: vista.aziendaAttiva }],
    });
    azienda = aziendaVista(org);
    if (azienda) {
      const membro = await ctx.adapter.findOne<{ role: string }>({
        model: "member",
        where: [
          { field: "userId", value: user.id },
          { field: "organizationId", value: azienda.id },
        ],
      });
      ruoliMembro = membro?.role ?? null;
      if (vista.ruoloPiattaforma === "superadmin") {
        const righe = await ctx.adapter.findMany<{ id: string; organizationId: string; motivo: string; scade: unknown; fine?: unknown }>({
          model: "assistenza",
          where: [
            { field: "userId", value: user.id },
            { field: "organizationId", value: azienda.id },
          ],
          sortBy: { field: "inizio", direction: "desc" },
          limit: 1,
        });
        const r = righe[0];
        if (r) {
          assistenza = {
            id: r.id,
            organizationId: r.organizationId,
            motivo: r.motivo,
            scade: ms(r.scade),
            ...(r.fine ? { fine: ms(r.fine) } : {}),
          };
        }
      }
    }
  }

  const esito = decidiAccesso({ sessione: vista, azienda, ruoliMembro, assistenza, ora });
  if ("negato" in esito) {
    // Sessione PIN scaduta o senza dispositivo valido: la revoca, così il cookie non vale più nemmeno se riprovato.
    if (esito.motivo === "sessione-scaduta" || esito.motivo === "dispositivo-revocato") await ctx.internalAdapter.deleteSession(session.token);
    return negata(esito.negato, esito.motivo);
  }

  // Sessione PIN: segna l'attività (updatedAt) con l'adapter interno di Better Auth, al massimo una volta al minuto.
  // Le richieste automatiche (intestazione x-attivita: passiva) non contano: con il tablet fermo la sessione scade
  // anche se una pagina resta aperta. Il battito del blocco di inattività (`attivitaAlle`) la segna sempre.
  // Il battito porta l'istante dell'ultimo tocco: si usa quello (mai oltre adesso, mai indietro), così il server
  // scade 5 minuti dopo l'ultimo tocco vero, insieme al blocco sullo schermo.
  if (vista.tipo === "pin" && !richiestaPassiva(req.headers)) {
    const battito = opzioni.attivitaAlle !== undefined && Number.isFinite(opzioni.attivitaAlle);
    const alle = battito ? Math.min(ora, opzioni.attivitaAlle!) : ora;
    if (battito ? alle > vista.ultimaAttivita : ora - vista.ultimaAttivita > PIN_AGGIORNA_OGNI_MS) {
      await ctx.internalAdapter.updateSession(session.token, { updatedAt: new Date(alle) });
    }
  }
  return esito;
}

export function soloRuoli(a: Accesso, ...r: Role[]): Response | null {
  if (r.some((x) => a.ruoli.includes(x))) return null;
  return Response.json({ error: "Non hai il permesso per questa operazione.", motivo: "ruolo" }, { status: 403, headers: { "Cache-Control": "no-store" } });
}

export async function superadminDaRichiesta(req: Request): Promise<{ utente: { id: string; nome: string } } | Response> {
  const dati = await leggiSessione(req);
  if (!dati) return negata(401, "nessuna-sessione");
  const { session, user } = dati;
  const u = user as typeof user & { role?: string | null; twoFactorEnabled?: boolean | null };
  const extra = session as typeof session & { tipoAccesso?: string | null; impersonatedBy?: string | null; dueFattoriVerificato?: boolean | null };
  if (extra.impersonatedBy) return negata(403, "impersonazione");
  if (extra.tipoAccesso === "pin" || !eSuperadmin(u.role)) {
    return Response.json({ error: "Area riservata.", motivo: "non-superadmin" }, { status: 403, headers: { "Cache-Control": "no-store" } });
  }
  if (u.twoFactorEnabled !== true || extra.dueFattoriVerificato !== true) return negata(403, "due-fattori");
  return { utente: { id: user.id, nome: user.name } };
}
