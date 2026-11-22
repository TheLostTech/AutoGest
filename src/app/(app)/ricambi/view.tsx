"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useStore } from "@/lib/store";
import { PageTitle, Panel, Empty } from "@/components/ui";
import { PartRow } from "@/components/PartRow";
import type { PartStatus } from "@/lib/types";
import { TypeOptions } from "@/components/TypeOptions";

const STATUSES: (PartStatus | "tutti")[] = ["tutti", "disponibile", "bozza", "riservato", "venduto", "invendibile", "scartato"];

export default function Page() {
  return (
    <Suspense>
      <Keyed />
    </Suspense>
  );
}

// Un link con un filtro diverso (es. dalla coda "Da fare") riparte con quel filtro
function Keyed() {
  const sp = useSearchParams();
  return <Magazzino key={sp.get("filtro") ?? ""} />;
}

function Magazzino() {
  const sp = useSearchParams();
  const { parts, vehicles, warehouses } = useStore();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<PartStatus | "tutti">("tutti");
  const [type, setType] = useState("");
  const [area, setArea] = useState("");
  // Filtri rapidi, anche dai link della coda "Da fare"
  const [quick, setQuick] = useState<"" | "senza-posizione" | "senza-etichetta" | "mancanti">(() => {
    const f = sp.get("filtro");
    return f === "senza-posizione" || f === "senza-etichetta" || f === "mancanti" ? f : "";
  });
  const active = (p: { status: PartStatus }) => p.status !== "venduto" && p.status !== "scartato";

  const query = q.trim().toUpperCase();
  const vById = new Map(vehicles.map((v) => [v.id, v]));
  const list = parts.filter((p) => {
    if (status !== "tutti" && p.status !== status) return false;
    if (type && p.typeId !== type) return false;
    if (area && p.location?.mag !== area) return false;
    if (quick === "senza-posizione" && (p.location || !(p.status === "disponibile" || p.status === "bozza"))) return false;
    if (quick === "senza-etichetta" && (p.labelPrints > 0 || !active(p))) return false;
    if (quick === "mancanti" && (!p.missingSince || !active(p))) return false;
    if (!query) return true;
    const v = vById.get(p.vehicleId);
    return [p.id, p.description, p.oem ?? "", p.legacyCode ?? "", p.manufacturer ?? "", p.vehicleId, v?.plate ?? "", v?.make ?? "", v?.model ?? "", p.pastDossier?.number ?? "", p.pastDossier?.plate ?? ""].some((x) => x.toUpperCase().includes(query));
  });

  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle title="Magazzino ricambi" sub={`${parts.length} pezzi, ognuno con il proprio ID e la sua provenienza.`} />
      <div className="mb-4 grid gap-3 md:grid-cols-[1.5fr_1fr_1fr_1fr]">
        <input className="field" placeholder="Cerca ID, vecchio codice K000…, OE, costruttore, targa…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Cerca ricambi" />
        <select className="field" value={status} onChange={(e) => setStatus(e.target.value as PartStatus | "tutti")} aria-label="Stato">
          {STATUSES.map((s) => <option key={s} value={s}>{s === "tutti" ? "Tutti gli stati" : s}</option>)}
        </select>
        <select className="field" value={type} onChange={(e) => setType(e.target.value)} aria-label="Tipologia">
          <option value="">Tutte le tipologie</option>
          <TypeOptions />
        </select>
        <select className="field" value={area} onChange={(e) => setArea(e.target.value)} aria-label="Magazzino">
          <option value="">Tutti i magazzini</option>
          {warehouses.map((w) => <option key={w.id} value={w.id}>{w.name} · {w.desc}</option>)}
        </select>
      </div>
      <div className="mb-4 flex flex-wrap gap-1.5" role="group" aria-label="Filtri rapidi">
        {(
          [
            ["senza-posizione", "Senza posizione"],
            ["senza-etichetta", "Senza etichetta"],
            ["mancanti", "Non trovati all'inventario"],
          ] as const
        ).map(([k, label]) => (
          <button
            key={k}
            aria-pressed={quick === k}
            onClick={() => setQuick(quick === k ? "" : k)}
            className={`h-10 rounded-full border px-4 text-[15px] font-semibold ${quick === k ? "border-ink bg-ink text-white" : "border-hair bg-label text-ink-2"}`}
          >
            {label}
          </button>
        ))}
      </div>
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
