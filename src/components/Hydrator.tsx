"use client";

import { useEffect, useState } from "react";
import { useStore } from "@/lib/store";

export function Hydrator({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const done = () => setReady(true);
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
