import { ruoliDaStringa } from "@/lib/accesso/ruoli";
import { FILE_RICHIESTA, leggiFileRichiesta } from "./richieste-file";
import { errore, testo } from "./server";
import type { Role } from "@/lib/types";

export type RichiestaIn = { fileId?: string; estremi?: string };

/** Ruoli del corpo: almeno uno, tutti validi (niente valori sconosciuti scartati in silenzio). */
export function ruoliDaCorpo(v: unknown): Role[] | null {
  if (!Array.isArray(v) || v.length === 0 || !v.every((r) => typeof r === "string")) return null;
  const r = ruoliDaStringa((v as string[]).join(","));
  return r.length === new Set(v as string[]).size ? r : null;
}

/** Richiesta scritta del corpo: serve almeno un file (già caricato per quest'azienda) o gli estremi. */
export async function richiestaDaCorpo(aziendaId: string, v: unknown, obbligatoria: boolean): Promise<{ richiesta: RichiestaIn | null } | { errore: Response }> {
  const o = v && typeof v === "object" ? (v as Record<string, unknown>) : null;
  const estremi = testo(o?.estremi, 3, 500) ?? undefined;
  const fileId = typeof o?.fileId === "string" && o.fileId ? o.fileId : undefined;
  if (fileId && (!FILE_RICHIESTA.test(fileId) || !(await leggiFileRichiesta(aziendaId, fileId)))) {
    return { errore: errore(400, "Il file della richiesta non c'è: caricalo di nuovo.") };
  }
  if (!fileId && !estremi) {
    return obbligatoria ? { errore: errore(400, "Serve la richiesta scritta dell'azienda: allega il file o scrivi gli estremi (data e chi la firma).", "richiesta") } : { richiesta: null };
  }
  return { richiesta: { ...(fileId ? { fileId } : {}), ...(estremi ? { estremi } : {}) } };
}

export const descrizioneRichiesta = (r: RichiestaIn | null) => (r ? [r.estremi, r.fileId ? "file allegato" : ""].filter(Boolean).join(" + ") : "nessuna");

export const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
