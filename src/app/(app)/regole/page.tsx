"use client";

import { useStore } from "@/lib/store";
import { PART_TYPES } from "@/lib/catalog";
import { PageTitle, Panel } from "@/components/ui";

export default function Regole() {
  const { rules, setRule, parts } = useStore();
  return (
    <div className="mx-auto max-w-4xl">
      <PageTitle
        title="Regole scorte"
        sub="Prima versione: soglia minima e massima per tipologia, per piattaforma di veicolo. Sotto il minimo il pezzo viene suggerito allo smontatore; dal massimo in su non conviene recuperarlo."
      />
      <Panel>
        <div className="grid grid-cols-[1fr_90px_90px_90px] gap-3 border-b border-hair-soft px-4 py-2.5 text-[13px] font-semibold uppercase tracking-wide text-ink-3 code">
          <span>Tipologia</span>
          <span className="text-center">Minimo</span>
          <span className="text-center">Massimo</span>
          <span className="text-right">In scorta</span>
        </div>
        <ul className="divide-y divide-hair-soft">
          {PART_TYPES.map((t) => {
            const r = rules.find((x) => x.typeId === t.id)!;
            const stock = parts.filter((p) => p.typeId === t.id && (p.status === "disponibile" || p.status === "bozza")).length;
            return (
              <li key={t.id} className="grid grid-cols-[1fr_90px_90px_90px] items-center gap-3 px-4 py-2.5">
                <span>
                  <span className="font-semibold">{t.name}</span>
                  <span className="block text-sm text-ink-3">{t.category}</span>
                </span>
                <input
                  type="number"
                  min={0}
                  className="field code h-11 min-h-0 text-center text-[18px] font-bold"
                  key={`min-${r.min}`}
                  defaultValue={r.min}
                  onBlur={(e) => { const v = Math.max(0, Number(e.target.value)); if (v !== r.min) setRule(t.id, v, Math.max(r.max, v)); }}
                  aria-label={`Minimo ${t.name}`}
                />
                <input
                  type="number"
                  min={0}
                  className="field code h-11 min-h-0 text-center text-[18px] font-bold"
                  key={`max-${r.max}`}
                  defaultValue={r.max}
                  onBlur={(e) => { const v = Math.max(0, Number(e.target.value)); if (v !== r.max) setRule(t.id, Math.min(r.min, v), v); }}
                  aria-label={`Massimo ${t.name}`}
                />
                <span className="code text-right text-[20px] font-bold">{stock}</span>
              </li>
            );
          })}
        </ul>
      </Panel>
      <p className="mt-4 max-w-[70ch] text-sm text-ink-3">
        Versione evoluta prevista: vendite storiche, giorni di giacenza, domanda, margine e rotazione. Le equivalenze tra veicoli andranno basate su codici OEM o cataloghi licenziati, non sulla sola marca e modello.
      </p>
    </div>
  );
}
