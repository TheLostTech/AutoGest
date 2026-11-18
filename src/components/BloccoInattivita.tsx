"use client";

import { useEffect, useRef, useState } from "react";
import { esci } from "@/lib/accesso/client";
import { PIN_INATTIVITA_MS } from "@/lib/accesso/regole";

// Sessione da PIN (tablet del piazzale): dopo 5 minuti senza tocchi né tasti il dispositivo prova a inviare le
// modifiche in sospeso, chiude la sessione e torna all'elenco dei nomi. Si misura con l'orologio, non con un
// timer solo: un tablet che si risveglia dallo standby si blocca subito.
const EVENTI = ["pointerdown", "keydown", "touchstart", "wheel"] as const;

export function BloccoInattivita({ attivo }: { attivo: boolean }) {
  const ultimo = useRef(0);
  const [blocco, setBlocco] = useState(false);

  useEffect(() => {
    if (!attivo) return;
    ultimo.current = Date.now();
    let fatto = false;
    const tocco = () => {
      ultimo.current = Date.now();
    };
    const controlla = () => {
      if (fatto || Date.now() - ultimo.current < PIN_INATTIVITA_MS) return;
      fatto = true;
      setBlocco(true);
      void esci();
    };
    for (const e of EVENTI) window.addEventListener(e, tocco, { passive: true, capture: true });
    document.addEventListener("visibilitychange", controlla);
    const t = setInterval(controlla, 5_000);
    return () => {
      for (const e of EVENTI) window.removeEventListener(e, tocco, { capture: true });
      document.removeEventListener("visibilitychange", controlla);
      clearInterval(t);
    };
  }, [attivo]);

  if (!blocco) return null;
  return (
    <div role="status" className="fixed inset-0 z-[100] grid place-items-center bg-ink/80 px-6 text-center text-white">
      <div>
        <p className="code text-[22px] font-bold uppercase tracking-wide">Dispositivo bloccato</p>
        <p className="mt-2 text-[16px] text-white/85">Nessun tocco da 5 minuti: salvo il lavoro e torno all&apos;elenco dei nomi…</p>
      </div>
    </div>
  );
}
