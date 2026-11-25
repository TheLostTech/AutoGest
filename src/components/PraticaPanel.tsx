"use client";

import { controllaDimensione } from "@/lib/limiti-file";
import Link from "next/link";
import { Fragment, useCallback, useEffect, useState } from "react";
import { CircleAlert, Check, FileText, Loader2, Printer, RefreshCw, Upload } from "lucide-react";
import { useStore } from "@/lib/store";
import {
  ATTESTAZIONE,
  cfOk,
  CODICI_RADIAZIONE,
  CONFERENTI,
  DISTRUZIONE,
  distruzioneDal,
  docsFor,
  fascicoloAuto,
  fascicoloFor,
  identOk,
  nextCertNumber,
  praticaSteps,
  RADIAZIONE,
  simulateVisura,
  type CodiceRadiazione,
  type StepState,
} from "@/lib/pratica";
import { dateIt } from "@/lib/logic";

// Importi ufficiali con i centesimi (es. emolumenti 13,50 €)
const eur = (n: number) => n.toLocaleString("it-IT", { style: "currency", currency: "EUR" });
import type { ConferenteTipo, Vehicle } from "@/lib/types";
import { Button, Panel } from "./ui";
import { fetchAzienda } from "@/lib/accesso/azienda-client";

// La pratica come percorso RVFU: un passo alla volta, l'azione compare solo sul passo attuale.
export function PraticaPanel({ v }: { v: Vehicle }) {
  const { updateVehicle, vehicles, role, operatore } = useStore();
  const steps = praticaSteps(v);
  // La pratica la gestisce l'ufficio: gli altri ruoli la vedono in sola lettura
  const canEdit = role === "accettazione" || role === "responsabile";
  const [tipo, setTipo] = useState<ConferenteTipo>(v.conferente?.tipo ?? "privato");
  const [nome, setNome] = useState(v.conferente?.nome ?? "");
  const [cf, setCf] = useState(v.conferente?.cf ?? "");
  const [docId, setDocId] = useState(v.conferente?.documento ?? "");
  const consegna = v.presaInCarico?.at ?? v.intakeAt;
  const deadline = new Date(new Date(consegna).getTime() + RADIAZIONE.terminiGiorni * 864e5).toISOString();
  const rad = v.radiazione;
  const dal = distruzioneDal(v);
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
          summary={
            v.visura
              ? `${v.visura.fermo ? "Fermo amministrativo presente" : "Nessun fermo"} · intestatario ${v.visura.intestatario} · ${dateIt(v.visura.at)}${v.visura.fonte === "simulata" ? " · simulata" : ""}`
              : v.visuraRichiesta
                ? `Richiesta a Openapi il ${dateIt(v.visuraRichiesta.at)} · ${v.visuraRichiesta.pdf ? "PDF arrivato, esito da registrare" : "in attesa del PDF"}`
                : "Intestatario, fermi e ipoteche"
          }
          note={
            (v.visura?.pdf || v.visura?.fermo) && (
              <span className="block space-y-2">
                {v.visura.pdf && (
                  <a className="inline-flex min-h-10 items-center gap-2 text-sm font-semibold text-band underline-offset-2 hover:underline" href={v.visura.pdf} target="_blank" rel="noreferrer">
                    <FileText className="size-4" aria-hidden /> Apri il PDF della visura
                  </a>
                )}
                {v.visura.fermo && (
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
                )}
              </span>
            )
          }
        >
          {steps.visura === "attuale" && <VisuraPra v={v} />}
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
                    presaInCarico: { at: new Date().toISOString(), by: operatore ? `${operatore.nome}${operatore.assistenza ? " (assistenza)" : ""}` : "Operatore" },
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

        {/* 4 · Radiazione: fascicolo digitale inviato al PRA, poi la ricevuta di avvenuta radiazione */}
        <Step
          readOnly={!canEdit}
          n={4}
          state={steps.radiazione}
          title="Radiazione dal PRA"
          summary={
            rad?.stato === "completata"
              ? `Radiato il ${dateIt(rad.completataAt!)} · ricevuta del PRA n. ${rad.estremi}${rad.ricevuta ? "" : " · PDF non allegato"}`
              : rad?.stato === "richiesta"
                ? `Inviata il ${dateIt(rad.richiestaAt!)} · ${rad.codice ?? RADIAZIONE.codicePratica} ${rad.canale === "agenzia" ? "tramite agenzia" : "nel RVFU"} · in attesa della ricevuta del PRA`
                : rad?.stato === "da integrare"
                  ? `Il PRA ha chiesto un'integrazione il ${dateIt(rad.integrazione!.at)}: completa il fascicolo e invialo di nuovo entro il ${dateIt(deadline)}`
                  : `Entro il ${dateIt(deadline)}: 30 giorni dalla consegna`
          }
          note={
            ((rad?.stato === "completata" && rad.ricevuta) || (rad?.stato === "da integrare" && rad.integrazione)) && (
              <span className="block space-y-2">
                {rad.stato === "completata" && rad.ricevuta && (
                  <a className="inline-flex min-h-10 items-center gap-2 text-sm font-semibold text-band underline-offset-2 hover:underline" href={rad.ricevuta} target="_blank" rel="noreferrer">
                    <FileText className="size-4" aria-hidden /> Apri la ricevuta di avvenuta radiazione
                  </a>
                )}
                {rad.stato === "da integrare" && rad.integrazione && (
                  <span className="flex items-start gap-2 rounded-md bg-warn-bg px-3 py-2 text-sm text-warn">
                    <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
                    <span>Il PRA chiede: {rad.integrazione.nota}</span>
                  </span>
                )}
              </span>
            )
          }
        >
          {steps.radiazione === "attuale" && rad?.stato !== "richiesta" && <InvioRadiazione v={v} />}
          {steps.radiazione === "attuale" && rad?.stato === "richiesta" && <EsitoRadiazione v={v} />}
          {rad?.stato === "completata" && !rad.ricevuta && (
            <CaricaPdf
              label="Allega il PDF della ricevuta"
              onCaricato={(url) => updateVehicle(v.id, { radiazione: { ...rad, ricevuta: url } }, "Ricevuta di radiazione allegata", `ricevuta n. ${rad.estremi}`)}
            />
          )}
        </Step>

        {/* 5 · Distruzione di targhe e documenti, da annotare nel RVFU */}
        <Step
          readOnly={!canEdit}
          n={5}
          last
          state={steps.distruzione}
          title="Distruzione di targhe e documenti"
          summary={
            v.distruzione
              ? `Distrutti il ${dateIt(v.distruzione.at)} · ${v.distruzione.by} · ${v.distruzione.cosa.map((k) => DISTRUZIONE.find((d) => d.key === k)?.label ?? k).join(", ")}`
              : dal && new Date(dal) <= new Date()
                ? `Si possono distruggere dal ${dateIt(dal)}, 120 giorni dal CRD: registra cosa e quando`
                : dal
                  ? `Dal ${dateIt(dal)}, 120 giorni dal CRD. Fino ad allora restano custoditi nel centro`
                  : "Dopo la radiazione, non prima di 120 giorni dal CRD"
          }
        >
          {steps.distruzione === "attuale" && <Distruzione v={v} />}
        </Step>
      </ol>
      <p className="border-t border-hair-soft px-4 py-2.5 text-[13px] text-ink-3">
        {!canEdit && "La pratica la gestisce l'ufficio. "}Flusso RVFU, obbligatorio dal 7/6/2024. RVFU e invio della radiazione sono simulati nel prototipo: la ricevuta del PRA si registra a mano e si allega in PDF. La visura PRA è vera se Openapi è collegato in Impostazioni → Collegamenti. Fonti e costi in docs/INTEGRAZIONI.md.
      </p>
    </Panel>
  );
}

