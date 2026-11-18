"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { abilitaSalvataggioLocale, STORE_SCHEMA, useStore } from "@/lib/store";
import { avviaVuotoPrimaDelSync, startSync, syncAvviata } from "@/lib/sync";
import { BloccoInattivita } from "./BloccoInattivita";
import { caricaSessione } from "@/lib/accesso/client";
import { percorsoNegozio, percorsoPiattaforma, percorsoPubblico } from "@/lib/accesso/percorsi";
import type { Accesso } from "@/lib/accesso/regole";

// Nome da mostrare per chi usa il dispositivo: dal collegamento a PIN il dispositivo ha un nome, altrimenti "Browser"
const operatoreDa = (a: Accesso) => ({ nome: a.utente.nome, dispositivo: a.dispositivo?.nome ?? "Browser", assistenza: !!a.assistenza });

const RICARICA_CATALOGO_MS = 30_000;
// Il catalogo pubblico è nello store di questa pagina: lo store non va più usato per la gestione senza ricaricare
let catalogoNelloStore = false;

async function caricaCatalogo(): Promise<void> {
  try {
    const r = await fetch("/api/negozio/catalogo", { cache: "no-store" });
    if (!r.ok) return;
    const c = (await r.json()) as { annunci?: unknown; parts?: unknown; vehicles?: unknown };
    if (!Array.isArray(c.annunci) || !Array.isArray(c.parts) || !Array.isArray(c.vehicles)) return;
    // Solo i tre elenchi del catalogo, e solo in memoria: niente copia locale, niente sincronizzazione
    useStore.setState({ annunci: c.annunci, parts: c.parts, vehicles: c.vehicles } as unknown as Partial<ReturnType<typeof useStore.getState>>);
    catalogoNelloStore = true;
  } catch {
    // server non raggiungibile: resta l'ultimo catalogo caricato
  }
}

export function Hydrator({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  // Sessione da PIN: blocco dopo 5 minuti senza tocchi su OGNI pagina della gestione (anche quelle di stampa)
  const [pin, setPin] = useState(false);
  const path = usePathname();
  // Le pagine pubbliche (accesso, negozio, eBay simulato, ...) non toccano i dati della gestione:
  // niente salvataggio nel browser e niente sincronizzazione con l'archivio di un'azienda.
  // L'area Piattaforma del super admin non è di nessuna azienda: stessa cosa (l'accesso lo chiede il proxy).
  const pubblica = percorsoPubblico(path) || percorsoPiattaforma(path);
  // Negozio ed eBay simulato: niente archivio dell'azienda, solo il catalogo pubblico dal server
  const negozio = percorsoNegozio(path);
  const [catalogoPronto, setCatalogoPronto] = useState(false);

  useEffect(() => {
    if (negozio) {
      abilitaSalvataggioLocale(false);
      // Arrivati qui dalla gestione senza ricaricare: la sincronizzazione è già attiva e spedirebbe il catalogo come modifiche
      if (syncAvviata()) {
        window.location.reload();
        return;
      }
      let attivo = true;
      useStore.setState({ annunci: [], parts: [], vehicles: [] });
      const giro = () => void caricaCatalogo();
      void caricaCatalogo().finally(() => attivo && setCatalogoPronto(true));
      const t = setInterval(giro, RICARICA_CATALOGO_MS);
      return () => {
        attivo = false;
        clearInterval(t);
      };
    }
    if (pubblica) {
      abilitaSalvataggioLocale(false);
      return;
    }
    // Tornati alla gestione dal negozio senza ricaricare: lo store ha il catalogo pubblico al posto dell'archivio
    if (catalogoNelloStore) {
      window.location.reload();
      return;
    }
    let attivo = true;
    let unsub: () => void = () => {};
    (async () => {
      const e = await caricaSessione();
      if (!attivo) return;
      if (!e.ok) {
        // Senza sessione valida si torna all'accesso
        window.location.assign(`/accesso?da=${encodeURIComponent(window.location.pathname + window.location.search)}`);
        return;
      }
      setPin(e.accesso.tipo === "pin");
      const chiave = `${STORE_SCHEMA}:${e.accesso.azienda.id}`;
      // Prima la chiave dell'azienda, poi ogni altra scrittura: niente può finire nella chiave sbagliata
      useStore.persist.setOptions({ name: chiave });
      abilitaSalvataggioLocale(true);
      let copiaLocale: string | null = null;
      try {
        localStorage.removeItem(STORE_SCHEMA); // vecchia chiave senza azienda
        copiaLocale = localStorage.getItem(chiave);
      } catch {}
      useStore.getState().setSessione(operatoreDa(e.accesso), e.accesso.ruoli);
      // Azienda vera senza copia locale: si parte da un archivio vuoto, mai dai dati demo
      // (solo prima che la sincronizzazione parta: dopo, un archivio vuoto locale finirebbe sul server)
      if (!e.accesso.azienda.demo && !copiaLocale) avviaVuotoPrimaDelSync();
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
  }, [pubblica, negozio]);

  if (negozio && !catalogoPronto) {
    return (
      <div className="grid min-h-dvh place-items-center bg-ground">
        <div className="code text-2xl font-semibold tracking-wide text-band">CARICAMENTO…</div>
      </div>
    );
  }
  if (!pubblica && !ready) {
    return (
      <div className="grid min-h-dvh place-items-center bg-ground">
        <div className="code text-2xl font-semibold tracking-wide text-band">CARICAMENTO…</div>
      </div>
    );
  }
  return (
    <>
      {!pubblica && <BloccoInattivita attivo={pin} />}
      {children}
    </>
  );
}
