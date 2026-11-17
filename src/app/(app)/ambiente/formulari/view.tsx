"use client";

import Link from "next/link";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { FilePlus2 } from "lucide-react";
import { useStore } from "@/lib/store";
import { eerByCode, fmtKg, stockByEer } from "@/lib/ambiente";
import { firNumberLooksValid, kgText, parseKg } from "@/lib/periodo";
import { dateIt } from "@/lib/logic";
import { Button, Field, Notice, PageTitle, Panel } from "@/components/ui";
import type { Fir, FirStatus, Soggetto } from "@/lib/types";

const FIR_TONE: Record<FirStatus, string> = {
  "da firmare": "bg-warn-bg text-warn",
  firmato: "bg-band-tint text-band",
  accettato: "bg-ok-bg text-ok",
};
const ESITO: Record<NonNullable<Fir["esito"]>, string> = { accettato: "accettato per intero", parziale: "accettato in parte", respinto: "respinto" };

const today = () => new Date().toISOString().slice(0, 10);
const nowLocal = () => {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
};

export default function Page() {
  return (
    <Suspense>
      <Formulari />
    </Suspense>
  );
}

// I formulari li compila e li vidima la ditta che ritira: qui si registrano, si firmano e si segna l'esito
function Formulari() {
  const sp = useSearchParams();
  const { firs, wasteMoves, soggetti, receiveFir, signFir, setFirOutcome } = useStore();
  const [open, setOpen] = useState(!!sp.get("eer"));
  const [msg, setMsg] = useState<{ tone: "ok" | "danger"; text: string } | null>(null);
  const [outcomeFor, setOutcomeFor] = useState<string | null>(null);
  const nome = (id?: string) => soggetti.find((x) => x.id === id)?.nome;
  const ordered = [...firs].sort((a, b) => Number(a.status === "accettato") - Number(b.status === "accettato") || b.at.localeCompare(a.at));

  return (
    <div className="mx-auto max-w-5xl">
      <PageTitle
        title="Formulari"
        sub="Il formulario lo porta la ditta che ritira, già vidimato. Qui lo registri e lo firmi: lo scarico entra da solo nel registro. Al ritorno segni quanto ha accettato il destinatario."
        actions={!open && <Button onClick={() => setOpen(true)}><FilePlus2 className="size-5" aria-hidden /> Registra formulario ricevuto</Button>}
      />
      {msg && <div className="mb-5"><Notice tone={msg.tone}>{msg.text}</Notice></div>}

      {open && (
        <NuovoFormulario
          soggetti={soggetti}
          stock={stockByEer(wasteMoves).filter((s) => s.code !== "16 01 04*")}
          pre={sp.get("eer")}
          onCancel={() => setOpen(false)}
          onSave={(f) => {
            const r = receiveFir(f);
            if (!r.ok) return setMsg({ tone: "danger", text: r.error });
            setMsg({ tone: "ok", text: `Formulario ${f.numero} registrato: firmalo quando il carico parte.` });
            setOpen(false);
          }}
        />
      )}

      <ul className="space-y-3">
        {ordered.map((f) => {
          const e = eerByCode(f.eer);
          const move = wasteMoves.find((m) => m.fir === f.id);
          return (
            <li key={f.id} className="label-sheet p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="code text-[24px] font-bold leading-none">{f.numero ?? f.id}</span>
                    <span className={`code inline-flex h-7 items-center rounded px-2.5 text-[13px] font-semibold uppercase tracking-wide ${FIR_TONE[f.status]}`}>{f.status}</span>
                  </div>
                  <p className="mt-2 font-semibold">
                    <span className="code">{f.eer}</span> {e?.short} · <span className="code">{fmtKg(f.kg)}</span>
                    {f.rinfusa && <span className="font-normal text-ink-2"> · alla rinfusa</span>}
                  </p>
                  <p className="text-sm text-ink-2">
                    Destinatario {f.destinatario ?? nome(f.destinatarioId)} · trasporto {f.trasportatore ?? nome(f.trasportatoreId)}
                    {f.intermediarioId && <> · intermediario {nome(f.intermediarioId)}</>}
                  </p>
                  {(f.targa || f.conducente) && (
                    <p className="text-sm text-ink-3">
                      {f.targa && <>Targa <span className="code">{f.targa}</span></>} {f.conducente && <>· conducente {f.conducente}</>}
                      {f.inizioTrasportoAt && <> · partenza {dateIt(f.inizioTrasportoAt, true)}</>}
                    </p>
                  )}
                  {f.esito && (
                    <p className={`mt-1 text-sm font-semibold ${f.esito === "accettato" ? "text-ok" : "text-warn"}`}>
                      Destinatario: {ESITO[f.esito]}
                      {f.esito === "parziale" && ` · ${fmtKg(f.kgAccettati ?? 0)} su ${fmtKg(f.kg)}`}
                      {f.arrivoAt && ` · arrivo ${dateIt(f.arrivoAt)}`}
                    </p>
                  )}
                  {move && (
                    <p className="text-sm text-ink-3">
                      Nel registro: <Link href="/ambiente" className="code font-semibold text-band underline">{move.numero ? `n. ${move.numero}` : "bozza"}</Link>
                    </p>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  {f.status === "da firmare" && (
                    <Button
                      size="sm"
                      onClick={() => {
                        const r = signFir(f.id);
                        setMsg(r.ok ? { tone: "ok", text: `Formulario ${f.numero ?? f.id} firmato: scarico registrato.` } : { tone: "danger", text: r.error });
                      }}
                    >
                      Firma
                    </Button>
                  )}
                  {f.status !== "da firmare" && outcomeFor !== f.id && (
                    <Button size="sm" variant={f.esito ? "quiet" : "secondary"} onClick={() => setOutcomeFor(f.id)}>
                      {f.esito ? "Correggi esito" : "Esito del destinatario"}
                    </Button>
                  )}
                </div>
              </div>
              {outcomeFor === f.id && (
                <EsitoForm
                  fir={f}
                  onCancel={() => setOutcomeFor(null)}
                  onSave={(esito, kg, arrivo) => {
                    const r = setFirOutcome(f.id, esito, kg, arrivo);
                    setMsg(r.ok ? { tone: "ok", text: `Esito registrato: ${ESITO[esito]}.` } : { tone: "danger", text: r.error });
                    if (r.ok) setOutcomeFor(null);
                  }}
                />
              )}
              <ol className="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-hair-soft pt-2 text-[13px] text-ink-3">
                {f.history.map((h, i) => (
                  <li key={i}>
                    <span className="font-semibold text-ink-2">{h.status}</span> {dateIt(h.at, true)} · {h.by}
                  </li>
                ))}
              </ol>
            </li>
          );
        })}
      </ul>
      <p className="mt-3 text-[13px] text-ink-3">Prototipo: i dati del formulario si ricopiano a mano. Con il collegamento al RENTRI si potranno scaricare dal numero del formulario.</p>
    </div>
  );
}

function NuovoFormulario({
  soggetti,
  stock,
  pre,
  onSave,
  onCancel,
}: {
  soggetti: Soggetto[];
  stock: ReturnType<typeof stockByEer>;
  pre: string | null;
  onSave: (f: Parameters<ReturnType<typeof useStore.getState>["receiveFir"]>[0]) => void;
  onCancel: () => void;
}) {
  const inStock = stock.filter((s) => s.kg > 0);
  const of = (r: Soggetto["ruolo"]) => soggetti.filter((x) => x.ruolo === r);
  const [numero, setNumero] = useState("");
  const [emesso, setEmesso] = useState(today());
  const [eer, setEer] = useState(pre && inStock.some((s) => s.code === pre) ? pre : (inStock[0]?.code ?? ""));
  const [kg, setKg] = useState("");
  const [rinfusa, setRinfusa] = useState(true);
  const [svuota, setSvuota] = useState(true);
  const [dest, setDest] = useState(of("destinatario")[0]?.id ?? "");
  const [carrier, setCarrier] = useState(of("trasportatore")[0]?.id ?? "");
  const [broker, setBroker] = useState("");
  const [targa, setTarga] = useState("");
  const [conducente, setConducente] = useState("");
  const [partenza, setPartenza] = useState(nowLocal());
  const [note, setNote] = useState("");
  const cur = inStock.find((s) => s.code === eer);
  const kgNum = parseKg(kg);
  const tooMuch = !svuota && !!(cur && kgNum && kgNum > cur.kg);
  const diff = svuota && cur && kgNum ? Math.round((kgNum - cur.kg) * 10) / 10 : 0;
  const oddNumber = numero.trim() !== "" && !firNumberLooksValid(numero);
  const canSave = numero.trim() && eer && kgNum && !tooMuch && dest && carrier;

  return (
    <Panel title="Formulario ricevuto" className="mb-6">
      <div className="grid gap-4 p-4 sm:grid-cols-2">
        <Field label="Numero del formulario" hint="Quello stampato in alto, es. JNMPC 00262 JC" error={oddNumber ? "Formato insolito: controlla, ma puoi salvarlo" : undefined}>
          <input className="field code text-[18px] font-bold uppercase" value={numero} onChange={(e) => setNumero(e.target.value.toUpperCase())} />
        </Field>
        <Field label="Data di emissione">
          <input type="date" className="field" value={emesso} onChange={(e) => setEmesso(e.target.value)} />
        </Field>
        <Field label="Rifiuto">
          <select className="field" value={eer} onChange={(e) => setEer(e.target.value)}>
            {inStock.map((s) => <option key={s.code} value={s.code}>{s.code} · {s.short} · {fmtKg(s.kg)} in giacenza</option>)}
          </select>
        </Field>
        <Field
          label={svuota ? "Peso della pesata (kg)" : "Quantità (kg)"}
          hint={cur ? `In giacenza (stimata) ${fmtKg(cur.kg)}${diff ? ` · differenza di pesata ${diff > 0 ? "+" : "−"}${fmtKg(Math.abs(diff))}, registrata da sola alla firma` : ""}` : undefined}
          error={tooMuch ? "Più di quanto in giacenza" : undefined}
        >
          <input className="field code text-[18px] font-bold" inputMode="decimal" value={kg} onChange={(e) => setKg(e.target.value.replace(/[^0-9.,]/g, ""))} />
        </Field>
        <Field label="Destinatario">
          <select className="field" value={dest} onChange={(e) => setDest(e.target.value)}>
            {of("destinatario").map((x) => <option key={x.id} value={x.id}>{x.nome}{x.operazione ? ` · ${x.operazione}` : ""}</option>)}
          </select>
        </Field>
        <Field label="Trasportatore">
          <select className="field" value={carrier} onChange={(e) => setCarrier(e.target.value)}>
            {of("trasportatore").map((x) => <option key={x.id} value={x.id}>{x.nome}{x.albo ? ` · Albo ${x.albo}` : ""}</option>)}
          </select>
        </Field>
        <Field label="Intermediario (se c'è)">
          <select className="field" value={broker} onChange={(e) => setBroker(e.target.value)}>
            <option value="">Nessuno</option>
            {of("intermediario").map((x) => <option key={x.id} value={x.id}>{x.nome}</option>)}
          </select>
        </Field>
        <label className="flex min-h-11 items-center gap-2 self-end">
          <input type="checkbox" className="size-5 accent-[var(--band)]" checked={rinfusa} onChange={(e) => setRinfusa(e.target.checked)} />
          <span>Alla rinfusa</span>
        </label>
        <label className="flex min-h-11 items-start gap-2 sm:col-span-2">
          <input type="checkbox" className="mt-0.5 size-5 shrink-0 accent-[var(--band)]" checked={svuota} onChange={(e) => setSvuota(e.target.checked)} />
          <span>
            <span className="font-semibold">Parte tutto il contenitore di questo rifiuto</span>
            <span className="block text-sm text-ink-3">Il peso della pesata è quello vero: la giacenza stimata si corregge da sola con una differenza di pesata.</span>
          </span>
        </label>
        <Field label="Targa del mezzo">
          <input className="field code uppercase" value={targa} onChange={(e) => setTarga(e.target.value.toUpperCase().replace(/\s+/g, ""))} />
        </Field>
        <Field label="Conducente">
          <input className="field" value={conducente} onChange={(e) => setConducente(e.target.value)} />
        </Field>
        <Field label="Inizio del trasporto">
          <input type="datetime-local" className="field" value={partenza} onChange={(e) => setPartenza(e.target.value)} />
        </Field>
        <Field label="Annotazioni">
          <input className="field" value={note} onChange={(e) => setNote(e.target.value)} />
        </Field>
        <p className="text-sm text-ink-3 sm:col-span-2">
          <Link href="/ambiente/soggetti" className="font-semibold text-band underline">Anagrafica soggetti</Link>: destinatari, trasportatori e intermediari si inseriscono una volta.
        </p>
        <div className="flex flex-wrap gap-2 sm:col-span-2">
          <Button
            disabled={!canSave}
            onClick={() =>
              onSave({
                numero: numero.trim(),
                emessoAt: new Date(emesso).toISOString(),
                eer,
                kg: kgNum!,
                destinatarioId: dest,
                trasportatoreId: carrier,
                intermediarioId: broker || undefined,
                targa: targa || undefined,
                conducente: conducente.trim() || undefined,
                inizioTrasportoAt: partenza ? new Date(partenza).toISOString() : undefined,
                rinfusa,
                svuota,
                annotazioni: note.trim() || undefined,
              })
            }
          >
            Registra formulario
          </Button>
          <Button variant="quiet" onClick={onCancel}>Annulla</Button>
        </div>
      </div>
    </Panel>
  );
}

function EsitoForm({ fir, onSave, onCancel }: { fir: Fir; onSave: (esito: NonNullable<Fir["esito"]>, kg: number, arrivo: string) => void; onCancel: () => void }) {
  const [esito, setEsito] = useState<NonNullable<Fir["esito"]>>(fir.esito ?? "accettato");
  const [kg, setKg] = useState(fir.kgAccettati !== undefined ? kgText(fir.kgAccettati) : "");
  const [arrivo, setArrivo] = useState(fir.arrivoAt?.slice(0, 10) ?? today());
  const kgNum = parseKg(kg);
  return (
    <div className="mt-3 grid gap-3 rounded-md border border-hair bg-carton p-3 sm:grid-cols-3">
      <Field label="Esito">
        <select className="field" value={esito} onChange={(e) => setEsito(e.target.value as NonNullable<Fir["esito"]>)}>
          {(Object.keys(ESITO) as NonNullable<Fir["esito"]>[]).map((k) => <option key={k} value={k}>{ESITO[k]}</option>)}
        </select>
      </Field>
      {esito === "parziale" && (
        <Field label="Kg accettati" hint={`Partiti ${fmtKg(fir.kg)}`}>
          <input className="field code font-bold" inputMode="decimal" value={kg} onChange={(e) => setKg(e.target.value.replace(/[^0-9.,]/g, ""))} />
        </Field>
      )}
      <Field label="Data di arrivo">
        <input type="date" className="field" value={arrivo} onChange={(e) => setArrivo(e.target.value)} />
      </Field>
      <div className="flex flex-wrap gap-2 sm:col-span-3">
        <Button size="sm" disabled={esito === "parziale" && !kgNum} onClick={() => onSave(esito, kgNum ?? 0, new Date(arrivo).toISOString())}>Salva esito</Button>
        <Button size="sm" variant="quiet" onClick={onCancel}>Annulla</Button>
      </div>
    </div>
  );
}
