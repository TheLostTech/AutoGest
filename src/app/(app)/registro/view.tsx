"use client";

import Link from "next/link";
import { useState } from "react";
import { useStore } from "@/lib/store";
import { dateIt } from "@/lib/logic";
import { PageTitle, Panel } from "@/components/ui";
import type { AuditEvent } from "@/lib/types";

const ENT: (AuditEvent["entity"] | "tutti")[] = ["tutti", "veicolo", "ricambio", "ordine", "regola", "sistema"];

export default function Registro() {
  const audit = useStore((s) => s.audit);
  const [ent, setEnt] = useState<(typeof ENT)[number]>("tutti");
  const [q, setQ] = useState("");
  const query = q.trim().toLowerCase();
  const list = [...audit]
    .reverse()
    .filter((e) => (ent === "tutti" || e.entity === ent) && (!query || `${e.entityId} ${e.action} ${e.detail ?? ""} ${e.user}`.toLowerCase().includes(query)));

  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle title="Registro operazioni" sub="Ogni azione con utente, dispositivo, data e ora. Nessuna cancellazione: le correzioni sono nuove righe." />
      <div className="mb-4 flex flex-wrap gap-3">
        <input className="field max-w-sm" placeholder="Cerca ID, azione, utente…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Cerca nel registro" />
        <select className="field max-w-[200px]" value={ent} onChange={(e) => setEnt(e.target.value as typeof ent)} aria-label="Tipo">
          {ENT.map((x) => <option key={x} value={x}>{x === "tutti" ? "Tutto" : x}</option>)}
        </select>
      </div>
      <Panel title={`${list.length} eventi`}>
        <ul className="divide-y divide-hair-soft">
          {list.slice(0, 300).map((e) => (
            <li key={e.id} className="grid gap-x-4 gap-y-0.5 px-4 py-2.5 text-[15px] md:grid-cols-[140px_120px_1fr_220px]">
              <span className="text-ink-3">{dateIt(e.at, true)}</span>
              <Link
                href={e.entity === "ricambio" ? `/ricambi/${e.entityId}` : e.entity === "veicolo" ? `/veicoli/${e.entityId}` : e.entity === "ordine" ? "/vendite" : "/registro"}
                className="code font-semibold text-band"
              >
                {e.entityId}
              </Link>
              <span className="min-w-0">
                <b>{e.action}</b>
                {e.detail && <span className="text-ink-2"> · {e.detail}</span>}
              </span>
              <span className="text-sm text-ink-3 md:text-right">{e.user} · {e.device}</span>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
