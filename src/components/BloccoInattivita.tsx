"use client";

import { useEffect, useState } from "react";
import { esci } from "@/lib/accesso/client";
import { BATTITO_OGNI_MS, CHIAVE_BLOCCO, CHIAVE_ULTIMO_TOCCO } from "@/lib/accesso/attivita";
import { PIN_INATTIVITA_MS } from "@/lib/accesso/regole";

// Sessione da PIN (tablet del piazzale): dopo 5 minuti senza tocchi né tasti il dispositivo prova a inviare le
// modifiche in sospeso, chiude la sessione e torna all'elenco dei nomi.
// - Vale in ogni pagina della gestione, anche quelle di stampa aperte in un'altra scheda (montato da Hydrator).
// - L'ultimo tocco è condiviso fra le schede (localStorage): un tocco in una scheda vale per tutte, e quando una
//   scheda si blocca le altre la seguono subito (evento `storage`).
// - Si misura con l'orologio, non con un timer solo: un tablet che si risveglia dallo standby si blocca subito.
// - Il server non conta le letture automatiche: i tocchi veri gli arrivano con un battito, al massimo uno al minuto.
const EVENTI = ["pointerdown", "keydown", "touchstart", "wheel"] as const;
const MARGINE_MS = 5_000;

function leggi(chiave: string): number {
  try {
    return Number(localStorage.getItem(chiave)) || 0;
  } catch {
    return 0;
  }
}
function scrivi(chiave: string, t: number) {
  try {
    localStorage.setItem(chiave, String(t));
  } catch {}
}

export function BloccoInattivita({ attivo }: { attivo: boolean }) {
  const [blocco, setBlocco] = useState(false);

  useEffect(() => {
    if (!attivo) return;
    // Aprire una pagina è un'azione della persona (e la sua lettura della sessione conta già sul server)
    let ultimo = Date.now();
    let scritto = ultimo;
    let battito = ultimo;
    scrivi(CHIAVE_ULTIMO_TOCCO, ultimo);
    let fatto = false;

    const blocca = (avvisaLeAltre: boolean) => {
      if (fatto) return;
      fatto = true;
      if (avvisaLeAltre) scrivi(CHIAVE_BLOCCO, Date.now());
      setBlocco(true);
      void esci();
    };
    // Battito al massimo uno al minuto; i tocchi arrivati nel frattempo partono con un battito "in coda" alla fine
    // del minuto, con l'istante dell'ultimo tocco: così il server scade insieme allo schermo, non prima.
    let inCoda: ReturnType<typeof setTimeout> | undefined;
    let mandato = ultimo;
    const manda = () => {
      inCoda = undefined;
      if (fatto || ultimo <= mandato) return;
      battito = Date.now();
      mandato = ultimo;
      void fetch("/api/sessione/attivita", {
        method: "POST",
        cache: "no-store",
        keepalive: true,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ultimoTocco: ultimo }),
      }).catch(() => undefined);
    };
    const tocco = () => {
      const t = Date.now();
      ultimo = t;
      if (t - scritto > 1_000) {
        scritto = t;
        scrivi(CHIAVE_ULTIMO_TOCCO, t);
      }
      if (t - battito >= BATTITO_OGNI_MS) manda();
      else inCoda ??= setTimeout(manda, battito + BATTITO_OGNI_MS - t);
    };
    // Lo schermo si blocca qualche secondo prima del server, così vince sempre il blocco ordinato (lavoro salvato)
    const controlla = () => {
      if (!fatto && Date.now() - Math.max(ultimo, leggi(CHIAVE_ULTIMO_TOCCO)) >= PIN_INATTIVITA_MS - MARGINE_MS) blocca(true);
    };
    const daAltraScheda = (e: StorageEvent) => {
      if (e.key === CHIAVE_BLOCCO && e.newValue) blocca(false);
    };

    for (const e of EVENTI) window.addEventListener(e, tocco, { passive: true, capture: true });
    window.addEventListener("storage", daAltraScheda);
    document.addEventListener("visibilitychange", controlla);
    const t = setInterval(controlla, 1_000);
    return () => {
      clearTimeout(inCoda);
      for (const e of EVENTI) window.removeEventListener(e, tocco, { capture: true });
      window.removeEventListener("storage", daAltraScheda);
      document.removeEventListener("visibilitychange", controlla);
      clearInterval(t);
    };
  }, [attivo]);

  if (!blocco) return null;
  return (
    <div role="status" className="no-print fixed inset-0 z-[100] grid place-items-center bg-ink/80 px-6 text-center text-white">
      <div>
        <p className="code text-[22px] font-bold uppercase tracking-wide">Dispositivo bloccato</p>
        <p className="mt-2 text-[16px] text-white/85">Nessun tocco da 5 minuti: salvo il lavoro e torno all&apos;elenco dei nomi…</p>
      </div>
    </div>
  );
}
