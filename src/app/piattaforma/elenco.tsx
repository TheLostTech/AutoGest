"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { LifeBuoy, Plus } from "lucide-react";
import { Button, ButtonLink, Empty, Field, Notice, PageTitle, Panel } from "@/components/ui";
import { chiama, usePiattaforma } from "./comune";

type Azienda = { id: string; nome: string; demo: boolean; utenti: number; ultimoAccesso: string | null };

const quando = (iso: string | null) => (iso ? new Date(iso).toLocaleString("it-IT", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "mai");

export default function ElencoAziende() {
  const { stato } = usePiattaforma();
  const [aziende, setAziende] = useState<Azienda[] | null>(null);
  const [errore, setErrore] = useState("");
  const [entra, setEntra] = useState<Azienda | null>(null);
  const [motivo, setMotivo] = useState("");
  const [attesa, setAttesa] = useState(false);

  const carica = useCallback(async () => {
    const r = await chiama<{ aziende: Azienda[] }>("/api/piattaforma/aziende");
    if (r.ok) setAziende(r.dati.aziende);
    else setErrore(r.messaggio);
  }, []);
  useEffect(() => {
    // Lettura iniziale dal server al caricamento della pagina
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void carica();
  }, [carica]);

  const puoiEntrare = stato.dueFattoriVerificato;

  async function conferma(ev: React.FormEvent) {
    ev.preventDefault();
    if (!entra) return;
    setAttesa(true);
    setErrore("");
    const r = await chiama("/api/piattaforma/assistenza", { method: "POST", corpo: { aziendaId: entra.id, motivo } });
    if (!r.ok) {
      setErrore(r.messaggio);
      setAttesa(false);
      return;
    }
    // Navigazione completa: la gestione parte da zero con i dati dell'azienda
    window.location.assign("/");
  }

  return (
    <div>
      <PageTitle
        title="Aziende"
        sub="Le aziende che usano la piattaforma. Da qui crei le aziende, gestisci chi può entrare e, se serve aiuto, entri per assistenza."
        actions={
          <ButtonLink href="/piattaforma/nuova">
            <Plus className="size-5" aria-hidden />
            Nuova azienda
          </ButtonLink>
        }
      />
      {errore && (
        <div role="alert" className="mb-4">
          <Notice tone="danger">{errore}</Notice>
        </div>
      )}
      {!puoiEntrare && <Notice tone="warn">L&apos;ingresso per assistenza è disattivato finché il codice dal telefono non è attivo e verificato.</Notice>}

      {entra && (
        <form onSubmit={conferma} className="my-4 space-y-4 rounded-md border border-hair bg-label p-4">
          <h2 className="text-[20px] font-bold text-ink">Entra per assistenza in «{entra.nome}»</h2>
          <Field label="Motivo dell'ingresso" hint={`Resta nel registro dell'azienda. L'ingresso dura ${stato.assistenzaMinuti / 60} ore.`}>
            <input className="field" value={motivo} onChange={(e) => setMotivo(e.target.value)} minLength={3} maxLength={300} required autoFocus />
          </Field>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={attesa || motivo.trim().length < 3}>
              {attesa ? "Entro…" : "Entra"}
            </Button>
            <Button type="button" variant="quiet" onClick={() => setEntra(null)}>
              Annulla
            </Button>
          </div>
        </form>
      )}

      <div className="mt-4">
        {!aziende && !errore && <p className="text-ink-2">Carico le aziende…</p>}
        {aziende && aziende.length === 0 && <Empty title="Nessuna azienda">Crea la prima con «Nuova azienda».</Empty>}
        {aziende && aziende.length > 0 && (
          <Panel>
            <ul className="divide-y divide-hair-soft">
              {aziende.map((a) => (
                <li key={a.id} className="flex flex-wrap items-center gap-3 px-4 py-3.5">
                  <span className="min-w-48 flex-1">
                    <Link href={`/piattaforma/aziende/${a.id}`} className="block font-semibold text-band hover:underline">
                      {a.nome}
                    </Link>
                    <span className="block text-sm text-ink-2">
                      {a.utenti} {a.utenti === 1 ? "utente" : "utenti"} · ultimo accesso: {quando(a.ultimoAccesso)}
                      {a.demo ? " · dati di prova" : ""}
                    </span>
                  </span>
                  <ButtonLink href={`/piattaforma/aziende/${a.id}`} variant="secondary" size="sm">
                    Utenti e dispositivi
                  </ButtonLink>
                  <Button size="sm" variant="secondary" disabled={!puoiEntrare} title={puoiEntrare ? undefined : "Serve il codice dal telefono"} onClick={() => { setEntra(a); setMotivo(""); setErrore(""); }}>
                    <LifeBuoy className="size-4" aria-hidden />
                    Entra per assistenza
                  </Button>
                </li>
              ))}
            </ul>
          </Panel>
        )}
      </div>
    </div>
  );
}
