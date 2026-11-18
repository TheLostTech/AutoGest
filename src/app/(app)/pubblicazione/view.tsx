"use client";

import Link from "next/link";
import { useState } from "react";
import { useStore } from "@/lib/store";
import { publishChecks, euro } from "@/lib/logic";
import { listingOf } from "@/lib/annunci";
import { Button, Empty, Notice, PageTitle, Panel, PartImage, StatusChip } from "@/components/ui";

export default function Pubblicazione() {
  const s = useStore();
  const [msg, setMsg] = useState("");
  const vById = new Map(s.vehicles.map((v) => [v.id, v]));
  const queue = s.parts
    .filter((p) => (p.status === "bozza" || p.status === "disponibile") && listingOf(p, s.annunci) !== "pubblicato")
    .map((p) => ({ p, missing: publishChecks(p, vById.get(p.vehicleId)).filter((c) => c.blocking && !c.ok) }))
    .sort((a, b) => a.missing.length - b.missing.length);
  // In blocco si pubblicano solo i pezzi mai ritirati: quelli tolti dal negozio a mano tornano online solo uno per uno
  const ready = queue.filter((x) => x.missing.length === 0 && x.p.status === "disponibile" && listingOf(x.p, s.annunci) === "non pubblicato");

  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle
        title="Approvazione e pubblicazione"
        sub="Un ricambio va online solo con foto, prezzo, dati minimi validati e provenienza certa. Le schede incomplete restano in bozza."
        actions={
          ready.length > 0 && (
            <Button onClick={() => { ready.forEach((x) => s.publish(x.p.id)); setMsg(`${ready.length} ricambi pubblicati sul negozio`); }}>
              Pubblica i {ready.length} pronti
            </Button>
          )
        }
      />
      {msg && <div className="mb-4"><Notice tone="ok">{msg}</Notice></div>}
      <Panel title={`In coda · ${queue.length}`}>
        {queue.length === 0 ? (
          <Empty title="Nessuna scheda in attesa" />
        ) : (
          <ul className="divide-y divide-hair-soft">
            {queue.map(({ p, missing }) => (
              <li key={p.id} className="grid grid-cols-[56px_1fr] gap-3 px-4 py-3 md:grid-cols-[56px_1fr_auto] md:items-center">
                <PartImage src={p.photos[0]} typeId={p.typeId} className="size-14 rounded bg-white [&>span]:hidden" />
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <Link href={`/ricambi/${p.id}`} className="code text-[22px] font-bold leading-none text-ink hover:text-band">{p.id}</Link>
                    <StatusChip status={p.status} />
                    <span className="code font-bold">{euro(p.price)}</span>
                  </div>
                  <div className="truncate font-medium">{p.description}</div>
                  {missing.length > 0 ? (
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {missing.map((m) => (
                        <span key={m.label} className="rounded bg-danger-bg px-2 py-0.5 text-[13px] font-semibold text-danger">{m.label}</span>
                      ))}
                    </div>
                  ) : (
                    <div className="mt-1 text-sm font-semibold text-ok">Pronto per la pubblicazione</div>
                  )}
                </div>
                <div className="col-span-2 flex flex-wrap gap-2 md:col-span-1 md:justify-end">
                  {p.status === "bozza" && <Button size="sm" variant="secondary" onClick={() => s.setPartStatus(p.id, "disponibile", "Scheda approvata dal responsabile")}>Approva scheda</Button>}
                  {missing.length === 0 ? (
                    <Button size="sm" onClick={() => s.publish(p.id)}>Pubblica</Button>
                  ) : (
                    <Link href={`/ricambi/${p.id}`} className="inline-flex min-h-9 items-center rounded-md px-3 text-sm font-semibold text-band hover:bg-band-tint">Completa scheda</Link>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
