"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, Check } from "lucide-react";
import { useStore } from "@/lib/store";
import { corsiaId, ripianiCount, sameRipiano, scaffaleId } from "@/lib/warehouse";
import { dateIt } from "@/lib/logic";
import { ButtonLink, Empty, Panel } from "@/components/ui";

export default function InventarioMagazzino() {
  const { mag } = useParams<{ mag: string }>();
  const id = decodeURIComponent(mag);
  const { warehouses, inventory, parts } = useStore();
  const w = warehouses.find((x) => x.id === id);
  const [sel, setSel] = useState<{ c: string; s: string } | null>(null);
  if (!w) return <Empty title={`Magazzino ${id} non trovato`} />;

  const lastCount = (c: string, s: string, r: string) => [...inventory].reverse().find((x) => x.mag === w.id && x.corsia === c && x.scaffale === s && x.ripiano === r);
  const here = (c: string, s: string, r: string) => parts.filter((p) => sameRipiano(p.location, w.id, c, s, r) && p.status !== "venduto" && p.status !== "scartato");
  const doneShelf = (c: string, s: string) => [...w.ripiani].filter((r) => lastCount(c, s, r)).length;
  const tot = ripianiCount(w);
  const done = new Set(inventory.filter((x) => x.mag === w.id).map((x) => `${x.corsia}-${x.scaffale}-${x.ripiano}`)).size;

  return (
    <div className="mx-auto max-w-6xl">
      <Link href="/inventario" className="mb-3 inline-flex items-center gap-1.5 text-[15px] font-semibold text-band">
        <ArrowLeft className="size-4" aria-hidden /> Inventario
      </Link>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="code text-[40px] font-bold leading-none">Mag. {w.id}</h1>
          <p className="mt-1 font-semibold">{w.name} <span className="font-normal text-ink-2">· {w.desc}</span></p>
        </div>
        <p className="text-ink-2"><b className="code text-[22px] text-ink">{done}</b> di {tot} ripiani contati</p>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Panel title="Tocca uno scaffale">
          <div className="overflow-x-auto p-3">
            <table className="border-separate border-spacing-1.5">
              <thead>
                <tr>
                  <th className="code px-1 text-left text-[13px] font-semibold text-ink-3">Corsia</th>
                  {Array.from({ length: w.scaffali }, (_, i) => (
                    <th key={i} className="code min-w-12 text-[13px] font-semibold text-ink-3">{scaffaleId(i + 1)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: w.corsie }, (_, ci) => {
                  const c = corsiaId(ci + 1);
                  return (
                    <tr key={c}>
                      <th className="code pr-2 text-left text-[18px] font-bold">{c}</th>
                      {Array.from({ length: w.scaffali }, (_, si) => {
                        const s = scaffaleId(si + 1);
                        const n = doneShelf(c, s);
                        const all = n === w.ripiani.length;
                        const on = sel?.c === c && sel.s === s;
                        return (
                          <td key={s}>
                            <button
                              onClick={() => setSel({ c, s })}
                              aria-pressed={on}
                              aria-label={`Corsia ${c} scaffale ${s}: ${n} ripiani contati su ${w.ripiani.length}`}
                              className={`code grid h-12 w-12 place-items-center rounded text-[15px] font-bold ${
                                on ? "ring-2 ring-ink ring-offset-1" : ""
                              } ${all ? "bg-band text-white" : n ? "bg-band-tint text-band" : "border border-hair bg-carton text-ink-3"}`}
                            >
                              {all ? <Check className="size-5" aria-hidden /> : `${n}/${w.ripiani.length}`}
                            </button>
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title={sel ? `Scaffale ${w.id}/${sel.c}-${sel.s}` : "Ripiani"}>
          {!sel ? (
            <p className="p-4 text-ink-2">Scegli lo scaffale davanti a cui ti trovi: poi conti un ripiano alla volta.</p>
          ) : (
            <ul className="divide-y divide-hair-soft">
              {[...w.ripiani].reverse().map((r) => {
                const last = lastCount(sel.c, sel.s, r);
                const n = here(sel.c, sel.s, r).length;
                return (
                  <li key={r} className="flex items-center gap-3 px-4 py-3">
                    <span className="code grid size-11 shrink-0 place-items-center rounded bg-carton text-[20px] font-bold">{r}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block font-semibold">Ripiano {r} · {n} {n === 1 ? "pezzo registrato" : "pezzi registrati"}</span>
                      <span className={`block text-sm ${last ? "text-ok" : "text-ink-3"}`}>
                        {last ? `Contato ${dateIt(last.at)} · ${last.found.length + last.added.length} presenti${last.missing.length ? ` · ${last.missing.length} mancanti` : ""}` : "Da contare"}
                      </span>
                    </span>
                    <ButtonLink
                      size="sm"
                      variant={last ? "secondary" : "primary"}
                      href={`/inventario/conta?mag=${encodeURIComponent(w.id)}&c=${sel.c}&s=${sel.s}&r=${r}`}
                    >
                      {last ? "Riconta" : "Conta"}
                    </ButtonLink>
                  </li>
                );
              })}
            </ul>
          )}
        </Panel>
      </div>
    </div>
  );
}
