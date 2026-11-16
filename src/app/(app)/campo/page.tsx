"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useStore } from "@/lib/store";
import { PageTitle, Plate } from "@/components/ui";

export default function Campo() {
  const { vehicles, parts, activeVehicleId } = useStore();
  const list = vehicles.filter((v) => v.work !== "smontato").sort((a, b) => (a.id === activeVehicleId ? -1 : b.id === activeVehicleId ? 1 : 0));
  return (
    <div className="mx-auto max-w-xl">
      <PageTitle title="Su quale veicolo lavori?" sub="Scegli il veicolo: ogni pezzo che catalogherai erediterà targa, telaio e pratica." />
      <ul className="space-y-3">
        {list.map((v) => {
          const n = parts.filter((p) => p.vehicleId === v.id).length;
          const active = v.id === activeVehicleId;
          return (
            <li key={v.id}>
              <Link
                href={`/campo/${v.id}`}
                className={`label-sheet flex items-center gap-4 p-4 transition-colors ${active ? "border-band ring-2 ring-band" : "hover:border-ink-3"}`}
              >
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="code text-[40px] font-bold leading-none">{v.id}</span>
                    {active && <span className="code inline-flex h-7 items-center rounded bg-band px-2.5 text-[13px] font-semibold uppercase tracking-wide text-white">in lavorazione</span>}
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <Plate plate={v.plate} size="sm" />
                    <span className="font-semibold">{v.make} {v.model}</span>
                  </div>
                  <div className="mt-1 text-sm text-ink-2">{v.work} · {n} pezzi catalogati</div>
                </div>
                <ArrowRight className="size-6 text-band" aria-hidden />
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
