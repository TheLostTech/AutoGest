"use client";

import { useEffect, useState } from "react";
import { useStore } from "@/lib/store";
import { startSync } from "@/lib/sync";

export function Hydrator({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  useEffect(() => {
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
  }, []);
  if (!ready) {
    return (
      <div className="grid min-h-dvh place-items-center bg-ground">
        <div className="code text-2xl font-semibold tracking-wide text-band">CARICAMENTO…</div>
      </div>
    );
  }
  return <>{children}</>;
}
