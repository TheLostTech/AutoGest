"use client";

import Link from "next/link";
import { useState } from "react";
import { useStore } from "@/lib/store";
import { ButtonLink, PageTitle, Plate, Panel } from "@/components/ui";
import { dateIt } from "@/lib/logic";

export default function Veicoli() {
  const { vehicles, parts } = useStore();
  const [q, setQ] = useState("");
  const query = q.trim().toUpperCase();
  const list = vehicles.filter((v) => !query || [v.id, v.plate, v.vin, v.make, v.model, v.dossier.number].some((x) => x.toUpperCase().includes(query)));

  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle title="Veicoli" sub="Ogni veicolo è la scheda madre dei suoi ricambi." actions={<ButtonLink href="/veicoli/nuovo">Nuovo ingresso</ButtonLink>} />
      <input className="field mb-4 max-w-md" placeholder="Cerca per targa, telaio, ID, pratica, modello…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Cerca veicoli" />
      <Panel>
        <div className="hidden grid-cols-[130px_120px_1fr_150px_120px_90px] gap-4 border-b border-hair-soft px-4 py-2.5 text-[13px] font-semibold uppercase tracking-wide text-ink-3 code lg:grid">
          <span>ID interno</span>
          <span>Targa</span>
          <span>Veicolo</span>
          <span>Pratica</span>
          <span>Lavorazione</span>
          <span className="text-right">Ricambi</span>
        </div>
        <ul className="divide-y divide-hair-soft">
          {list.map((v) => (
            <li key={v.id}>
              <Link href={`/veicoli/${v.id}`} className="grid grid-cols-[auto_1fr] items-center gap-x-4 gap-y-1 px-4 py-3 hover:bg-carton lg:grid-cols-[130px_120px_1fr_150px_120px_90px]">
                <span className="code text-[24px] font-bold leading-none">{v.id}</span>
                <span><Plate plate={v.plate} size="sm" /></span>
                <span className="col-span-2 min-w-0 lg:col-span-1">
                  <span className="block truncate font-semibold">{v.make} {v.model} <span className="font-normal text-ink-2">{v.version}</span></span>
                  <span className="block text-sm text-ink-3">ingresso {dateIt(v.intakeAt)}{v.verification === "da verificare" && <b className="text-warn"> · da verificare</b>}</span>
                </span>
                <span className="code text-[15px] text-ink-2">{v.dossier.number || <span className="text-warn">da registrare</span>}</span>
                <span className="text-[15px] font-medium">{v.work}</span>
                <span className="code text-right text-[22px] font-bold">{parts.filter((p) => p.vehicleId === v.id).length}</span>
              </Link>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
