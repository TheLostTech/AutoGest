"use client";

// Stato dell'abbonamento nel browser, da GET /api/abbonamento/stato: una copia sola per la pagina, condivisa da
// AppShell (riquadro di pagamento), pagina Abbonamento e ritorno da Checkout.
import { useEffect, useState } from "react";
import type { Abbonamento, Conto } from "./abbonamento";
import type { ModalitaStripe } from "./stripe/chiavi";
import { fetchAzienda } from "./accesso/azienda-client";
import { intestazioniPassive } from "./accesso/attivita";

// orologioPronto: solo con controllaOrologio (strumenti di prova); altrimenti null
export type StatoApi = { abbonamento: Abbonamento | null; registrata: boolean; modalita: ModalitaStripe; conto: Conto | null; orologioPronto: boolean | null };

let dati: StatoApi | null = null;
let letto = 0; // quando è arrivata l'ultima risposta (ms)
let inCorso: Promise<void> | null = null;
const ascoltatori = new Set<() => void>();
// Tornando sulla scheda si rilegge, ma non più di una volta ogni 30 secondi
const RILEGGI_DOPO_MS = 30_000;

async function leggi(parametri: string): Promise<StatoApi | null> {
  try {
    // Lettura automatica: per una sessione da PIN non conta come attività della persona
    const r = await fetchAzienda(`/api/abbonamento/stato${parametri}`, { cache: "no-store", headers: intestazioniPassive() });
    if (!r.ok) return null;
    const nuovi = (await r.json()) as StatoApi;
    dati = nuovi;
    letto = Date.now();
    ascoltatori.forEach((f) => f());
    return nuovi;
  } catch {
    // server non raggiungibile: resta l'ultimo stato letto
    return null;
  }
}

/**
 * Strumenti di prova: rilegge lo stato con quello dell'orologio di prova (`orologioPronto`). Non passa dal limite dei
 * 15 secondi di ricarica(true): il server sincronizza da solo, una volta, quando l'orologio torna pronto. null se il
 * server non risponde. Aggiorna la copia condivisa come le altre letture.
 */
export function controllaOrologio(): Promise<StatoApi | null> {
  return leggi("?orologio=1");
}

/** Rilegge lo stato; con `sincronizza` il server lo chiede prima a Stripe (al massimo una volta ogni 15 secondi). */
export function ricaricaAbbonamento(sincronizza = false): Promise<void> {
  // Una lettura semplice già in corso basta; una con sincronizzazione parte comunque dopo
  if (inCorso && !sincronizza) return inCorso;
  const prima = inCorso ?? Promise.resolve();
  const run: Promise<void> = prima.then(async () => void (await leggi(sincronizza ? "?sincronizza=1" : ""))).finally(() => {
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
