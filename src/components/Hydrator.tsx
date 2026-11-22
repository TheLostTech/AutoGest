"use client";

import { Suspense, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { useStore } from "@/lib/store";
import { startSync } from "@/lib/sync";

const Caricamento = () => (
  <div className="grid min-h-dvh place-items-center bg-ground">
    <div className="code text-2xl font-semibold tracking-wide text-band">CARICAMENTO…</div>
  </div>
);

// usePathname nelle pagine con indirizzo variabile (/veicoli/[id]…) si legge solo nel browser:
// senza Suspense la compilazione si ferma. Le pagine fisse (presentazione, news) restano scritte dal server.
export function Hydrator({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<Caricamento />}>
      <Allinea>{children}</Allinea>
    </Suspense>
  );
}

function Allinea({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  // La pagina di presentazione è pubblica: non legge né allinea i dati del gestionale
  const percorso = usePathname();
  const pubblica = percorso === "/scopri" || percorso.startsWith("/news");
  useEffect(() => {
    if (pubblica) return;
    // Prima i dati salvati nel browser, poi l'allineamento con gli altri dispositivi (al massimo 2 secondi)
    const done = () => void startSync().finally(() => setReady(true));
    const unsub = useStore.persist.onFinishHydration(done);
    try {
      void useStore.persist.rehydrate();
    } catch {
      done();
    }
    if (useStore.persist.hasHydrated()) done();
    return unsub;
  }, [pubblica]);
  if (!ready && !pubblica) return <Caricamento />;
  return <>{children}</>;
}
