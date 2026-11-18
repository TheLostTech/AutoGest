"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { STORE_SCHEMA, useStore } from "@/lib/store";
import { startSync } from "@/lib/sync";
import { caricaSessione } from "@/lib/accesso/client";
import { percorsoPubblico } from "@/lib/accesso/percorsi";
import type { Accesso } from "@/lib/accesso/regole";

// Nome da mostrare per chi usa il dispositivo: dal collegamento a PIN il dispositivo ha un nome, altrimenti "Browser"
const operatoreDa = (a: Accesso) => ({ nome: a.utente.nome, dispositivo: a.dispositivo?.nome ?? "Browser", assistenza: !!a.assistenza });

export function Hydrator({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const path = usePathname();
  // La pagina di accesso non ha bisogno dei dati; le altre pagine pubbliche (negozio, eBay simulato) restano come prima.
  const soloAccesso = path === "/accesso" || path.startsWith("/accesso/");
  const pubblica = percorsoPubblico(path);

  useEffect(() => {
    if (soloAccesso) return;
    let attivo = true;
    let unsub: () => void = () => {};
    (async () => {
      if (!pubblica) {
        const e = await caricaSessione();
        if (!attivo) return;
        if (!e.ok) {
          // Senza sessione valida si torna all'accesso
          window.location.assign(`/accesso?da=${encodeURIComponent(window.location.pathname + window.location.search)}`);
          return;
        }
        // Prima chi è e quali ruoli ha, poi i dati salvati nel browser di QUESTA azienda
        useStore.getState().setSessione(operatoreDa(e.accesso), e.accesso.ruoli);
        useStore.persist.setOptions({ name: `${STORE_SCHEMA}:${e.accesso.azienda.id}` });
      }
      // Prima i dati salvati nel browser, poi l'allineamento con gli altri dispositivi (al massimo 2 secondi)
      const done = () => void startSync().finally(() => attivo && setReady(true));
      unsub = useStore.persist.onFinishHydration(done);
      try {
        void useStore.persist.rehydrate();
      } catch {
        done();
      }
      if (useStore.persist.hasHydrated()) done();
    })();
    return () => {
      attivo = false;
      unsub();
    };
  }, [soloAccesso, pubblica]);

  if (soloAccesso) return <>{children}</>;
  if (!ready) {
    return (
      <div className="grid min-h-dvh place-items-center bg-ground">
        <div className="code text-2xl font-semibold tracking-wide text-band">CARICAMENTO…</div>
      </div>
    );
  }
  return <>{children}</>;
}
