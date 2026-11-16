"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { FilePlus2 } from "lucide-react";
import { useStore } from "@/lib/store";
import { DESTINATARI, eerByCode, FIR_NEXT, fmtKg, stockByEer, TRASPORTATORI } from "@/lib/ambiente";
import { dateIt } from "@/lib/logic";
import { Button, Field, Notice, PageTitle, Panel } from "@/components/ui";
import type { FirStatus } from "@/lib/types";

const FIR_TONE: Record<FirStatus, string> = {
  "da firmare": "bg-warn-bg text-warn",
  firmato: "bg-band-tint text-band",
  trasmesso: "bg-band text-white",
  accettato: "bg-ok-bg text-ok",
};

export default function Page() {
  return (
    <Suspense>
      <Formulari />
    </Suspense>
  );
}

function Formulari() {
  const sp = useSearchParams();
  const { firs, wasteMoves, createFir, advanceFir } = useStore();
  const stock = stockByEer(wasteMoves).filter((s) => s.kg > 0 && s.code !== "16 01 04*");
  const pre = sp.get("eer");
  const [open, setOpen] = useState(!!pre);
  const [eer, setEer] = useState(pre && stock.some((s) => s.code === pre) ? pre : (stock[0]?.code ?? ""));
  const cur = stock.find((s) => s.code === eer);
  const [kg, setKg] = useState(cur ? String(cur.kg) : "");
  const [dest, setDest] = useState(eerByCode(eer)?.destinatario ?? DESTINATARI[0]);
  const [carrier, setCarrier] = useState(TRASPORTATORI[0]);
  const [msg, setMsg] = useState<string | null>(null);

  const pick = (code: string) => {
    setEer(code);
    const s = stock.find((x) => x.code === code);
    setKg(s ? String(s.kg) : "");
    setDest(eerByCode(code)?.destinatario ?? DESTINATARI[0]);
  };
  const kgNum = Number(kg.replace(",", ".")) || 0;
  // Prima quelli che chiedono un'azione, poi i più recenti
  const ordered = [...firs].sort((a, b) => Number(!FIR_NEXT[a.status]) - Number(!FIR_NEXT[b.status]) || b.at.localeCompare(a.at));
  const tooMuch = cur ? kgNum > cur.kg : false;

  return (
    <div className="mx-auto max-w-5xl">
      <PageTitle
        title="Formulari"
        sub="Ogni uscita di rifiuti ha il suo formulario. Con la firma il rifiuto lascia l'impianto e lo scarico entra da solo nel registro."
        actions={!open && <Button onClick={() => setOpen(true)}><FilePlus2 className="size-5" aria-hidden /> Nuovo formulario</Button>}
      />
      {msg && <div className="mb-5"><Notice tone="ok">{msg}</Notice></div>}

      {open && (
        <Panel title="Nuovo formulario" className="mb-6">
          <div className="grid gap-4 p-4 sm:grid-cols-2">
            <Field label="Rifiuto">
              <select className="field" value={eer} onChange={(e) => pick(e.target.value)}>
                {stock.map((s) => <option key={s.code} value={s.code}>{s.code} · {s.short} · {fmtKg(s.kg)} in giacenza</option>)}
              </select>
            </Field>
            <Field label="Quantità" hint={cur ? `In giacenza ${fmtKg(cur.kg)}` : undefined} error={tooMuch ? "Più della giacenza registrata" : undefined}>
              <span className="flex items-center gap-2">
                <input className="field code text-[18px] font-bold" inputMode="decimal" value={kg} onChange={(e) => setKg(e.target.value.replace(/[^0-9.,]/g, ""))} />
                <span className="text-ink-3">kg</span>
              </span>
            </Field>
            <Field label="Destinatario">
              <select className="field" value={dest} onChange={(e) => setDest(e.target.value)}>
                {DESTINATARI.map((d) => <option key={d}>{d}</option>)}
              </select>
            </Field>
            <Field label="Trasportatore">
              <select className="field" value={carrier} onChange={(e) => setCarrier(e.target.value)}>
                {TRASPORTATORI.map((d) => <option key={d}>{d}</option>)}
              </select>
            </Field>
            <div className="flex flex-wrap gap-2 sm:col-span-2">
              <Button
                disabled={!eer || !kgNum || tooMuch}
                onClick={() => {
                  const id = createFir({ eer, kg: kgNum, destinatario: dest, trasportatore: carrier });
                  setMsg(`Formulario ${id} pronto: firmalo alla partenza del carico.`);
                  setOpen(false);
                }}
              >
                Crea formulario
              </Button>
              <Button variant="quiet" onClick={() => setOpen(false)}>Annulla</Button>
            </div>
          </div>
        </Panel>
      )}

      <ul className="space-y-3">
        {ordered.map((f) => {
          const e = eerByCode(f.eer);
          const next = FIR_NEXT[f.status];
          return (
            <li key={f.id} className="label-sheet p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="code text-[26px] font-bold leading-none">{f.id}</span>
                    <span className={`code inline-flex h-7 items-center rounded px-2.5 text-[13px] font-semibold uppercase tracking-wide ${FIR_TONE[f.status]}`}>{f.status}</span>
                  </div>
                  <p className="mt-2 font-semibold">
                    <span className="code">{f.eer}</span> {e?.short} · <span className="code">{fmtKg(f.kg)}</span>
                  </p>
                  <p className="text-sm text-ink-2">{f.destinatario} · trasporto {f.trasportatore}</p>
                </div>
                {next && (
                  <Button size="sm" variant={f.status === "da firmare" ? "primary" : "secondary"} onClick={() => advanceFir(f.id)}>
                    {next.label}
                  </Button>
                )}
              </div>
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
      <p className="mt-3 text-[13px] text-ink-3">Formulario digitale (xFIR) dimostrativo: firma, trasmissione al RENTRI e accettazione del destinatario sono simulate.</p>
    </div>
  );
}
