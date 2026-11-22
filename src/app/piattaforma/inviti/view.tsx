"use client";

import { useCallback, useEffect, useState } from "react";
import { Copy } from "lucide-react";
import { Button, Empty, Field, Notice, PageTitle, Panel } from "@/components/ui";
import { chiama } from "../comune";

type Stato = "valido" | "usato" | "scaduto";
type Invito = { id: string; nota: string; creato: string; scade: string; stato: Stato; azienda: string | null };
type Nuovo = { codice: string; link: string; scade: string };

const giorno = (iso: string) => new Date(iso).toLocaleDateString("it-IT", { day: "numeric", month: "short", year: "numeric" });
const ETICHETTA: Record<Stato, string> = { valido: "Valido", usato: "Usato", scaduto: "Scaduto" };

export default function Inviti() {
  const [inviti, setInviti] = useState<Invito[] | null>(null);
  const [nota, setNota] = useState("");
  const [nuovo, setNuovo] = useState<Nuovo | null>(null);
  const [errore, setErrore] = useState("");
  const [attesa, setAttesa] = useState(false);
  const [copiato, setCopiato] = useState(false);

  const carica = useCallback(async () => {
    const r = await chiama<{ inviti: Invito[] }>("/api/piattaforma/inviti");
    if (r.ok) setInviti(r.dati.inviti);
    else setErrore(r.messaggio);
  }, []);
  useEffect(() => {
    // Lettura iniziale dal server al caricamento della pagina
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void carica();
  }, [carica]);

  async function crea(ev: React.FormEvent) {
    ev.preventDefault();
    setAttesa(true);
    setErrore("");
    setCopiato(false);
    const r = await chiama<Nuovo>("/api/piattaforma/inviti", { method: "POST", corpo: { nota } });
    setAttesa(false);
    if (!r.ok) {
      setErrore(r.messaggio);
      return;
    }
    setNuovo(r.dati);
    setNota("");
    void carica();
  }

  async function copia() {
    if (!nuovo) return;
    try {
      await navigator.clipboard.writeText(`${window.location.origin}${nuovo.link}`);
      setCopiato(true);
    } catch {
      setErrore("Non sono riuscito a copiare: seleziona il link e copialo a mano.");
    }
  }

  return (
    <div>
      <PageTitle title="Inviti" sub="Finché i pagamenti sono in prova ci si registra solo con un codice invito: vale 30 giorni e si usa una volta sola." />
      {errore && (
        <div role="alert" className="mb-4">
          <Notice tone="danger">{errore}</Notice>
        </div>
      )}

      <form onSubmit={crea} className="space-y-4 rounded-md border border-hair bg-label p-4">
        <Field label="Nota (facoltativa)" hint="Per ricordarti a chi lo dai. Non la vede nessun altro.">
          <input className="field" value={nota} onChange={(e) => setNota(e.target.value)} maxLength={120} />
        </Field>
        <Button type="submit" disabled={attesa}>
          {attesa ? "Creo…" : "Crea invito"}
        </Button>
      </form>

      {nuovo && (
        <div className="mt-4 space-y-3 rounded-md border border-hair bg-label p-4" role="status">
          <p className="font-bold text-ink">Invito creato</p>
          <p className="code text-2xl font-bold tracking-wider text-band-deep">{nuovo.codice}</p>
          <p className="break-all text-sm text-ink-2" data-testid="link-invito">
            {typeof window !== "undefined" ? window.location.origin : ""}
            {nuovo.link}
          </p>
          <Button type="button" variant="secondary" onClick={() => void copia()}>
            <Copy className="size-4" aria-hidden />
            {copiato ? "Link copiato" : "Copia link"}
          </Button>
          <Notice tone="warn">Il codice si vede solo adesso: non sarà più mostrato. Copia il link prima di lasciare la pagina. Scade il {giorno(nuovo.scade)}.</Notice>
        </div>
      )}

      <div className="mt-6">
        {!inviti && !errore && <p className="text-ink-2">Carico gli inviti…</p>}
        {inviti && inviti.length === 0 && <Empty title="Nessun invito">Creane uno con «Crea invito».</Empty>}
        {inviti && inviti.length > 0 && (
          <Panel>
            <ul className="divide-y divide-hair-soft">
              {inviti.map((i) => (
                <li key={i.id} className="flex flex-wrap items-center gap-3 px-4 py-3.5">
                  <span className="min-w-48 flex-1">
                    <span className="block font-semibold text-ink">{i.nota || "Senza nota"}</span>
                    <span className="block text-sm text-ink-2">
                      Creato il {giorno(i.creato)} · scade il {giorno(i.scade)}
                      {i.azienda ? ` · usato da ${i.azienda}` : ""}
                    </span>
                  </span>
                  <span className={`rounded-md px-2 py-1 text-sm font-semibold ${i.stato === "valido" ? "bg-band-tint text-band-deep" : "bg-carton text-ink-2"}`}>{ETICHETTA[i.stato]}</span>
                </li>
              ))}
            </ul>
          </Panel>
        )}
      </div>
    </div>
  );
}
