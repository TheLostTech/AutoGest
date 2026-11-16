"use client";

import Link from "next/link";
import { useState } from "react";
import { useStore } from "@/lib/store";
import { dateIt, euro } from "@/lib/logic";
import { Button, Empty, Notice, PageTitle } from "@/components/ui";
import type { DocType } from "@/lib/types";
import { DOC_LABEL } from "@/lib/docs";

const FILTERS: { value: "tutti" | DocType; label: string }[] = [
  { value: "tutti", label: "Tutti" },
  { value: "preventivo", label: "Preventivi" },
  { value: "documento commerciale", label: "Scontrini" },
  { value: "fattura", label: "Fatture" },
  { value: "nota di credito", label: "Note di credito" },
];


export default function Documenti() {
  const { docs, convertQuote } = useStore();
  const [f, setF] = useState<(typeof FILTERS)[number]["value"]>("tutti");
  const [msg, setMsg] = useState<{ tone: "ok" | "danger"; text: React.ReactNode } | null>(null);
  const list = docs.filter((d) => f === "tutti" || d.type === f);

  return (
    <div className="mx-auto max-w-5xl">
      <PageTitle title="Documenti" sub="Preventivi, scontrini, fatture e note di credito nascono dalle vendite: niente da ricopiare." />
      {msg && <div className="mb-5"><Notice tone={msg.tone}>{msg.text}</Notice></div>}

      <div className="mb-4 flex gap-1.5 overflow-x-auto pb-1" role="tablist" aria-label="Tipo di documento">
        {FILTERS.map((x) => (
          <button
            key={x.value}
            role="tab"
            aria-selected={f === x.value}
            onClick={() => setF(x.value)}
            className={`h-10 shrink-0 rounded-full px-4 text-[15px] font-semibold ${f === x.value ? "bg-ink text-white" : "border border-hair bg-label text-ink-2"}`}
          >
            {x.label} <span className={f === x.value ? "text-white/70" : "text-ink-3"}>{x.value === "tutti" ? docs.length : docs.filter((d) => d.type === x.value).length}</span>
          </button>
        ))}
      </div>

      {list.length === 0 ? (
        <Empty title="Nessun documento di questo tipo" />
      ) : (
        <ul className="divide-y divide-hair-soft rounded-md border border-hair bg-label">
          {list.map((d) => (
            <li key={d.id} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-2 px-4 py-3 md:grid-cols-[170px_minmax(0,1fr)_110px_auto]">
              <Link href={`/documento/${d.id}`} target="_blank" className="min-w-0">
                <span className="code block text-[20px] font-bold leading-none text-band underline-offset-2 hover:underline">{d.id}</span>
                <span className="text-sm text-ink-3">{DOC_LABEL[d.type]} · {dateIt(d.at)}</span>
              </Link>
              <span className="col-span-2 min-w-0 md:col-span-1 md:row-auto">
                <span className="block truncate font-semibold">{d.customer.name}</span>
                <span className="block truncate text-sm text-ink-2">
                  {d.lines.length} {d.lines.length === 1 ? "riga" : "righe"}
                  {d.customer.taxId && <> · <span className="code">{d.customer.taxId}</span></>}
                  {d.orderId && <> · ordine <span className="code">{d.orderId}</span></>}
                  {d.refDocId && <> · rif. <span className="code">{d.refDocId}</span></>}
                </span>
              </span>
              <span className={`code text-[20px] font-bold md:text-right ${d.total < 0 ? "text-danger" : ""}`}>{euro(d.total)}</span>
              <span className="flex flex-wrap items-center justify-end gap-2">
                {d.type === "preventivo" && d.status === "aperto" ? (
                  <Button
                    size="sm"
                    onClick={() => {
                      const r = convertQuote(d.id, d.customer.taxId ? "fattura" : "documento commerciale");
                      setMsg(
                        r.ok
                          ? { tone: "ok", text: <>Preventivo {d.id} venduto: emesso <Link href={`/documento/${r.value}`} target="_blank" className="code font-semibold underline">{r.value}</Link>.</> }
                          : { tone: "danger", text: `Non convertibile: ${r.conflicts?.join(", ") ?? r.error} non più disponibile.` },
                      );
                    }}
                  >
                    Vendi
                  </Button>
                ) : (
                  <span className="code text-[13px] font-semibold uppercase tracking-wide text-ink-3">{d.status}</span>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-3 text-[13px] text-ink-3">Documenti dimostrativi: numerazione, invio allo SdI, registratore telematico e regime IVA vanno definiti con il commercialista.</p>
    </div>
  );
}
