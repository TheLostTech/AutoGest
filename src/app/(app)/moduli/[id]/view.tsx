"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { ModuloBloccato } from "@/components/ModuloBloccato";
import { useModuli } from "@/lib/use-moduli";
import type { Modulo } from "@/lib/moduli";

// Dove si lavora con un modulo già attivo (la pratica sta nella scheda di ogni veicolo)
const PRIMA_PAGINA: Record<Modulo, string> = { magazzino: "/", accettazione: "/veicoli", ambiente: "/ambiente", vendite: "/vendite" };

export default function ModuloView({ modulo }: { modulo: Modulo }) {
  const moduli = useModuli();
  const router = useRouter();
  const aperto = moduli.has(modulo);
  useEffect(() => {
    if (aperto) router.replace(PRIMA_PAGINA[modulo]);
  }, [aperto, modulo, router]);
  return aperto ? null : <ModuloBloccato modulo={modulo} />;
}
