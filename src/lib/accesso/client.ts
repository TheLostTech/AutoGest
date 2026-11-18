"use client";

// Sessione nel browser: si carica una volta da /api/sessione e la leggono Hydrator, menu e fascia di assistenza.
import { useEffect, useState } from "react";
import type { Accesso } from "./regole";

export type EsitoSessione = { ok: true; accesso: Accesso } | { ok: false; stato: number; motivo?: string };

let cache: EsitoSessione | null = null;
let inCorso: Promise<EsitoSessione> | null = null;
const ascoltatori = new Set<() => void>();

async function leggi(): Promise<EsitoSessione> {
  try {
    const r = await fetch("/api/sessione", { cache: "no-store" });
    if (r.ok) return { ok: true, accesso: (await r.json()) as Accesso };
    const j = (await r.json().catch(() => ({}))) as { motivo?: string };
    return { ok: false, stato: r.status, motivo: j.motivo };
  } catch {
    return { ok: false, stato: 0 };
  }
}

/** Carica la sessione una sola volta; `forza` la rilegge dal server. */
export function caricaSessione(forza = false): Promise<EsitoSessione> {
  if (!forza && cache) return Promise.resolve(cache);
  if (!inCorso) {
    inCorso = leggi().then((e) => {
      cache = e;
      inCorso = null;
      ascoltatori.forEach((f) => f());
      return e;
    });
  }
  return inCorso;
}

export function useSessione(): { accesso: Accesso | null; ricarica: () => Promise<EsitoSessione> } {
  const [esito, setEsito] = useState<EsitoSessione | null>(cache);
  useEffect(() => {
    const f = () => setEsito(cache);
    ascoltatori.add(f);
    void caricaSessione();
    return () => void ascoltatori.delete(f);
  }, []);
  return { accesso: esito && esito.ok ? esito.accesso : null, ricarica: () => caricaSessione(true) };
}

/**
 * Esce dall'account e torna alla pagina di accesso (su un dispositivo dell'azienda: all'elenco dei nomi).
 * Prima prova a inviare le modifiche in sospeso; quelle non inviate restano per il prossimo accesso.
 */
export async function esci(): Promise<void> {
  const { inviaInSospeso } = await import("../sync");
  await inviaInSospeso().catch(() => false);
  const { authClient } = await import("../auth/client");
  await authClient.signOut().catch(() => undefined);
  window.location.assign("/accesso");
}
