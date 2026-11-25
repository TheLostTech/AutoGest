"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useStore } from "@/lib/store";
import { PageTitle, Panel, Empty } from "@/components/ui";
import { PartRow } from "@/components/PartRow";
import type { PartStatus } from "@/lib/types";
import { TypePicker } from "@/components/TypePicker";
import { PART_TYPES, typeById } from "@/lib/catalog";
import { cercaTipologie, corrisponde } from "@/lib/cerca";

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
  return <Magazzino key={`${sp.get("filtro") ?? ""}|${sp.get("tipo") ?? ""}`} />;
}

function Magazzino() {
  const sp = useSearchParams();
  const { parts, vehicles, warehouses } = useStore();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<PartStatus | "tutti">("tutti");
  // "" tutte, l'id di una tipologia o "cat:<Categoria>"; dalla ricerca generale arriva con ?tipo=
  const [type, setType] = useState(() => sp.get("tipo") ?? "");
  const [area, setArea] = useState("");
  // Filtri rapidi, anche dai link della coda "Da fare"
  const [quick, setQuick] = useState<"" | "senza-posizione" | "senza-etichetta" | "mancanti">(() => {
    const f = sp.get("filtro");
    return f === "senza-posizione" || f === "senza-etichetta" || f === "mancanti" ? f : "";
  });
  const active = (p: { status: PartStatus }) => p.status !== "venduto" && p.status !== "scartato";

  const vById = new Map(vehicles.map((v) => [v.id, v]));
  // Pezzi in magazzino (non venduti né scartati) per tipologia e per categoria, accanto alle voci del selettore
  const conteggi = new Map<string, number>();
  for (const p of parts) {
    if (!active(p)) continue;
    const t = typeById(p.typeId);
    conteggi.set(t.id, (conteggi.get(t.id) ?? 0) + 1);
    conteggi.set(`cat:${t.category}`, (conteggi.get(`cat:${t.category}`) ?? 0) + 1);
  }
  const list = parts.filter((p) => {
    if (status !== "tutti" && p.status !== status) return false;
    if (type.startsWith("cat:") ? typeById(p.typeId).category !== type.slice(4) : type && p.typeId !== type) return false;
    if (area && p.location?.mag !== area) return false;
    if (quick === "senza-posizione" && (p.location || !(p.status === "disponibile" || p.status === "bozza"))) return false;
    if (quick === "senza-etichetta" && (p.labelPrints > 0 || !active(p))) return false;
    if (quick === "mancanti" && (!p.missingSince || !active(p))) return false;
    const v = vById.get(p.vehicleId);
    const t = typeById(p.typeId);
    return corrisponde(q, [p.id, p.description, t.name, t.category, p.misura, p.oem, p.legacyCode, p.manufacturer, p.vehicleId, v?.plate, v?.make, v?.model, p.pastDossier?.number, p.pastDossier?.plate]);
  });
  // Tipologie che corrispondono a quello che si scrive: un tocco e diventano il filtro
  const tipiTrovati = q.trim() && !type ? cercaTipologie(q, PART_TYPES).slice(0, 8) : [];

  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle title="Magazzino ricambi" sub={`${parts.length} pezzi, ognuno con il proprio ID e la sua provenienza.`} />
      <div className="mb-4 grid gap-3 md:grid-cols-[1.5fr_1fr_1fr_1fr]">
        <input className="field" placeholder="Cerca pezzo, codice o targa…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Cerca ricambi" />
        <select className="field" value={status} onChange={(e) => setStatus(e.target.value as PartStatus | "tutti")} aria-label="Stato">
          {STATUSES.map((s) => <option key={s} value={s}>{s === "tutti" ? "Tutti gli stati" : s}</option>)}
        </select>
        <TypePicker value={type} onChange={setType} vuoto="Tutte le tipologie" categorie conteggi={conteggi} />
        <select className="field" value={area} onChange={(e) => setArea(e.target.value)} aria-label="Magazzino">
          <option value="">Tutti i magazzini</option>
          {warehouses.map((w) => <option key={w.id} value={w.id}>{w.name} · {w.desc}</option>)}
        </select>
      </div>
      {tipiTrovati.length > 0 && (
        <div className="mb-3 flex flex-wrap items-center gap-1.5" role="group" aria-label="Tipologie trovate">
          <span className="mr-1 text-[15px] font-semibold text-ink-2">Tipologie:</span>
          {tipiTrovati.map((t) => (
            <button
              key={t.id}
              onClick={() => {
                setType(t.id);
                setQ("");
              }}
              className="h-10 rounded-full border border-band bg-band-tint px-4 text-[15px] font-semibold text-band"
            >
              {t.name} <span className="font-normal text-ink-2">· {conteggi.get(t.id) ?? 0}</span>
            </button>
          ))}
        </div>
      )}
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
          type && !type.startsWith("cat:") && !q.trim() && status === "tutti" && !area && !quick ? (
            <Empty title={`Nessun pezzo «${typeById(type).name}» in magazzino`}>Quando ne catalogherai uno, comparirà qui.</Empty>
          ) : (
            <Empty title="Nessun ricambio con questi filtri">Prova a togliere un filtro o a cercare per targa.</Empty>
          )
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
