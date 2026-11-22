"use client";

import { annunciaAziendaSessione } from "@/lib/accesso/azienda-client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { Building2, LogOut, Mail, ShieldCheck } from "lucide-react";
import { authClient } from "@/lib/auth/client";
import type { ModalitaStripe } from "@/lib/stripe/chiavi";
import { Button, Notice } from "@/components/ui";

export type StatoPiattaforma = {
  utente: { id: string; nome: string; email: string };
  dueFattoriAttivo: boolean;
  dueFattoriVerificato: boolean;
  aziendaAttiva: string | null;
  assistenzaMinuti: number;
  stripe: ModalitaStripe;
};

const Contesto = createContext<{ stato: StatoPiattaforma; ricarica: () => Promise<void> } | null>(null);

export function usePiattaforma() {
  const c = useContext(Contesto);
  if (!c) throw new Error("fuori dall'area Piattaforma");
  return c;
}

/** Chiamata alle API della piattaforma: JSON dentro e fuori; l'errore è il messaggio da mostrare. */
export async function chiama<T = Record<string, unknown>>(url: string, opzioni: { method?: string; corpo?: unknown } = {}): Promise<{ ok: true; dati: T } | { ok: false; messaggio: string; stato: number }> {
  try {
    const r = await fetch(url, {
      method: opzioni.method ?? "GET",
      headers: opzioni.corpo !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: opzioni.corpo !== undefined ? JSON.stringify(opzioni.corpo) : undefined,
      cache: "no-store",
    });
    const j = (await r.json().catch(() => ({}))) as T & { error?: string };
    if (!r.ok) return { ok: false, messaggio: j.error ?? "Operazione non riuscita. Riprova.", stato: r.status };
    return { ok: true, dati: j };
  } catch {
    return { ok: false, messaggio: "Non riesco a contattare il server. Riprova.", stato: 0 };
  }
}

export function Guscio({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [stato, setStato] = useState<StatoPiattaforma | null>(null);
  const [rifiuto, setRifiuto] = useState<string | null>(null);

  const ricarica = useCallback(async () => {
    const r = await chiama<StatoPiattaforma>("/api/piattaforma/stato");
    if (r.ok) {
      setStato(r.dati);
      setRifiuto(null);
    } else if (r.stato === 401) {
      window.location.assign(`/accesso?da=${encodeURIComponent(window.location.pathname)}`);
    } else {
      setRifiuto(r.messaggio);
    }
  }, []);
  useEffect(() => {
    // Lettura iniziale dal server al caricamento della pagina
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void ricarica();
  }, [ricarica]);

  async function esci() {
    // L'uscita dall'account chiude anche l'ingresso di assistenza aperto (lo registra il server); le altre schede lo sanno subito
    await authClient.signOut().catch(() => undefined);
    annunciaAziendaSessione(null);
    window.location.assign("/accesso");
  }

  if (rifiuto) {
    return (
      <main className="mx-auto max-w-xl px-4 py-16">
        <Notice tone="warn">{rifiuto}</Notice>
        <div className="mt-4">
          <Button variant="secondary" onClick={() => void esci()}>
            Esci
          </Button>
        </div>
      </main>
    );
  }
  if (!stato) return <main className="grid min-h-dvh place-items-center bg-ground" aria-busy="true" />;

  const nav = [
    { href: "/piattaforma", nome: "Aziende", icona: Building2, attivo: path === "/piattaforma" || path.startsWith("/piattaforma/aziende") || path === "/piattaforma/nuova" },
    { href: "/piattaforma/inviti", nome: "Inviti", icona: Mail, attivo: path === "/piattaforma/inviti" },
    { href: "/piattaforma/sicurezza", nome: "Sicurezza", icona: ShieldCheck, attivo: path === "/piattaforma/sicurezza" },
  ];
  const aSicurezza = path === "/piattaforma/sicurezza";

  return (
    <Contesto.Provider value={{ stato, ricarica }}>
      <div className="min-h-dvh bg-ground">
        <header className="border-b border-hair bg-label">
          <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
            <p className="code text-lg font-bold tracking-wide text-band">PIATTAFORMA</p>
            <nav className="flex flex-1 gap-1" aria-label="Piattaforma">
              {nav.map((n) => (
                <Link
                  key={n.href}
                  href={n.href}
                  aria-current={n.attivo ? "page" : undefined}
                  className={`inline-flex min-h-10 items-center gap-2 rounded-md px-3 font-semibold ${n.attivo ? "bg-band-tint text-band-deep" : "text-ink-2 hover:bg-carton"}`}
                >
                  <n.icona className="size-4" aria-hidden />
                  {n.nome}
                </Link>
              ))}
            </nav>
            <span className="text-sm text-ink-2">{stato.utente.nome}</span>
            <Button variant="quiet" size="sm" onClick={() => void esci()}>
              <LogOut className="size-4" aria-hidden />
              Esci
            </Button>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-4 py-8">
          {!stato.dueFattoriVerificato && !aSicurezza ? (
            <Notice tone="warn">
              Per usare la piattaforma serve il codice dal telefono. {stato.dueFattoriAttivo ? "Esci e accedi di nuovo con il codice." : <>Attivalo nella pagina <Link href="/piattaforma/sicurezza" className="font-bold underline">Sicurezza</Link>.</>}
            </Notice>
          ) : (
            children
          )}
        </main>
      </div>
    </Contesto.Provider>
  );
}
