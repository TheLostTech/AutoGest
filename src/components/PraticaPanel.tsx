"use client";

import Link from "next/link";
import { Fragment, useState } from "react";
import { CircleAlert, Check, Loader2, Printer } from "lucide-react";
import { ROLE_USER, useStore } from "@/lib/store";
import { ATTESTAZIONE, cfOk, identOk, CONFERENTI, docsFor, nextCertNumber, praticaSteps, RADIAZIONE, simulateVisura, type StepState } from "@/lib/pratica";
import { dateIt } from "@/lib/logic";

// Importi ufficiali con i centesimi (es. emolumenti 13,50 €)
const eur = (n: number) => n.toLocaleString("it-IT", { style: "currency", currency: "EUR" });
import type { ConferenteTipo, Vehicle } from "@/lib/types";
import { Button, Panel } from "./ui";

// La pratica come percorso RVFU: un passo alla volta, l'azione compare solo sul passo attuale.
export function PraticaPanel({ v }: { v: Vehicle }) {
  const { updateVehicle, vehicles, role } = useStore();
  const steps = praticaSteps(v);
  // La pratica la gestisce l'ufficio: gli altri ruoli la vedono in sola lettura
  const canEdit = role === "accettazione" || role === "responsabile";
  const [tipo, setTipo] = useState<ConferenteTipo>(v.conferente?.tipo ?? "privato");
  const [nome, setNome] = useState(v.conferente?.nome ?? "");
  const [cf, setCf] = useState(v.conferente?.cf ?? "");
  const [docId, setDocId] = useState(v.conferente?.documento ?? "");
  const [checking, setChecking] = useState(false);
  const [canale, setCanale] = useState<"rvfu" | "agenzia">("rvfu");
  const consegna = v.presaInCarico?.at ?? v.intakeAt;
  const deadline = new Date(new Date(consegna).getTime() + RADIAZIONE.terminiGiorni * 864e5).toISOString();
  const costoRad = RADIAZIONE.costi.reduce((a, c) => a + c.euro, 0);
  const changed =
    tipo !== v.conferente?.tipo || nome.trim() !== (v.conferente?.nome ?? "") || cf.trim().toUpperCase() !== (v.conferente?.cf ?? "") || docId.trim() !== (v.conferente?.documento ?? "");

  const toggleDoc = (key: string, on: boolean) => {
    const docs = new Set(v.documenti ?? []);
    if (on) docs.add(key);
    else docs.delete(key);
    updateVehicle(v.id, { documenti: [...docs] }, on ? "Documento ricevuto" : "Documento tolto", [...docsFor(v), ATTESTAZIONE].find((d) => d.key === key)?.label);
  };

  return (
    <Panel title="Pratica di demolizione · RVFU" action={v.dossier.number && <span className="code text-[15px] font-semibold text-ink">{v.dossier.number}</span>}>
      <ol className="p-4">
        {/* 1 · Chi consegna e documenti */}
        <Step
          readOnly={!canEdit}
          n={1}
          state={steps.docs}
          title="Chi consegna e documenti"
          summary={
            v.conferente
              ? `${CONFERENTI.find((c) => c.value === v.conferente!.tipo)?.label} · ${v.conferente.nome}${v.conferente.cf ? ` · ${v.conferente.cf}` : ""}`
              : "Da registrare"
          }
        >
          {steps.docs !== "fatto" && (
            <div className="space-y-3">
              <div className="grid gap-2">
                <select className="field h-11" value={tipo} onChange={(e) => setTipo(e.target.value as ConferenteTipo)} aria-label="Tipo di conferente">
                  {CONFERENTI.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
                <input className="field h-11" value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Nome e cognome o ragione sociale" aria-label="Nome di chi consegna" />
                <input className="field code h-11 uppercase" value={cf} onChange={(e) => setCf(e.target.value)} placeholder="Codice fiscale o partita IVA" aria-label="Codice fiscale o partita IVA" />
                {cf && !cfOk(cf) && <span className="text-sm font-medium text-danger">16 caratteri per il codice fiscale, 11 cifre per la partita IVA</span>}
                <input className="field h-11" value={docId} onChange={(e) => setDocId(e.target.value)} placeholder="Documento d'identità (tipo e numero)" aria-label="Documento d'identità" />
                {changed && (
                  <Button
                    size="sm"
                    className="h-11 justify-self-start"
                    disabled={!nome.trim() || !cfOk(cf)}
                    onClick={() =>
                      updateVehicle(v.id, { conferente: { tipo, nome: nome.trim(), cf: cf.trim().toUpperCase(), documento: docId.trim() || undefined } }, "Dati di chi consegna registrati", `${tipo} · ${nome.trim()}`)
                    }
                  >
                    Salva
                  </Button>
                )}
              </div>
              {v.conferente?.cf && (
                <ul className="grid gap-1">
                  {docsFor(v).map((d) => (
                    <li key={d.key}>
                      <label className="flex min-h-10 items-center gap-2.5 text-[15px]">
                        <input type="checkbox" className="size-5 shrink-0 accent-band" checked={!!v.documenti?.includes(d.key)} onChange={(e) => toggleDoc(d.key, e.target.checked)} />
                        {d.label}
                      </label>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {steps.docs === "fatto" && (
            <p className="text-sm text-ink-3">
              {docsFor(v).filter((d) => v.documenti?.includes(d.key)).length} documenti ritirati{v.conferente?.documento ? ` · ${v.conferente.documento}` : ""}
            </p>
          )}
        </Step>

        {/* 2 · Visura PRA */}
        <Step
          readOnly={!canEdit}
          n={2}
          state={steps.visura}
          title="Visura al PRA"
          summary={v.visura ? `${v.visura.fermo ? "Fermo amministrativo presente" : "Nessun fermo"} · intestatario ${v.visura.intestatario} · ${dateIt(v.visura.at)}` : "Intestatario, fermi e ipoteche"}
          note={
            v.visura?.fermo && (
              <span className="block space-y-2 rounded-md bg-warn-bg px-3 py-2 text-sm text-warn">
                <span className="flex items-start gap-2">
                  <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
                  <span>Dal 20/02/2026 il fermo non impedisce la radiazione per demolizione, se c&apos;è l&apos;attestazione di inutilizzabilità del veicolo (art. 5 c. 8-bis D.Lgs. 209/2003). Il proprietario perde eventuali incentivi.</span>
                </span>
                <label className="flex min-h-10 items-center gap-2.5 font-semibold">
                  <input type="checkbox" className="size-5 shrink-0 accent-band" disabled={!canEdit || !!v.presaInCarico} checked={!!v.documenti?.includes(ATTESTAZIONE.key)} onChange={(e) => toggleDoc(ATTESTAZIONE.key, e.target.checked)} />
                  {ATTESTAZIONE.label}
                </label>
              </span>
            )
          }
        >
          {steps.visura === "attuale" && (
            <Button
              size="sm"
              disabled={checking}
              onClick={async () => {
                setChecking(true);
                const r = await simulateVisura(v);
                setChecking(false);
                updateVehicle(v.id, { visura: r }, "Visura PRA eseguita", r.fermo ? "fermo amministrativo presente" : "nessun fermo amministrativo");
              }}
            >
              {checking ? <><Loader2 className="size-4 animate-spin" aria-hidden /> Visura in corso…</> : "Esegui la visura"}
            </Button>
          )}
        </Step>

        {/* 3 · Presa in carico nel RVFU e CRD */}
        <Step
          readOnly={!canEdit}
          n={3}
          state={steps.presa}
          title="Presa in carico e certificato digitale (CRD)"
          summary={
            v.presaInCarico
              ? `${dateIt(v.presaInCarico.at, true)} · ${v.presaInCarico.by} · consegna la copia stampata a chi ha portato il veicolo. Targhe e documenti si distruggono non prima del ${dateIt(new Date(new Date(v.presaInCarico.at).getTime() + RADIAZIONE.conservazioneGiorni * 864e5).toISOString())}`
              : !identOk(v)
                ? "Bloccata: serve il telaio (VIN) verificato sul veicolo, vedi l'avviso in alto nella scheda"
                : "Nel RVFU: il CRD riceve un codice nazionale e si può annullare solo in giornata"
          }
        >
          {steps.presa === "attuale" && (
            <Button
              size="sm"
              onClick={() => {
                const number = v.dossier.number || nextCertNumber(vehicles);
                updateVehicle(
                  v.id,
                  {
                    presaInCarico: { at: new Date().toISOString(), by: ROLE_USER[role].user },
                    dossier: { ...v.dossier, number, kind: "Certificato di Rottamazione Digitale", status: "in corso" },
                    radiazione: { stato: "da richiedere" },
                  },
                  "Presa in carico nel RVFU (simulata)",
                  `CRD ${number}`,
                );
              }}
            >
              Prendi in carico e genera il CRD
            </Button>
          )}
          {steps.presa === "fatto" && (
            <Link href={`/certificato/${v.id}`} target="_blank" className="inline-flex items-center gap-1.5 text-[15px] font-semibold text-band">
              <Printer className="size-4" aria-hidden /> Stampa la copia del CRD
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
                ? `Richiesta il ${dateIt(v.radiazione.richiestaAt!)} ${v.radiazione.canale === "agenzia" ? "tramite agenzia" : "nel RVFU"} · in attesa di esito`
                : `Entro il ${dateIt(deadline)}: 30 giorni dalla consegna`
          }
        >
          {steps.radiazione === "attuale" && v.radiazione?.stato !== "richiesta" && (
            <div className="space-y-3">
              <div className="inline-flex rounded-md border border-hair bg-carton p-1" role="radiogroup" aria-label="Canale della radiazione">
                {(["rvfu", "agenzia"] as const).map((c) => (
                  <button
                    key={c}
                    role="radio"
                    aria-checked={canale === c}
                    onClick={() => setCanale(c)}
                    className={`min-h-10 rounded px-3 text-[15px] font-semibold ${canale === c ? "bg-label text-ink shadow-sm" : "text-ink-2"}`}
                  >
                    {c === "rvfu" ? "Diretta nel RVFU" : "Tramite agenzia"}
                  </button>
                ))}
              </div>
              <dl className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 gap-y-0.5 text-sm">
                {RADIAZIONE.costi.map((c) => (
                  <Fragment key={c.voce}>
                    <dt className="text-ink-2">{c.voce}</dt>
                    <dd className="code text-right">{eur(c.euro)}</dd>
                  </Fragment>
                ))}
                <dt className="font-semibold">Totale{canale === "agenzia" ? " + compenso agenzia" : ""}</dt>
                <dd className="code text-right font-bold">{eur(costoRad)}</dd>
              </dl>
              <p className="text-[13px] text-ink-3">
                Pratica DU {RADIAZIONE.codicePratica}. {RADIAZIONE.fascicolo}. {RADIAZIONE.nota}.
              </p>
              <Button
                size="sm"
                onClick={() =>
                  updateVehicle(v.id, { radiazione: { stato: "richiesta", richiestaAt: new Date().toISOString(), canale } }, "Radiazione richiesta", canale === "rvfu" ? "nel RVFU (simulato)" : "tramite agenzia (simulato)")
                }
              >
                Richiedi la radiazione
              </Button>
            </div>
          )}
          {steps.radiazione === "attuale" && v.radiazione?.stato === "richiesta" && (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                const estremi = `RAD-${(v.dossier.number || v.id).slice(-6)}`;
                updateVehicle(
                  v.id,
                  { radiazione: { ...v.radiazione!, stato: "completata", completataAt: new Date().toISOString(), estremi }, dossier: { ...v.dossier, status: "completata" } },
                  "Radiazione completata",
                  estremi,
                );
              }}
            >
              Registra l&apos;esito della radiazione
            </Button>
          )}
        </Step>
      </ol>
      <p className="border-t border-hair-soft px-4 py-2.5 text-[13px] text-ink-3">
        {!canEdit && "La pratica la gestisce l'ufficio. "}Flusso RVFU, obbligatorio dal 7/6/2024. Visura, RVFU e radiazione sono simulati nel prototipo; fonti e costi in docs/INTEGRAZIONI.md.
      </p>
    </Panel>
  );
}

function Step({
  n,
  state,
  title,
  summary,
  children,
  note,
  last,
  readOnly,
}: {
  n: number;
  state: StepState;
  title: string;
  summary: string;
  children?: React.ReactNode;
  note?: React.ReactNode;
  last?: boolean;
  readOnly?: boolean;
}) {
  const dot = state === "fatto" ? "bg-ok text-white" : state === "attuale" ? "bg-band text-white" : "border border-hair bg-label text-ink-3";
  return (
    <li className="grid grid-cols-[32px_minmax(0,1fr)] gap-x-3">
      <span className="flex flex-col items-center">
        <span className={`code grid size-8 shrink-0 place-items-center rounded-full text-[15px] font-bold ${dot}`}>{state === "fatto" ? <Check className="size-4" aria-hidden /> : n}</span>
        {!last && <span className={`w-px flex-1 ${state === "fatto" ? "bg-ok" : "bg-hair"}`} aria-hidden />}
      </span>
      <div className={`min-w-0 ${last ? "" : "pb-5"}`}>
        <p className={`font-semibold leading-8 ${state === "dopo" ? "text-ink-3" : ""}`}>{title}</p>
        <p className="text-sm text-ink-2">{summary}</p>
        {note && <div className="mt-2">{note}</div>}
        {children && state !== "dopo" && !readOnly && <div className="mt-2.5">{children}</div>}
      </div>
    </li>
  );
}
