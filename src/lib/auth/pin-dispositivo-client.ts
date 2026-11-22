import type { BetterAuthClientPlugin } from "better-auth/client";
import { intestazioniAzienda } from "@/lib/accesso/azienda-client";

// Le chiamate del plugin pin-dispositivo dal browser, con i tipi delle risposte.
export type NomiDispositivo = { azienda: string; dispositivo: string; bloccato: boolean; nomi: { userId: string; nome: string; bloccato: boolean }[] };
export type DispositivoAzienda = { id: string; nome: string; creato: string; creatoDa: string; revocato: string | null; bloccato: boolean; questo: boolean };
export type ElencoDispositivi = { passwordSession: boolean; dispositivi: DispositivoAzienda[] };

type Esito<T> = { data: T | null; error: { status: number; message?: string; code?: string } | null };

export const pinDispositivoClient = () =>
  ({
    id: "pin-dispositivo",
    pathMethods: {
      "/pin-dispositivo/nomi": "GET",
      "/pin-dispositivo/elenco": "GET",
    },
    getActions: ($fetch) => ({
      pinDispositivo: {
        nomi: () => $fetch<NomiDispositivo>("/pin-dispositivo/nomi", { method: "GET" }) as Promise<Esito<NomiDispositivo>>,
        entra: (b: { userId: string; pin: string }) => $fetch<{ ok: true }>("/pin-dispositivo/entra", { method: "POST", body: b }) as Promise<Esito<{ ok: true }>>,
        registra: (b: { nome: string }) => $fetch<{ id: string; nome: string }>("/pin-dispositivo/registra", { method: "POST", body: b, headers: intestazioniAzienda() }) as Promise<Esito<{ id: string; nome: string }>>,
        // Gestione dei dispositivi: con l'azienda della scheda (x-azienda), come le altre API dell'azienda
        elenco: () => $fetch<ElencoDispositivi>("/pin-dispositivo/elenco", { method: "GET", headers: intestazioniAzienda() }) as Promise<Esito<ElencoDispositivi>>,
        revoca: (b: { dispositivoId: string }) => $fetch<{ ok: true }>("/pin-dispositivo/revoca", { method: "POST", body: b, headers: intestazioniAzienda() }) as Promise<Esito<{ ok: true }>>,
        // esci: sbloccato proprio questo browser, la sessione è stata chiusa (si torna all'elenco dei nomi)
        sblocca: (b: { dispositivoId: string }) =>
          $fetch<{ ok: true; esci?: boolean }>("/pin-dispositivo/sblocca", { method: "POST", body: b, headers: intestazioniAzienda() }) as Promise<Esito<{ ok: true; esci?: boolean }>>,
      },
    }),
  }) satisfies BetterAuthClientPlugin;
