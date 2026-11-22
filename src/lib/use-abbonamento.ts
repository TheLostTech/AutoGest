"use client";

// Stato dell'abbonamento nel browser, da GET /api/abbonamento/stato: una copia sola per la pagina, condivisa da
// AppShell (riquadro di pagamento), pagina Abbonamento e ritorno da Checkout.
import { useEffect, useState } from "react";
import type { Abbonamento, Conto } from "./abbonamento";
import type { ModalitaStripe } from "./stripe/chiavi";
import { fetchAzienda } from "./accesso/azienda-client";
import { intestazioniPassive } from "./accesso/attivita";

export type StatoApi = { abbonamento: Abbonamento | null; registrata: boolean; modalita: ModalitaStripe; conto: Conto | null };

let dati: StatoApi | null = null;
let letto = 0; // quando è arrivata l'ultima risposta (ms)
let inCorso: Promise<void> | null = null;
const ascoltatori = new Set<() => void>();
// Tornando sulla scheda si rilegge, ma non più di una volta ogni 30 secondi
const RILEGGI_DOPO_MS = 30_000;

async function leggi(sincronizza: boolean): Promise<void> {
  try {
    // Lettura automatica: per una sessione da PIN non conta come attività della persona
    const r = await fetchAzienda(`/api/abbonamento/stato${sincronizza ? "?sincronizza=1" : ""}`, { cache: "no-store", headers: intestazioniPassive() });
    if (!r.ok) return;
    dati = (await r.json()) as StatoApi;
    letto = Date.now();
    ascoltatori.forEach((f) => f());
  } catch {
    // server non raggiungibile: resta l'ultimo stato letto
  }
}

/** Rilegge lo stato; con `sincronizza` il server lo chiede prima a Stripe (al massimo una volta ogni 15 secondi). */
export function ricaricaAbbonamento(sincronizza = false): Promise<void> {
  // Una lettura semplice già in corso basta; una con sincronizzazione parte comunque dopo
  if (inCorso && !sincronizza) return inCorso;
  const prima = inCorso ?? Promise.resolve();
  const run: Promise<void> = prima.then(() => leggi(sincronizza)).finally(() => {
    if (inCorso === run) inCorso = null;
  });
  inCorso = run;
  return run;
}

export function useAbbonamento(): { dati: StatoApi | null; ricarica: (sincronizza?: boolean) => Promise<void> } {
  const [stato, setStato] = useState<StatoApi | null>(dati);
  useEffect(() => {
    const f = () => setStato(dati);
    ascoltatori.add(f);
    f();
    if (!dati) void ricaricaAbbonamento();
    const visibile = () => {
      if (document.visibilityState === "visible" && Date.now() - letto > RILEGGI_DOPO_MS) void ricaricaAbbonamento();
    };
    document.addEventListener("visibilitychange", visibile);
    return () => {
      ascoltatori.delete(f);
      document.removeEventListener("visibilitychange", visibile);
    };
  }, []);
  return { dati: stato, ricarica: ricaricaAbbonamento };
}
