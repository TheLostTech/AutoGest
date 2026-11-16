"use client";

import Link from "next/link";
import { Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { useStore } from "@/lib/store";
import { recoveryList, type StockLevel } from "@/lib/logic";
import type { Vehicle } from "@/lib/types";
import { LevelChip } from "./ui";

const FILTERS: { key: "utili" | "tutti"; label: string }[] = [
  { key: "utili", label: "Da recuperare" },
  { key: "tutti", label: "Tutti" },
];

// Confronto con le scorte reali: cosa manca, cosa è sotto soglia, cosa basta già.
export function RecoveryList({ vehicle, addHref }: { vehicle: Vehicle; addHref?: (typeId: string) => string }) {
  const { parts, vehicles, rules } = useStore();
  const rows = useMemo(() => recoveryList(vehicle, parts, vehicles, rules), [vehicle, parts, vehicles, rules]);
  const [filter, setFilter] = useState<"utili" | "tutti">("utili");
  const useful = (l: StockLevel) => l === "manca" || l === "sotto soglia";
  const shown = filter === "utili" ? rows.filter((r) => useful(r.level)) : rows;
  const unknown = vehicle.platform === "sconosciuta" || !vehicle.platform;

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-hair-soft px-4 py-3">
        <div className="flex rounded-md border border-hair p-0.5" role="tablist">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              role="tab"
              aria-selected={filter === f.key}
              onClick={() => setFilter(f.key)}
              className={`min-h-10 rounded px-4 text-[15px] font-semibold ${filter === f.key ? "bg-band text-white" : "text-ink-2"}`}
            >
              {f.label}
              <span className="code ml-1.5 opacity-80">{f.key === "utili" ? rows.filter((r) => useful(r.level)).length : rows.length}</span>
            </button>
          ))}
        </div>
        <p className="text-[13px] text-ink-3">Scorte compatibili (stesso modello o intercambiabili verificati)</p>
      </div>
      {unknown && <p className="bg-warn-bg px-4 py-2 text-sm font-semibold text-warn">Piattaforma non determinata: il confronto scorte non è affidabile finché il veicolo non è verificato.</p>}
      <ul className="divide-y divide-hair-soft">
        {shown.map((r) => (
          <li key={r.typeId} className="grid grid-cols-[1fr_auto] items-center gap-3 px-4 py-3">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[17px] font-semibold text-ink">{r.name}</span>
                <LevelChip level={r.level} />
              </div>
              <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-[14px] text-ink-2">
                <span>
                  In scorta <b className="code text-[17px] text-ink">{r.disponibili + r.bozze}</b>
                  <span className="text-ink-3"> / soglia {r.min}–{r.max}</span>
                </span>
                {r.riservati > 0 && <span>{r.riservati} riservati</span>}
                {r.invendibili > 0 && <span className="basis-full">{r.invendibili} {r.invendibili === 1 ? "invendibile" : "invendibili"} (non contati)</span>}
                {r.daAltriModelli > 0 && <span>{r.daAltriModelli} da modelli compatibili</span>}
                {r.daQuestoVeicolo > 0 && <span className="font-semibold text-band">{r.daQuestoVeicolo} già da questo veicolo</span>}
              </div>
            </div>
            {addHref && (
              <Link href={addHref(r.typeId)} className="grid size-12 place-items-center rounded-md border border-hair bg-label text-band hover:border-band" aria-label={`Cataloga ${r.name}`}>
                <Plus className="size-6" strokeWidth={2.4} />
              </Link>
            )}
          </li>
        ))}
        {shown.length === 0 && <li className="px-4 py-8 text-center text-ink-2">Le scorte coprono già tutte le tipologie per questa piattaforma.</li>}
      </ul>
      <p className="border-t border-hair-soft px-4 py-3 text-[13px] text-ink-3">
        Il suggerimento non sostituisce il giudizio dello smontatore su stato fisico e convenienza del recupero.
      </p>
    </div>
  );
}

export function useVehicle(id: string) {
  return useStore((s) => s.vehicles.find((v) => v.id === id));
}
