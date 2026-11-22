"use client";

import { useMemo } from "react";
import { useStore } from "./store";
import { moduliAttivi, type Modulo } from "./moduli";

/** Moduli attivi dell'azienda, per le schermate */
export function useModuli(): Set<Modulo> {
  const stato = useStore((s) => s.moduli);
  return useMemo(() => moduliAttivi(stato), [stato]);
}
