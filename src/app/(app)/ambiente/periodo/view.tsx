"use client";

import Link from "next/link";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { CircleCheck, Download, Send } from "lucide-react";
import { useStore } from "@/lib/store";
import { EER, eerByCode, fmtKg } from "@/lib/ambiente";
import { CAUSALE_LABEL, canTransmit, correctedIds, duplicateIds, isDraft, kgText, MISSING_TEXT, missingFields, monthStock, moveIssues, parseKg, periodsOf, rigaRentri, type Period } from "@/lib/periodo";
import { dateIt } from "@/lib/logic";
import { Button, Field, Notice, PageTitle, Panel } from "@/components/ui";
import type { Fir, Vehicle, WasteMove } from "@/lib/types";

const DAY = 864e5;

export default function Page() {
  return (
    <Suspense>
      <Periodo />
    </Suspense>
  );
}

// Il lavoro mensile della consulente: controllare il mese, completare le bozze, rettificare o annullare, trasmettere.
function Periodo() {
  const sp = useSearchParams();
  const { wasteMoves, firs, vehicles, transmitPeriod } = useStore();
  const periods = periodsOf(wasteMoves, firs);
  // Il mese di serie (il primo da trasmettere) si fissa all'apertura: dopo la trasmissione si resta su quel mese
  const [initial] = useState(() => (periods.find((x) => x.status === "da trasmettere") ?? periods.at(-1))?.key);
  const p = periods.find((x) => x.key === (sp.get("mese") ?? initial)) ?? periods.at(-1);
  const [msg, setMsg] = useState<{ tone: "ok" | "danger"; text: string } | null>(null);
  if (!p) return <p className="p-8">Nessuna registrazione nel registro.</p>;

  const firById = new Map(firs.map((f) => [f.id, f]));
  const rows = monthStock(wasteMoves, p.key, EER.map((e) => ({ code: e.code, limitKg: e.limitKg }))).filter((r) => r.carichi || r.scarichi || r.giacenza);
  // Prima le bozze, poi le registrazioni in ordine di numero
  const list = [...p.moves].sort((a, b) => Number(!isDraft(a)) - Number(!isDraft(b)) || (a.numero ?? 0) - (b.numero ?? 0));
  const cancelledBy = new Map(wasteMoves.filter((m) => m.annullaDi).map((m) => [m.annullaDi!, m]));
  const rectifiedBy = new Map(wasteMoves.filter((m) => m.rettificaDi).map((m) => [m.rettificaDi!, m]));
  const dups = duplicateIds(wasteMoves);
  const corrected = correctedIds(wasteMoves);

  return (
    <div className="mx-auto max-w-5xl">
      <PageTitle
        title="Periodo RENTRI"
        sub="Le registrazioni di un mese si trasmettono al RENTRI entro la fine del mese successivo. Una registrazione numerata non si modifica: si rettifica o si annulla con una registrazione nuova."
      />
      {msg && <div className="mb-5"><Notice tone={msg.tone}>{msg.text}</Notice></div>}

      <nav aria-label="Mesi" className="mb-5 flex flex-wrap gap-2">
        {periods.map((x) => (
          <Link
            key={x.key}
            href={`/ambiente/periodo?mese=${x.key}`}
            aria-current={x.key === p.key ? "page" : undefined}
            className={`inline-flex min-h-11 items-center gap-2 rounded-md border-2 px-3 font-semibold ${x.key === p.key ? "border-band bg-band-tint text-band-deep" : "border-hair bg-label text-ink hover:border-band"}`}
          >
            <span className="capitalize">{x.label}</span>
            <StatusDot p={x} />
          </Link>
        ))}
      </nav>

      <Stato
        p={p}
        onTransmit={() => {
          const r = transmitPeriod(p.key);
          setMsg(r.ok ? { tone: "ok", text: `Periodo di ${p.label} trasmesso. Ricevuta ${r.value} (trasmissione simulata).` } : { tone: "danger", text: r.error });
        }}
        onDownload={() => downloadCsv(p, firById, wasteMoves)}
      />

      <Panel title={`Totali per codice · ${p.label}`} className="mt-6">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-left text-[15px]">
            <thead className="text-sm text-ink-3">
              <tr>
                <th className="px-4 py-2 font-semibold">Codice</th>
                <th className="px-4 py-2 text-right font-semibold">Carichi</th>
                <th className="px-4 py-2 text-right font-semibold">Scarichi</th>
                <th className="px-4 py-2 text-right font-semibold">Giacenza a fine mese</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-hair-soft">
              {rows.map((r) => (
                <tr key={r.code}>
                  <td className="px-4 py-2">
                    <span className="code font-semibold">{r.code}</span> <span className="text-ink-2">{eerByCode(r.code)?.short}</span>
                  </td>
                  <td className="code px-4 py-2 text-right">{fmtKg(r.carichi)}</td>
                  <td className="code px-4 py-2 text-right">{fmtKg(r.scarichi)}</td>
                  <td className={`code px-4 py-2 text-right font-bold ${r.over || r.negative ? "text-danger" : ""}`}>
                    {r.negative ? `−${fmtKg(-r.giacenza)}` : fmtKg(r.giacenza)}
                    {r.over && <span className="ml-2 font-sans text-sm font-semibold">oltre il limite di {fmtKg(r.limitKg)}</span>}
                    {r.negative && <span className="ml-2 font-sans text-sm font-semibold">giacenza negativa: manca un carico o c&apos;è uno scarico in più</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title={`Registrazioni · ${p.moves.length}`} className="mt-6">
        <ul className="divide-y divide-hair-soft">
          {list.map((m) => (
            <Riga
              key={`${m.id}|${m.at}`}
              m={m}
              fir={m.fir ? firById.get(m.fir) : undefined}
              cancelled={cancelledBy.get(m.id)}
              rectified={rectifiedBy.get(m.id)}
              corrected={corrected.has(m.id)}
              duplicate={dups.has(m.id)}
              all={wasteMoves}
              vehicle={vehicles.find((v) => v.id === m.origin)}
              onMsg={setMsg}
            />
          ))}
        </ul>
      </Panel>
      <p className="mt-3 text-[13px] text-ink-3">Prototipo: la trasmissione al RENTRI è simulata. Fonti: DM 59/2023 art. 15 (trasmissione mensile), art. 190 D.Lgs. 152/2006 (annotazione entro 2 giorni lavorativi), manuale RENTRI del registro (rettifica e annullamento).</p>
    </div>
  );
}

function StatusDot({ p }: { p: Period }) {
  if (p.status === "trasmesso") return <CircleCheck className="size-4 text-ok" aria-label="trasmesso" />;
  if (p.status === "aperto") return <span className="text-sm font-normal text-ink-3">in corso</span>;
  return <span className={`size-2.5 rounded-full ${p.drafts ? "bg-danger" : "bg-warn"}`} aria-label="da trasmettere" />;
}

function Stato({ p, onTransmit, onDownload }: { p: Period; onTransmit: () => void; onDownload: () => void }) {
  const [now] = useState(() => Date.now());
  const left = new Date(p.deadline).getTime() - now;
  const late = p.status === "da trasmettere" && left < 0;
  const soon = p.status === "da trasmettere" && !late && left < 7 * DAY;
  const deadline = new Date(p.deadline).toLocaleDateString("it-IT", { day: "numeric", month: "long", year: "numeric" });
  const tone = p.status === "trasmesso" ? "border-ok bg-ok-bg" : late ? "border-danger bg-danger-bg" : soon ? "border-warn bg-warn-bg" : "border-hair bg-label";
  return (
    <section className={`rounded-md border-2 px-4 py-4 ${tone}`} aria-live="polite">
      <p className="text-[22px] font-bold capitalize leading-tight">{p.label}</p>
      <p className="mt-1 text-[16px]">
        {p.status === "trasmesso" && <>Trasmesso al RENTRI · ricevuta <span className="code font-semibold">{p.ricevuta}</span></>}
        {p.status === "aperto" && <>Mese in corso: si trasmette dal 1° del mese prossimo, entro il {deadline}.</>}
        {p.status === "da trasmettere" && (
          <>
            Da trasmettere <b>entro il {deadline}</b>
            {late && <b className="text-danger"> · scaduto</b>}
            {soon && <b className="text-warn"> · mancano {Math.ceil(left / DAY)} giorni</b>}
          </>
        )}
      </p>
      <p className="mt-1 text-sm text-ink-2">
        {p.moves.length} registrazioni · {p.drafts ? <b className="text-danger">{p.drafts} {p.drafts === 1 ? "bozza" : "bozze"} da completare</b> : "nessuna bozza"} · {p.warnings} {p.warnings === 1 ? "avviso" : "avvisi"}
        {p.duplicates > 0 && <b className="text-danger"> · {p.duplicates} numeri di registro doppi: correggili con un annullamento prima di trasmettere</b>}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {p.status === "da trasmettere" && (
          <Button disabled={!canTransmit(p)} onClick={onTransmit}>
            <Send className="size-5" aria-hidden /> Trasmetti il periodo al RENTRI
          </Button>
        )}
        <Button variant="secondary" onClick={onDownload}>
          <Download className="size-5" aria-hidden /> Scarica riepilogo
        </Button>
      </div>
      {p.status === "da trasmettere" && p.drafts > 0 && <p className="mt-2 text-sm text-ink-2">Prima completa le bozze qui sotto: una bozza non è ancora nel registro.</p>}
    </section>
  );
}

function Riga({
  m,
  fir,
  cancelled,
  rectified,
  corrected,
  duplicate,
  all,
  vehicle,
  onMsg,
}: {
  m: WasteMove;
  fir?: Fir;
  cancelled?: WasteMove;
  rectified?: WasteMove;
  corrected: boolean;
  duplicate: boolean;
  all: WasteMove[];
  vehicle?: Vehicle;
  onMsg: (x: { tone: "ok" | "danger"; text: string }) => void;
}) {
  const { completeDraft, rectifyMove, cancelMove, confirmMove } = useStore();
  const [mode, setMode] = useState<"none" | "rett" | "ann">("none");
  const [kg, setKg] = useState(kgText(m.kg));
  const [motivo, setMotivo] = useState("");
  // Si ricava tutto quello che il gestionale sa già (conferente e pratica del veicolo); il resto si scrive
  const [nome, setNome] = useState(m.produttore?.nome || vehicle?.conferente?.nome || "");
  const [cf, setCf] = useState(m.produttore?.cf ?? vehicle?.conferente?.cf ?? "");
  const [crdNum, setCrdNum] = useState(m.certificato?.numero ?? vehicle?.dossier.number ?? "");
  const [crdData, setCrdData] = useState((m.certificato?.data ?? vehicle?.presaInCarico?.at)?.slice(0, 10) ?? "");
  const [pesa, setPesa] = useState(m.pesoPesa ? kgText(m.kg) : "");
  const [note, setNote] = useState<{ tone: "ok" | "danger"; text: string } | null>(null);
  const issues = moveIssues(m, fir, corrected, all);
  const draft = isDraft(m);
  const missing = draft ? missingFields(m, all) : [];
  const e = eerByCode(m.eer);

  return (
    <li className={`px-4 py-3 ${draft ? "bg-warn-bg/40" : ""} ${cancelled ? "opacity-60" : ""}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <span className="flex flex-wrap items-baseline gap-x-3">
          <span className="code w-16 text-[16px] font-bold">{draft ? <span className="text-warn">bozza</span> : `n. ${m.numero}`}</span>
          <span className="text-sm text-ink-3">{dateIt(m.registeredAt ?? m.at, true)}</span>
          <span className="text-sm font-semibold text-ink-2">{m.causale ? CAUSALE_LABEL[m.causale] : m.kind}</span>
        </span>
        <span className="code text-[18px] font-bold">
          {m.causale === "ANN" ? "annulla" : `${m.causale === "RETT" ? "= " : m.kind === "carico" ? "+" : "−"}${fmtKg(m.kg)}`}
        </span>
      </div>
      <p className="mt-0.5">
        <span className="code font-semibold">{m.eer}</span> <span className="text-ink-2">{e?.short}</span>
        <span className="text-sm text-ink-3"> · provenienza {m.provenienza ?? "S"}</span>
        {m.statoFisico && <span className="text-sm text-ink-3"> · stato {m.statoFisico}</span>}
        {!!m.hp?.length && <span className="text-sm text-ink-3"> · {m.hp.join(", ")}</span>}
        {m.operazione && <span className="text-sm text-ink-3"> · {m.operazione}</span>}
      </p>
      <p className="text-sm text-ink-2">
        {m.vfu && <>Veicolo fuori uso · </>}
        {m.stimato && <>peso stimato per modello · </>}
        {m.causale === "T*" && m.kgLibretto && <>libretto {fmtKg(m.kgLibretto)} · </>}
        {m.verificato && <>controllata da {m.verificato.by} · </>}
        {m.produttore && <>{m.produttore.nome}{m.produttore.cf ? <> · <span className="code">{m.produttore.cf}</span></> : ""} · </>}
        {m.certificato && <>certificato <span className="code">{m.certificato.numero}</span> del {dateIt(m.certificato.data)} · </>}
        {fir && <>formulario <span className="code">{fir.numero ?? fir.id}</span> · {fir.destinatario} · </>}
        {m.motivo && <>motivo: {m.motivo} · </>}
        <Link href={m.origin.startsWith("V-") ? `/veicoli/${m.origin}` : "/ambiente/formulari"} className="code font-semibold text-band underline">{m.origin}</Link>
      </p>
      {(issues.length > 0 || cancelled || rectified || duplicate) && (
        <ul className="mt-1.5 flex flex-wrap gap-1.5">
          {issues.map((i) => (
            <li key={i.code} className={`rounded px-2 py-0.5 text-[13px] font-semibold ${i.blocking ? "bg-danger text-white" : "bg-warn-bg text-ink"}`}>{i.text}</li>
          ))}
          {duplicate && <li className="rounded bg-danger px-2 py-0.5 text-[13px] font-semibold text-white">Numero di registro doppio</li>}
          {cancelled && <li className="rounded bg-ink px-2 py-0.5 text-[13px] font-semibold text-white">Annullata dalla n. {cancelled.numero}</li>}
          {rectified && !cancelled && <li className="rounded bg-band-tint px-2 py-0.5 text-[13px] font-semibold text-band-deep">Rettificata dalla n. {rectified.numero}: {fmtKg(rectified.kg)}</li>}
        </ul>
      )}

      {draft && missing.includes("carico") && (
        <p className="mt-2 text-sm text-ink-2">Si registra da sola quando è completa la {MISSING_TEXT.carico} del veicolo.</p>
      )}
      {draft && !missing.includes("carico") && (
        <div className="mt-3 grid gap-3 rounded-md border border-hair bg-label p-3 sm:grid-cols-3">
          {missing.includes("produttore") && (
            <Field label="Nome di chi conferisce">
              <input className="field" value={nome} onChange={(ev) => setNome(ev.target.value)} />
            </Field>
          )}
          {missing.includes("cf-produttore") && (
            <Field label="Codice fiscale di chi conferisce">
              <input className="field code uppercase" value={cf} onChange={(ev) => setCf(ev.target.value.toUpperCase())} />
            </Field>
          )}
          {missing.includes("certificato") && (
            <>
              <Field label="N. certificato di rottamazione">
                <input className="field code uppercase" value={crdNum} onChange={(ev) => setCrdNum(ev.target.value.toUpperCase())} />
              </Field>
              <Field label="Data del certificato">
                <input type="date" className="field" value={crdData} onChange={(ev) => setCrdData(ev.target.value)} />
              </Field>
            </>
          )}
          {missing.includes("peso") && (
            <Field label="Peso della pesa (kg)" hint={`Da libretto: ${fmtKg(m.kg)}`}>
              <input className="field code font-bold" inputMode="decimal" value={pesa} onChange={(ev) => setPesa(ev.target.value.replace(/[^0-9.,]/g, ""))} />
            </Field>
          )}
          <div className="flex flex-wrap items-center gap-3 sm:col-span-3">
            <Button
              size="sm"
              onClick={() => {
                // Prima si controlla cosa manca, e lo si dice qui accanto (non in cima alla pagina, dove non si vede)
                const w = missing.includes("peso") ? parseKg(pesa) : null;
                const lacks = [
                  missing.includes("produttore") && !nome.trim() ? "il nome di chi conferisce" : "",
                  missing.includes("cf-produttore") && !cf.trim() ? "il codice fiscale" : "",
                  missing.includes("certificato") && (!crdNum.trim() || !crdData) ? "numero e data del certificato" : "",
                  missing.includes("peso") && !w ? "il peso della pesa in kg" : "",
                ].filter(Boolean);
                if (lacks.length) return setNote({ tone: "danger", text: `Scrivi ${lacks.join(", ")}.` });
                const r = completeDraft(m.id, {
                  ...(missing.includes("produttore") ? { produttoreNome: nome } : {}),
                  ...(missing.includes("cf-produttore") ? { produttoreCf: cf } : {}),
                  ...(missing.includes("certificato") && crdNum.trim() && crdData ? { certificato: { numero: crdNum.trim(), data: new Date(crdData).toISOString() } } : {}),
                  ...(w ? { kg: w, pesoPesa: true } : {}),
                });
                const out = !r.ok
                  ? { tone: "danger" as const, text: r.error }
                  : r.value
                    ? { tone: "ok" as const, text: "Registrata oggi con il suo numero: entra nel periodo del mese in corso." }
                    : { tone: "danger" as const, text: "Bozza aggiornata, ma manca ancora qualche dato: non ha ancora un numero." };
                setNote(out);
                onMsg(out);
              }}
            >
              Completa la registrazione
            </Button>
            {note && <span role="status" className={`text-[15px] font-semibold ${note.tone === "ok" ? "text-ok" : "text-danger"}`}>{note.text}</span>}
          </div>
        </div>
      )}

      {!draft && m.causale !== "ANN" && !cancelled && (
        <div className="mt-2">
          {mode === "none" && (
            <span className="flex gap-2">
              {issues.some((i) => i.code === "diff-pesata" || i.code === "peso-diverso") && (
                <Button size="sm" variant="secondary" onClick={() => { confirmMove(m.id); onMsg({ tone: "ok", text: "Segnata come controllata." }); }}>Va bene così</Button>
              )}
              {m.causale !== "RETT" && (
                <Button size="sm" variant="quiet" onClick={() => setMode("rett")}>Rettifica</Button>
              )}
              <Button size="sm" variant="quiet" onClick={() => setMode("ann")}>Annulla</Button>
            </span>
          )}
          {mode !== "none" && (
            <div className="mt-1 grid gap-3 rounded-md border border-hair bg-label p-3 sm:grid-cols-3">
              {mode === "rett" && (
                <Field label="Kg corretti">
                  <input className="field code font-bold" inputMode="decimal" value={kg} onChange={(ev) => setKg(ev.target.value.replace(/[^0-9.,]/g, ""))} />
                </Field>
              )}
              <Field label={mode === "rett" ? "Motivo della rettifica" : "Motivo dell'annullamento"}>
                <input className="field" value={motivo} onChange={(ev) => setMotivo(ev.target.value)} />
              </Field>
              <div className="flex items-end gap-2">
                <Button
                  size="sm"
                  variant={mode === "ann" ? "danger" : "primary"}
                  onClick={() => {
                    const r = mode === "rett" ? rectifyMove(m.id, parseKg(kg) ?? 0, motivo) : cancelMove(m.id, motivo);
                    onMsg(r.ok ? { tone: "ok", text: mode === "rett" ? "Rettifica registrata con un nuovo numero." : "Annullamento registrato con un nuovo numero." } : { tone: "danger", text: r.error });
                    if (r.ok) setMode("none");
                  }}
                >
                  {mode === "rett" ? "Registra rettifica" : "Registra annullamento"}
                </Button>
                <Button size="sm" variant="quiet" onClick={() => setMode("none")}>Chiudi</Button>
              </div>
            </div>
          )}
        </div>
      )}
    </li>
  );
}

// Riepilogo del periodo (la strada di riserva: la consulente lo può caricare con un suo strumento)
// Colonne e codici come nel registro RENTRI: causale (T*, NP, I, aT), provenienza (U/S), classi HP01–HP15,
// rettifica e annullamento con il numero/anno della registrazione richiamata.
function downloadCsv(p: Period, firById: Map<string, Fir>, all: WasteMove[]) {
  const cols = ["numero", "data registrazione", "data operazione", "causale RENTRI", "carico/scarico", "codice EER", "provenienza", "stato fisico", "classi di pericolo", "kg", "attivita", "veicolo fuori uso", "certificato rottamazione", "data certificato", "produttore", "codice fiscale", "formulario", "destinatario", "rettifica reg. nr.", "annulla reg. nr.", "motivo", "nota", "RENTRI"];
  // Dati salvati con «HP3»: il RENTRI vuole HP03
  const hpRentri = (hp?: string[]) => hp?.map((h) => h.replace(/^HP(\d)$/, "HP0$1")).join(" ");
  // Un testo che inizia con = + - @ verrebbe eseguito come formula da Excel: si neutralizza con un apostrofo
  const cell = (v: unknown) => {
    const t = String(v ?? "");
    return `"${(/^[=+\-@\t\r]/.test(t) ? `'${t}` : t).replace(/"/g, '""')}"`;
  };
  const lines = p.moves.map((m) => {
    const f = m.fir ? firById.get(m.fir) : undefined;
    const r = rigaRentri(m, all);
    return [
      m.numero ?? "bozza",
      m.registeredAt?.slice(0, 10),
      m.at.slice(0, 10),
      r.causale,
      m.kind,
      m.eer,
      r.provenienza,
      m.statoFisico,
      hpRentri(m.hp),
      String(m.kg).replace(".", ","),
      m.operazione,
      m.vfu ? "si" : "",
      m.certificato?.numero,
      m.certificato?.data?.slice(0, 10),
      m.produttore?.nome,
      m.produttore?.cf,
      f?.numero,
      f?.destinatario,
      r.rettificaDi,
      r.annullaDi,
      m.motivo,
      r.nota,
      m.rentri,
    ].map(cell).join(";");
  });
  const blob = new Blob(["﻿" + [cols.map(cell).join(";"), ...lines].join("\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `registro-rifiuti-${p.key}.csv`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
