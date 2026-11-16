"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useStore } from "@/lib/store";
import { PageTitle, Panel, Empty } from "@/components/ui";
import { PartRow } from "@/components/PartRow";
import { PART_TYPES } from "@/lib/catalog";
import { WAREHOUSES } from "@/lib/warehouse";
import type { PartStatus } from "@/lib/types";

const STATUSES: (PartStatus | "tutti")[] = ["tutti", "disponibile", "bozza", "riservato", "venduto", "invendibile", "scartato"];

export default function Page() {
  return (
    <Suspense>
      <Magazzino />
    </Suspense>
  );
}

function Magazzino() {
  const sp = useSearchParams();
  const { parts, vehicles } = useStore();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<PartStatus | "tutti">("tutti");
  const [type, setType] = useState("");
  const [area, setArea] = useState("");
  const [noLoc, setNoLoc] = useState(sp.get("filtro") === "senza-posizione");

  const query = q.trim().toUpperCase();
  const vById = new Map(vehicles.map((v) => [v.id, v]));
  const list = parts.filter((p) => {
    if (status !== "tutti" && p.status !== status) return false;
    if (type && p.typeId !== type) return false;
    if (area && p.location?.mag !== area) return false;
    if (noLoc && p.location) return false;
    if (!query) return true;
    const v = vById.get(p.vehicleId);
    return [p.id, p.description, p.oem ?? "", p.legacyCode ?? "", p.manufacturer ?? "", p.vehicleId, v?.plate ?? "", v?.make ?? "", v?.model ?? ""].some((x) => x.toUpperCase().includes(query));
  });

  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle title="Magazzino ricambi" sub={`${parts.length} pezzi, ognuno con il proprio ID e la provenienza dal veicolo.`} />
      <div className="mb-4 grid gap-3 md:grid-cols-[1.5fr_1fr_1fr_1fr]">
        <input className="field" placeholder="Cerca ID, vecchio codice K000…, OE, costruttore, targa…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Cerca ricambi" />
        <select className="field" value={status} onChange={(e) => setStatus(e.target.value as PartStatus | "tutti")} aria-label="Stato">
          {STATUSES.map((s) => <option key={s} value={s}>{s === "tutti" ? "Tutti gli stati" : s}</option>)}
        </select>
        <select className="field" value={type} onChange={(e) => setType(e.target.value)} aria-label="Tipologia">
          <option value="">Tutte le tipologie</option>
          {PART_TYPES.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        <select className="field" value={area} onChange={(e) => setArea(e.target.value)} aria-label="Magazzino">
          <option value="">Tutti i magazzini</option>
          {WAREHOUSES.map((w) => <option key={w.id} value={w.id}>{w.name} · {w.desc}</option>)}
        </select>
      </div>
      <label className="mb-4 inline-flex min-h-11 items-center gap-2 font-medium text-ink-2">
        <input type="checkbox" checked={noLoc} onChange={(e) => setNoLoc(e.target.checked)} className="size-5 accent-[var(--band)]" />
        Solo pezzi senza posizione
      </label>
      <Panel title={`${list.length} risultati`}>
        {list.length === 0 ? (
          <Empty title="Nessun ricambio con questi filtri">Prova a togliere un filtro o a cercare per targa.</Empty>
        ) : (
          <ul className="divide-y divide-hair-soft">
            {list.slice(0, 200).map((p) => (
              <li key={p.id}>
                <PartRow part={p} />
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
