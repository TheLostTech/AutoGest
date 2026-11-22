"use client";

import { Suspense, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { abilitaSalvataggioLocale, STORE_SCHEMA, useStore } from "@/lib/store";
import { avviaVuotoPrimaDelSync, startSync, syncAvviata } from "@/lib/sync";
import { BloccoInattivita } from "./BloccoInattivita";
import { caricaSessione } from "@/lib/accesso/client";
import { percorsoNegozio, percorsoPiattaforma, percorsoPubblico } from "@/lib/accesso/percorsi";
import type { Accesso } from "@/lib/accesso/regole";
import { aziendaDaAnnuncio, aziendaFissata, fissaAzienda, segnalaAziendaCambiata } from "@/lib/accesso/azienda-client";
import { chiaviDaTogliere } from "@/lib/accesso/copie-locali";

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
      // Blocco dopo 5 minuti: sessione da PIN, o qualunque sessione su un dispositivo condiviso (es. il responsabile sul tablet)
      setPin(e.accesso.tipo === "pin" || e.accesso.dispositivoCondiviso === true);
      // Questa scheda resta di questa azienda: ogni chiamata alle API lo dice al server (x-azienda)
      fissaAzienda(e.accesso.azienda.id);
      const chiave = `${STORE_SCHEMA}:${e.accesso.azienda.id}`;
      // Prima la chiave dell'azienda, poi ogni altra scrittura: niente può finire nella chiave sbagliata
      useStore.persist.setOptions({ name: chiave });
      abilitaSalvataggioLocale(true);
      let copiaLocale: string | null = null;
      try {
        localStorage.removeItem(STORE_SCHEMA); // vecchia chiave senza azienda
        // Cambio di azienda: le copie locali delle altre aziende si tolgono (restano solo le loro modifiche in sospeso)
        const tutte: string[] = [];
        for (let i = 0; i < localStorage.length; i++) {
          const k = localStorage.key(i);
          if (k) tutte.push(k);
        }
        for (const k of chiaviDaTogliere(tutte, STORE_SCHEMA, e.accesso.azienda.id)) localStorage.removeItem(k);
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
    // Un'altra scheda ha cambiato l'azienda della sessione (ingresso o uscita di assistenza): questa scheda si ferma
    // (le modifiche non inviate restano in sospeso per questa azienda) e si ricarica con l'azienda nuova.
    const daAltraScheda = (ev: StorageEvent) => {
      const nuova = aziendaDaAnnuncio(ev);
      if (nuova === undefined || !aziendaFissata() || nuova === aziendaFissata()) return;
      segnalaAziendaCambiata();
      window.location.reload();
    };
    window.addEventListener("storage", daAltraScheda);
    return () => {
      attivo = false;
      unsub();
      window.removeEventListener("storage", daAltraScheda);
    };
  }, [pubblica, negozio]);

  if (negozio && !catalogoPronto) return <Caricamento />;
  if (!pubblica && !ready) return <Caricamento />;
  return (
    <>
      {!pubblica && <BloccoInattivita attivo={pin} />}
      {children}
    </>
  );
}