// Passo 2: visura PRA. Con Openapi configurato (Impostazioni → Collegamenti) la visura è vera e asincrona:
// si chiede, il PDF arriva entro 24 ore lavorative, l'ufficio lo legge e registra intestatario e fermo.
// Senza Openapi resta la visura simulata del prototipo.
const TIPI_PRA = [
  { value: "AUTOVEICOLO", label: "Autoveicolo" },
  { value: "MOTOVEICOLO", label: "Motoveicolo" },
  { value: "RIMORCHIO", label: "Rimorchio" },
];

const leggi = async (res: Response) => {
  const d = (await res.json().catch(() => ({}))) as { error?: string } & Record<string, unknown>;
  if (!res.ok) throw new Error(d.error || `Errore ${res.status}`);
  return d;
};

function VisuraPra({ v }: { v: Vehicle }) {
  const { updateVehicle } = useStore();
  const rq = v.visuraRichiesta;
  const [modo, setModo] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [errore, setErrore] = useState("");
  const [avviso, setAvviso] = useState("");
  const [tipo, setTipo] = useState("AUTOVEICOLO");
  const [intestatario, setIntestatario] = useState(v.conferente?.nome ?? "");
  const [fermo, setFermo] = useState(false);


  const controlla = useCallback(async () => {
    if (!rq) return;
    setBusy(true);
    setErrore("");
    setAvviso("");
    try {
      const d = (await leggi(await fetchAzienda(`/api/visura/${rq.id}`, { cache: "no-store" }))) as { stato: string; pdf?: string; messaggio?: string };
      if (d.messaggio) setAvviso(d.messaggio);
      else if (!d.pdf) setAvviso("Visura non ancora pronta: Openapi la evade entro 24 ore lavorative.");
      if (d.stato !== rq.stato || d.pdf !== rq.pdf)
        updateVehicle(v.id, { visuraRichiesta: { ...rq, stato: d.stato, pdf: d.pdf } }, d.pdf ? "Visura PRA arrivata" : "Stato visura PRA aggiornato", d.pdf ? "PDF da leggere" : d.stato);
    } catch (e) {
      setErrore((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, [rq, v.id, updateVehicle]);

  // All'apertura della pratica: come lavora la visura e, se ce n'è una in attesa, se il PDF è arrivato
  useEffect(() => {
    fetchAzienda("/api/visura", { cache: "no-store" })
      .then(leggi)
      .then((d) => {
        const m = String(d.modo);
        setModo(m);
        if (m !== "Simulato" && rq && !rq.pdf) void controlla();
      })
      .catch(() => setModo("Simulato"));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- una volta sola, all'apertura
  }, []);

  if (!modo) return <p className="flex items-center gap-2 text-sm text-ink-3"><Loader2 className="size-4 animate-spin" aria-hidden /> Controllo del collegamento…</p>;

  const msg = (
    <>
      {errore && <p className="text-sm font-semibold text-danger" role="alert">{errore}</p>}
      {avviso && <p className="text-sm text-ink-2">{avviso}</p>}
    </>
  );

  if (modo === "Simulato" && !rq)
    return (
      <div className="space-y-2">
        <Button
          size="sm"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            const r = await simulateVisura(v);
            setBusy(false);
            updateVehicle(v.id, { visura: { ...r, fonte: "simulata" } }, "Visura PRA eseguita", `simulata · ${r.fermo ? "fermo amministrativo presente" : "nessun fermo amministrativo"}`);
          }}
        >
          {busy ? <><Loader2 className="size-4 animate-spin" aria-hidden /> Visura in corso…</> : "Esegui la visura (simulata)"}
        </Button>
        <p className="text-xs text-ink-3">Per la visura vera collega Openapi in Impostazioni → Collegamenti e scegli &quot;Visura PRA&quot;.</p>
      </div>
    );

  if (!rq)
    return (
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <select className="field h-11" value={tipo} onChange={(e) => setTipo(e.target.value)} aria-label="Tipo di veicolo al PRA">
            {TIPI_PRA.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
          <Button
            size="sm"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              setErrore("");
              try {
                const d = await leggi(await fetchAzienda("/api/visura", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ targa: v.plate, tipo }) }));
                updateVehicle(
                  v.id,
                  { visuraRichiesta: { id: String(d.id), at: new Date().toISOString(), stato: String(d.stato), modo: String(d.modo) } },
                  "Visura PRA richiesta",
                  `Openapi ${d.modo} · targa ${v.plate}`,
                );
              } catch (e) {
                setErrore((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            {busy ? <><Loader2 className="size-4 animate-spin" aria-hidden /> Invio…</> : `Richiedi la visura di ${v.plate}`}
          </Button>
        </div>
        <p className="text-xs text-ink-3">
          Openapi {modo === "Sandbox" ? "· ambiente di prova, nessun addebito" : "· a pagamento (10,90–16,70 €, da confermare)"}. Il PDF arriva entro 24 ore lavorative.
        </p>
        {msg}
      </div>
    );

  if (!rq.pdf)
    return (
      <div className="space-y-2">
        <Button size="sm" variant="secondary" disabled={busy} onClick={() => void controlla()}>
          {busy ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <RefreshCw className="size-4" aria-hidden />} Controlla se è arrivata
        </Button>
        <p className="text-xs text-ink-3">Richiesta n. <span className="code">{rq.id}</span> · Openapi {rq.modo}</p>
        {msg}
      </div>
    );

  return (
    <div className="space-y-3">
      <a className="inline-flex min-h-10 items-center gap-2 text-sm font-semibold text-band underline-offset-2 hover:underline" href={rq.pdf} target="_blank" rel="noreferrer">
        <FileText className="size-4" aria-hidden /> Apri il PDF della visura
      </a>
      <p className="text-sm text-ink-2">Leggi la visura e registra cosa riporta.</p>
      <input className="field h-11 w-full" value={intestatario} onChange={(e) => setIntestatario(e.target.value)} placeholder="Intestatario come da visura" aria-label="Intestatario come da visura" />
      <label className="flex min-h-10 items-center gap-2.5 text-sm font-semibold">
        <input type="checkbox" className="size-5 shrink-0 accent-band" checked={fermo} onChange={(e) => setFermo(e.target.checked)} />
        La visura riporta un fermo amministrativo
      </label>
      <Button
        size="sm"
        disabled={!intestatario.trim()}
        onClick={() =>
          updateVehicle(
            v.id,
            { visura: { at: new Date().toISOString(), fermo, intestatario: intestatario.trim(), pdf: rq.pdf, fonte: "openapi" }, visuraRichiesta: undefined },
            "Visura PRA registrata",
            fermo ? "fermo amministrativo presente" : "nessun fermo amministrativo",
          )
        }
      >
        Registra l&apos;esito
      </Button>
    </div>
  );
}

// Giorno locale AAAA-MM-GG (per i campi data): toISOString darebbe il giorno in UTC
const giorno = (d: Date | string) => {
  const x = new Date(d);
  return `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, "0")}-${String(x.getDate()).padStart(2, "0")}`;
};
// A mezzogiorno, così il fuso orario non sposta la data
const daGiorno = (g: string) => new Date(`${g}T12:00:00`).toISOString();

function Scelta<T extends string>({ label, value, options, onChange }: { label: string; value: T; options: { value: T; label: string }[]; onChange: (v: T) => void }) {
  return (
    <div className="inline-flex flex-wrap rounded-md border border-hair bg-carton p-1" role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          onClick={() => onChange(o.value)}
          className={`min-h-10 rounded px-3 text-[15px] font-semibold ${value === o.value ? "bg-label text-ink shadow-sm" : "text-ink-2"}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

// Passo 4, prima parte: codice della pratica, canale, fascicolo digitale e costi. Si usa anche per reinviare dopo un'integrazione.
function InvioRadiazione({ v }: { v: Vehicle }) {
  const { updateVehicle } = useStore();
  const r = v.radiazione;
  const [codice, setCodice] = useState<CodiceRadiazione>(r?.codice ?? "C05332");
  const [canale, setCanale] = useState<"rvfu" | "agenzia">(r?.canale ?? "rvfu");
  // Dopo una richiesta di integrazione le voci spuntate a mano si confermano di nuovo
  const [spuntati, setSpuntati] = useState(() => new Set(r?.stato === "da integrare" ? [] : (r?.fascicolo ?? [])));
  const auto = fascicoloAuto(v);
  const voci = fascicoloFor(codice);
  const pronto = (k: string) => auto.has(k) || spuntati.has(k);
  const completo = voci.every((d) => pronto(d.key));
  const esente = !!CODICI_RADIAZIONE.find((c) => c.value === codice)?.esente;
  const totale = esente ? 0 : RADIAZIONE.costi.reduce((a, c) => a + c.euro, 0);
  const reinvio = r?.stato === "da integrare";

  return (
    <div className="space-y-3">
      <Scelta label="Codice della pratica" value={codice} onChange={setCodice} options={CODICI_RADIAZIONE.map((c) => ({ value: c.value, label: `${c.label} · ${c.value}` }))} />
      <Scelta
        label="Canale della radiazione"
        value={canale}
        onChange={setCanale}
        options={[
          { value: "rvfu", label: "Diretta nel RVFU" },
          { value: "agenzia", label: "Tramite agenzia" },
        ]}
      />
      <fieldset className="space-y-1">
        <legend className="text-sm font-semibold">Fascicolo digitale (un PDF unico)</legend>
        {voci.map((d) => (
          <label key={d.key} className="flex min-h-10 items-center gap-2.5 text-sm">
            <input
              type="checkbox"
              className="size-5 shrink-0 accent-band"
              disabled={auto.has(d.key)}
              checked={pronto(d.key)}
              onChange={(e) =>
                setSpuntati((s) => {
                  const n = new Set(s);
                  if (e.target.checked) n.add(d.key);
                  else n.delete(d.key);
                  return n;
                })
              }
            />
            <span>
              {d.label}
              {auto.has(d.key) && <span className="text-ink-3"> · dal {d.da}</span>}
            </span>
          </label>
        ))}
      </fieldset>
      <dl className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 gap-y-0.5 text-sm">
        {esente ? (
          <>
            <dt className="text-ink-2">Bollo ed emolumenti</dt>
            <dd className="text-right">esente</dd>
          </>
        ) : (
          RADIAZIONE.costi.map((c) => (
            <Fragment key={c.voce}>
              <dt className="text-ink-2">{c.voce}</dt>
              <dd className="code text-right">{eur(c.euro)}</dd>
            </Fragment>
          ))
        )}
        <dt className="font-semibold">Totale{canale === "agenzia" ? " + compenso agenzia" : ""}</dt>
        <dd className="code text-right font-bold">{eur(totale)}</dd>
      </dl>
      <p className="text-[13px] text-ink-3">
        {esente ? RADIAZIONE.fascicolo.replace("pagare e ", "") : RADIAZIONE.fascicolo}.{esente ? "" : ` ${RADIAZIONE.nota}.`} {canale === "agenzia" ? "L'agenzia ti manda la ricevuta del PRA quando la radiazione è fatta." : "La ricevuta del PRA arriva nel RVFU."}
      </p>
      <Button
        size="sm"
        disabled={!completo}
        onClick={() =>
          updateVehicle(
            v.id,
            { radiazione: { ...r, stato: "richiesta", codice, canale, fascicolo: voci.map((d) => d.key), richiestaAt: new Date().toISOString() } },
            reinvio ? "Radiazione: fascicolo integrato e inviato" : "Radiazione richiesta",
            `${codice} ${canale === "rvfu" ? "nel RVFU" : "tramite agenzia"} (simulato)`,
          )
        }
      >
        {reinvio ? "Invia di nuovo il fascicolo" : "Invia la pratica di radiazione"}
      </Button>
      {!completo && <p className="text-[13px] text-ink-3">Spunta le voci del fascicolo per inviare la pratica.</p>}
    </div>
  );
}

// Passo 4, seconda parte: il PRA risponde con la ricevuta di avvenuta radiazione (o chiede un'integrazione).
function EsitoRadiazione({ v }: { v: Vehicle }) {
  const { updateVehicle } = useStore();
  const r = v.radiazione!;
  const oggi = giorno(new Date());
  const min = r.richiestaAt ? giorno(r.richiestaAt) : undefined;
  const [numero, setNumero] = useState("");
  const [data, setData] = useState(oggi);
  const [pdf, setPdf] = useState<string>();
  const [integra, setIntegra] = useState(false);
  const [nota, setNota] = useState("");
  const dataOk = !!data && data <= oggi && (!min || data >= min);

  if (integra)
    return (
      <div className="space-y-2.5">
        <label className="block text-sm font-semibold" htmlFor={`integra-${v.id}`}>
          Cosa chiede il PRA
        </label>
        <textarea id={`integra-${v.id}`} className="field min-h-20 w-full py-2" value={nota} onChange={(e) => setNota(e.target.value)} placeholder="Es. manca la firma sull'istanza unificata" />
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            disabled={!nota.trim()}
            onClick={() =>
              updateVehicle(v.id, { radiazione: { ...r, stato: "da integrare", integrazione: { at: new Date().toISOString(), nota: nota.trim() } } }, "Radiazione: il PRA chiede un'integrazione", nota.trim())
            }
          >
            Registra la richiesta
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setIntegra(false)}>
            Annulla
          </Button>
        </div>
      </div>
    );

  return (
    <div className="space-y-2.5">
      <p className="text-sm text-ink-2">
        Quando il PRA registra la radiazione emette la <b className="text-ink">ricevuta di avvenuta radiazione</b>: è l&apos;unica prova che il veicolo è cancellato. {r.canale === "agenzia" ? "Te la manda l'agenzia" : "Arriva nel RVFU"}: riporta qui numero e data e allega il PDF.
      </p>
      <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
        <input className="field h-11" value={numero} onChange={(e) => setNumero(e.target.value)} placeholder="Numero della ricevuta" aria-label="Numero della ricevuta di avvenuta radiazione" />
        <input type="date" className="field h-11" value={data} min={min} max={oggi} onChange={(e) => setData(e.target.value)} aria-label="Data della radiazione" />
      </div>
      {pdf ? (
        <a className="inline-flex min-h-10 items-center gap-2 text-sm font-semibold text-band underline-offset-2 hover:underline" href={pdf} target="_blank" rel="noreferrer">
          <FileText className="size-4" aria-hidden /> PDF della ricevuta allegato
        </a>
      ) : (
        <CaricaPdf label="Allega il PDF della ricevuta" onCaricato={setPdf} />
      )}
      {!dataOk && data && <p className="text-sm text-danger">La data deve essere tra l&apos;invio della pratica e oggi.</p>}
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          disabled={!numero.trim() || !dataOk}
          onClick={() =>
            updateVehicle(
              v.id,
              { radiazione: { ...r, stato: "completata", completataAt: daGiorno(data), estremi: numero.trim(), ricevuta: pdf }, dossier: { ...v.dossier, status: "completata" } },
              "Radiazione completata",
              `ricevuta del PRA n. ${numero.trim()}${pdf ? "" : " (PDF non allegato)"}`,
            )
          }
        >
          Registra la ricevuta
        </Button>
        <Button size="sm" variant="secondary" onClick={() => setIntegra(true)}>
          Il PRA chiede un&apos;integrazione
        </Button>
      </div>
    </div>
  );
}

const PDF_PREFIX = "data:application/pdf;base64,";

function CaricaPdf({ label, onCaricato }: { label: string; onCaricato: (url: string) => void }) {
  const [busy, setBusy] = useState(false);
  const [errore, setErrore] = useState("");

  const carica = async (f: File) => {
    setErrore("");
    const dim = controllaDimensione(f.size);
    if (!dim.ok) return setErrore(dim.messaggio);
    setBusy(true);
    try {
      const url = await new Promise<string>((ok, ko) => {
        const fr = new FileReader();
        fr.onload = () => ok(String(fr.result));
        fr.onerror = () => ko(new Error("File non leggibile"));
        fr.readAsDataURL(f);
      });
      const d = (await leggi(
        await fetchAzienda("/api/allegati", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ data: PDF_PREFIX + url.split(",")[1] }) }),
      )) as { url: string };
      onCaricato(d.url);
    } catch (e) {
      setErrore((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <label className={`inline-flex min-h-10 items-center gap-1.5 text-[15px] font-semibold text-band ${busy ? "opacity-60" : "cursor-pointer"}`}>
        {busy ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Upload className="size-4" aria-hidden />}
        {label}
        <input
          type="file"
          accept="application/pdf,.pdf"
          className="sr-only"
          disabled={busy}
          onChange={(e) => {
            const f = e.target.files?.[0];
            e.target.value = "";
            if (f) void carica(f);
          }}
        />
      </label>
      {errore && <p className="text-sm text-danger">{errore}</p>}
    </div>
  );
}

// Passo 5: dopo la radiazione e non prima di 120 giorni dal CRD si distruggono targhe e documenti; la data va nel RVFU.
function Distruzione({ v }: { v: Vehicle }) {
  const { updateVehicle, operatore } = useStore();
  const oggi = giorno(new Date());
  const dal = giorno(distruzioneDal(v)!);
  const [cosa, setCosa] = useState(() => new Set(DISTRUZIONE.map((d) => d.key)));
  const [data, setData] = useState(oggi);
  if (oggi < dal) return null;
  const dataOk = !!data && data >= dal && data <= oggi;

  return (
    <div className="space-y-2.5">
      <fieldset className="space-y-1">
        <legend className="text-sm font-semibold">Cosa è stato distrutto</legend>
        {DISTRUZIONE.map((d) => (
          <label key={d.key} className="flex min-h-10 items-center gap-2.5 text-sm">
            <input
              type="checkbox"
              className="size-5 shrink-0 accent-band"
              checked={cosa.has(d.key)}
              onChange={(e) =>
                setCosa((s) => {
                  const n = new Set(s);
                  if (e.target.checked) n.add(d.key);
                  else n.delete(d.key);
                  return n;
                })
              }
            />
            {d.label}
          </label>
        ))}
      </fieldset>
      <input type="date" className="field h-11" value={data} min={dal} max={oggi} onChange={(e) => setData(e.target.value)} aria-label="Data della distruzione" />
      {!dataOk && data && <p className="text-sm text-danger">La data deve essere tra il {dateIt(daGiorno(dal))} e oggi.</p>}
      <p className="text-[13px] text-ink-3">Targhe smarrite o rubate: togli la spunta, vale la denuncia ricevuta al passo 1. La data va annotata nel RVFU (simulato).</p>
      <Button
        size="sm"
        disabled={cosa.size === 0 || !dataOk}
        onClick={() => {
          const voci = DISTRUZIONE.filter((d) => cosa.has(d.key));
          updateVehicle(v.id, { distruzione: { at: daGiorno(data), by: operatore ? `${operatore.nome}${operatore.assistenza ? " (assistenza)" : ""}` : "Operatore", cosa: voci.map((d) => d.key) } }, "Targhe e documenti distrutti", voci.map((d) => d.label).join(", "));
        }}
      >
        Registra la distruzione
      </Button>
    </div>
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
