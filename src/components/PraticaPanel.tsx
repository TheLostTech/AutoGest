"use client";

import Link from "next/link";
import { useState } from "react";
import { Check, Loader2, Lock, Printer } from "lucide-react";
import { ROLE_USER, useStore } from "@/lib/store";
import { CONFERENTI, docsFor, nextCertNumber, praticaSteps, simulateVisura, type StepState } from "@/lib/pratica";
import { TERMS } from "@/lib/agenda";
import { dateIt } from "@/lib/logic";
import type { ConferenteTipo, Vehicle } from "@/lib/types";
import { Button, Panel } from "./ui";

// La pratica come percorso: un passo alla volta, l'azione compare solo sul passo attuale.
export function PraticaPanel({ v }: { v: Vehicle }) {
  const { updateVehicle, vehicles, role } = useStore();
  const steps = praticaSteps(v);
  // La pratica la gestisce l'ufficio: gli altri ruoli la vedono in sola lettura
  const canEdit = role === "accettazione" || role === "responsabile";
  const [tipo, setTipo] = useState<ConferenteTipo>(v.conferente?.tipo ?? "privato");
  const [nome, setNome] = useState(v.conferente?.nome ?? "");
  const [checking, setChecking] = useState(false);
  const deadline = new Date(new Date(v.intakeAt).getTime() + TERMS.radiazione * 864e5).toISOString();

  const toggleDoc = (key: string, on: boolean) => {
    const docs = new Set(v.documenti ?? []);
    if (on) docs.add(key);
    else docs.delete(key);
    updateVehicle(v.id, { documenti: [...docs] }, on ? "Documento ricevuto" : "Documento tolto", docsFor(v).find((d) => d.key === key)?.label);
  };

  return (
    <Panel title="Pratica di demolizione" action={v.dossier.number && <span className="code text-[15px] font-semibold text-ink">{v.dossier.number}</span>}>
      <ol className="p-4">
        {/* 1 · Conferimento e documenti */}
        <Step readOnly={!canEdit} n={1} state={steps.docs} title="Chi conferisce e documenti" summary={v.conferente ? `${CONFERENTI.find((c) => c.value === v.conferente!.tipo)?.label} · ${v.conferente.nome}` : "Da registrare"}>
          {steps.docs !== "fatto" && (
            <div className="space-y-3">
              <div className="grid gap-2">
                <select className="field h-11" value={tipo} onChange={(e) => setTipo(e.target.value as ConferenteTipo)} aria-label="Tipo di conferente">
                  {CONFERENTI.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
                <input className="field h-11" value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Nome o ragione sociale" aria-label="Nome di chi conferisce" />
                {(tipo !== v.conferente?.tipo || nome.trim() !== (v.conferente?.nome ?? "")) && (
                  <Button size="sm" className="h-11 justify-self-start" disabled={!nome.trim()} onClick={() => updateVehicle(v.id, { conferente: { tipo, nome: nome.trim() } }, "Conferente registrato", `${tipo} · ${nome.trim()}`)}>
                    Salva
                  </Button>
                )}
              </div>
              {v.conferente && (
                <ul className="grid gap-1 sm:grid-cols-2">
                  {docsFor(v).map((d) => (
                    <li key={d.key}>
                      <label className="flex min-h-10 items-center gap-2.5 text-[15px]">
                        <input type="checkbox" className="size-5 accent-band" checked={!!v.documenti?.includes(d.key)} onChange={(e) => toggleDoc(d.key, e.target.checked)} />
                        {d.label}
                      </label>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {steps.docs === "fatto" && <p className="text-sm text-ink-3">{docsFor(v).length} documenti ricevuti</p>}
        </Step>

        {/* 2 · Visura PRA */}
        <Step
          readOnly={!canEdit}
          n={2}
          state={steps.visura}
          title="Visura al PRA"
          summary={v.visura ? (v.visura.fermo ? "Fermo amministrativo presente" : `Nessun fermo · ${dateIt(v.visura.at)}`) : "Verifica intestatario e fermi"}
        >
          {steps.visura === "bloccato" && (
            <p className="text-[15px] font-semibold text-danger">La presa in carico è bloccata finché il fermo non viene cancellato. Contatta chi conferisce il veicolo.</p>
          )}
          {(steps.visura === "attuale" || steps.visura === "bloccato") && (
            <Button
              size="sm"
              variant={steps.visura === "bloccato" ? "secondary" : "primary"}
              disabled={checking}
              onClick={async () => {
                setChecking(true);
                const r = await simulateVisura(v);
                setChecking(false);
                updateVehicle(v.id, { visura: r }, "Visura PRA eseguita", r.fermo ? "fermo amministrativo presente" : "nessun fermo amministrativo");
              }}
            >
              {checking ? <><Loader2 className="size-4 animate-spin" aria-hidden /> Visura in corso…</> : steps.visura === "bloccato" ? "Ripeti la visura" : "Esegui la visura"}
            </Button>
          )}
        </Step>

        {/* 3 · Presa in carico e certificato */}
        <Step readOnly={!canEdit} n={3} state={steps.presa} title="Presa in carico e certificato" summary={v.presaInCarico ? `${dateIt(v.presaInCarico.at)} · ${v.presaInCarico.by}` : "Genera il certificato di rottamazione"}>
          {steps.presa === "attuale" && (
            <Button
              size="sm"
              onClick={() => {
                const number = v.dossier.number || nextCertNumber(vehicles);
                updateVehicle(
                  v.id,
                  { presaInCarico: { at: new Date().toISOString(), by: ROLE_USER[role].user }, dossier: { ...v.dossier, number, status: "in corso" }, radiazione: { stato: "da richiedere" } },
                  "Presa in carico",
                  `certificato ${number}`,
                );
              }}
            >
              Prendi in carico e genera il certificato
            </Button>
          )}
          {steps.presa === "fatto" && (
            <Link href={`/certificato/${v.id}`} target="_blank" className="inline-flex items-center gap-1.5 text-[15px] font-semibold text-band">
              <Printer className="size-4" aria-hidden /> Stampa il certificato
            </Link>
          )}
        </Step>

        {/* 4 · Radiazione */}
        <Step
          readOnly={!canEdit}
          n={4}
          last
          state={steps.radiazione}
          title="Radiazione dal PRA"
          summary={
            v.radiazione?.stato === "completata"
              ? `Completata ${dateIt(v.radiazione.completataAt!)} · ${v.radiazione.estremi}`
              : v.radiazione?.stato === "richiesta"
                ? `Richiesta il ${dateIt(v.radiazione.richiestaAt!)} · in attesa di esito`
                : `Da richiedere entro il ${dateIt(deadline)}`
          }
        >
          {steps.radiazione === "attuale" && v.radiazione?.stato !== "richiesta" && (
            <Button size="sm" onClick={() => updateVehicle(v.id, { radiazione: { stato: "richiesta", richiestaAt: new Date().toISOString() } }, "Radiazione richiesta", "tramite agenzia partner (simulato)")}>
              Richiedi la radiazione
            </Button>
          )}
          {steps.radiazione === "attuale" && v.radiazione?.stato === "richiesta" && (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                const estremi = `RAD-${(v.dossier.number || v.id).slice(-6)}`;
                updateVehicle(v.id, { radiazione: { ...v.radiazione!, stato: "completata", completataAt: new Date().toISOString(), estremi }, dossier: { ...v.dossier, status: "completata" } }, "Radiazione completata", estremi);
              }}
            >
              Registra l&apos;esito della radiazione
            </Button>
          )}
        </Step>
      </ol>
      <p className="border-t border-hair-soft px-4 py-2.5 text-[13px] text-ink-3">
        {!canEdit && "La pratica la gestisce l'ufficio. "}Visura, certificato e radiazione sono simulati: modelli e collegamenti ufficiali da verificare.
      </p>
    </Panel>
  );
}

function Step({ n, state, title, summary, children, last, readOnly }: { n: number; state: StepState; title: string; summary: string; children?: React.ReactNode; last?: boolean; readOnly?: boolean }) {
  const dot =
    state === "fatto"
      ? "bg-ok text-white"
      : state === "attuale"
        ? "bg-band text-white"
        : state === "bloccato"
          ? "bg-danger text-white"
          : "border border-hair bg-label text-ink-3";
  return (
    <li className="grid grid-cols-[32px_minmax(0,1fr)] gap-x-3">
      <span className="flex flex-col items-center">
        <span className={`code grid size-8 shrink-0 place-items-center rounded-full text-[15px] font-bold ${dot}`}>
          {state === "fatto" ? <Check className="size-4" aria-hidden /> : state === "bloccato" ? <Lock className="size-4" aria-hidden /> : n}
        </span>
        {!last && <span className={`w-px flex-1 ${state === "fatto" ? "bg-ok" : "bg-hair"}`} aria-hidden />}
      </span>
      <div className={`min-w-0 ${last ? "" : "pb-5"}`}>
        <p className={`font-semibold leading-8 ${state === "dopo" ? "text-ink-3" : ""}`}>{title}</p>
        <p className={`text-sm ${state === "bloccato" ? "font-semibold text-danger" : "text-ink-2"}`}>{summary}</p>
        {children && state !== "dopo" && !readOnly && <div className="mt-2.5">{children}</div>}
      </div>
    </li>
  );
}
