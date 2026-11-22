"use client";

// L'ora del Mac per le righe che contano i giorni (conto alla rovescia, fascia): si rilegge una volta al minuto.
// Il valore resta fermo tra un minuto e l'altro (useSyncExternalStore lo vuole stabile); sul server vale 0.
import { useSyncExternalStore } from "react";

const MINUTO = 60_000;
let ultima = Date.now();

function ascolta(cambia: () => void) {
  ultima = Date.now(); // all'aggancio React rilegge il valore e ridisegna se è cambiato
  const t = setInterval(() => {
    ultima = Date.now();
    cambia();
  }, MINUTO);
  return () => clearInterval(t);
}

export function useOra(): number {
  return useSyncExternalStore(ascolta, () => ultima, () => 0);
}
