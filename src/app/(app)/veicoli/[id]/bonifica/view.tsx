"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, CircleCheck, Wrench } from "lucide-react";
import { useStore } from "@/lib/store";
import { BONIFICA, fmtKg, itemKg, typicalBonifica } from "@/lib/ambiente";
import { dateIt } from "@/lib/logic";
import { ButtonLink, Button, Empty, Notice, Plate } from "@/components/ui";
import type { BonificaItem } from "@/lib/types";

export default function BonificaVeicolo() {
  const { id } = useParams<{ id: string }>();
  const v = useStore((s) => s.vehicles.find((x) => x.id === id));
  const saveBonifica = useStore((s) => s.saveBonifica);
  const [items, setItems] = useState<BonificaItem[]>(() => (v ? (v.bonifica?.items ?? typicalBonifica(v)) : []));
  const [weight, setWeight] = useState(v?.weightKg ? String(v.weightKg) : "");
  const [saved, setSaved] = useState<number | null>(null);

  if (!v) return <Empty title={`Veicolo ${id} non trovato`} />;
  const done = !!v.bonifica;
  const removedKg = items.reduce((a, i) => a + itemKg(i), 0);
  const w = Number(weight) || 0;
  const residual = Math.max(0, Math.round(w - removedKg));
  const set = (key: string, patch: Partial<BonificaItem>) => setItems((xs) => xs.map((x) => (x.key === key ? { ...x, ...patch } : x)));

  return (
    <div className="mx-auto max-w-2xl">
      <Link href={`/veicoli/${v.id}`} className="mb-3 inline-flex items-center gap-1.5 text-[15px] font-semibold text-band">
        <ArrowLeft className="size-4" aria-hidden /> {v.id}
      </Link>
      <h1 className="text-[28px] font-bold leading-tight md:text-[34px]">Bonifica</h1>
      <div className="mt-2 mb-5 flex flex-wrap items-center gap-2 text-ink-2">
        <Plate plate={v.plate} size="sm" />
        <span className="font-semibold text-ink">{v.make} {v.model}</span>
        <span>{v.fuel} · {v.year}</span>
      </div>

      {saved !== null && (
        <div className="mb-5 space-y-3">
          <Notice tone="ok">
            Bonifica registrata. Il registro rifiuti si è aggiornato da solo: <b>{saved} movimenti</b> scritti, da trasmettere al RENTRI.
          </Notice>
          <div className="flex flex-wrap gap-2">
            <ButtonLink href={`/campo/${v.id}`}><Wrench className="size-5" aria-hidden /> Avvia lo smontaggio</ButtonLink>
            <ButtonLink href="/ambiente" variant="secondary">Vedi il registro</ButtonLink>
          </div>
        </div>
      )}

      {done && saved === null && (
        <div className="mb-5">
          <Notice tone="ok">
            Registrata il {dateIt(v.bonifica!.at, true)} da {v.bonifica!.by} · carcassa bonificata {fmtKg(v.bonifica!.residualKg)}
          </Notice>
        </div>
      )}

      <label className="label-sheet mb-4 flex items-center justify-between gap-4 p-4">
        <span>
          <span className="block font-semibold">Peso in ingresso</span>
          <span className="block text-sm text-ink-3">{v.weightKg ? "dalla pesata all'ingresso" : "nessuna pesata: inserisci il peso"}</span>
        </span>
        <span className="flex items-center gap-2">
          <input
            className="field code h-12 w-28 text-right text-[22px] font-bold"
            inputMode="numeric"
            value={weight}
            disabled={done}
            onChange={(e) => setWeight(e.target.value.replace(/[^0-9]/g, ""))}
            aria-label="Peso in chilogrammi"
          />
          <span className="text-ink-3">kg</span>
        </span>
      </label>

      <ul className="divide-y divide-hair-soft rounded-md border border-hair bg-label">
        {BONIFICA.map((b) => {
          const it = items.find((x) => x.key === b.key)!;
          return (
            <li key={b.key} className={`flex items-center gap-3 px-3 py-3 sm:px-4 ${it.done ? "" : "opacity-60"}`}>
              <input
                type="checkbox"
                className="size-6 shrink-0 accent-band"
                checked={it.done}
                disabled={done}
                onChange={(e) => set(b.key, { done: e.target.checked })}
                aria-label={`${b.label} rimosso`}
              />
              <span className="min-w-0 flex-1">
                <span className="block font-semibold leading-snug">{b.label}</span>
                <span className="code block text-[13px] text-ink-3">EER {b.eer(v)} · {fmtKg(itemKg(it))}</span>
              </span>
              <span className="flex shrink-0 items-center gap-1.5">
                <input
                  className="field code h-11 w-20 text-right text-[18px] font-semibold"
                  inputMode="decimal"
                  value={String(it.qty).replace(".", ",")}
                  disabled={done || !it.done}
                  onChange={(e) => set(b.key, { qty: Number(e.target.value.replace(",", ".").replace(/[^0-9.]/g, "")) || 0 })}
                  aria-label={`${b.label}, quantità in ${b.unit}`}
                />
                <span className="w-6 text-sm text-ink-3">{b.unit}</span>
              </span>
            </li>
          );
        })}
      </ul>

      {/* Riepilogo e conferma, sempre a portata di pollice */}
      <div className="sticky bottom-[calc(72px+env(safe-area-inset-bottom))] z-20 mt-5 flex items-center justify-between gap-3 rounded-md border border-hair bg-label p-3 shadow-[0_8px_24px_-12px_rgb(17_20_24/0.35)] md:bottom-4">
        <dl className="flex gap-5">
          <div>
            <dt className="text-[13px] text-ink-3">Rimossi</dt>
            <dd className="code text-[20px] font-bold leading-none">{fmtKg(removedKg)}</dd>
          </div>
          <div>
            <dt className="text-[13px] text-ink-3">Carcassa</dt>
            <dd className="code text-[20px] font-bold leading-none">{fmtKg(residual)}</dd>
          </div>
        </dl>
        {done ? (
          <span className="flex items-center gap-1.5 font-semibold text-ok"><CircleCheck className="size-5" aria-hidden /> Registrata</span>
        ) : (
          <Button disabled={!w} onClick={() => {
              setSaved(saveBonifica(v.id, items, w));
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}>Registra bonifica</Button>
        )}
      </div>
      <p className="mt-3 text-[13px] text-ink-3">
        Quantità tipiche precompilate: correggi solo ciò che è diverso. Codici rifiuto e conversioni in kg sono dimostrativi, da validare con il consulente ambientale.
      </p>
    </div>
  );
}
