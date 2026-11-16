"use client";

import Link from "next/link";
import { Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Search } from "lucide-react";
import { useStore } from "@/lib/store";
import { corsiaId, locLong, sameShelf, scaffaleId, slotCapacity, WAREHOUSES } from "@/lib/warehouse";
import { PageTitle, Panel, PartImage, StatusChip } from "@/components/ui";
import type { Part } from "@/lib/types";

export default function Page() {
  return (
    <Suspense>
      <Mappa />
    </Suspense>
  );
}

const present = (p: Part) => !!p.location && p.status !== "venduto" && p.status !== "scartato";

function Mappa() {
  const sp = useSearchParams();
  const parts = useStore((s) => s.parts);
  const stocked = useMemo(() => parts.filter(present), [parts]);
  const [mag, setMag] = useState(sp.get("mag") ?? "1");
  const [sel, setSel] = useState<{ corsia: string; scaffale: string } | null>(null);
  const [find, setFind] = useState("");
  const [found, setFound] = useState<Part | null>(null);
  const [miss, setMiss] = useState(false);

  const w = WAREHOUSES.find((x) => x.id === mag)!;
  const cap = slotCapacity(w);
  const inMag = stocked.filter((p) => p.location!.mag === mag);
  const count = (c: string, s: string) => inMag.filter((p) => sameShelf(p.location, mag, c, s)).length;
  const shelfParts = sel ? inMag.filter((p) => sameShelf(p.location, mag, sel.corsia, sel.scaffale)) : [];

  function locate(e: React.FormEvent) {
    e.preventDefault();
    const q = find.trim().toUpperCase();
    const p = stocked.find((x) => x.id === q || x.legacyCode === q || x.oem?.replace(/\s/g, "") === q.replace(/\s/g, ""));
    setMiss(!p);
    setFound(p ?? null);
    if (p?.location) {
      setMag(p.location.mag);
      setSel({ corsia: p.location.corsia, scaffale: p.location.scaffale });
    }
  }

  return (
    <div className="mx-auto max-w-7xl">
      <PageTitle title="Mappa del magazzino" sub="Magazzino → corsia → scaffale → ripiano → contenitore. Ogni scaffale mostra quanti pezzi contiene; tocca uno scaffale per vedere ripiani e contenitori." />

      <form onSubmit={locate} className="mb-5 flex max-w-xl gap-2">
        <label className="relative flex-1">
          <Search className="absolute left-3 top-1/2 size-5 -translate-y-1/2 text-ink-3" aria-hidden />
          <input className="field pl-10 code text-[18px] font-semibold uppercase" placeholder="Trova: R-002341, K000…, codice OE" value={find} onChange={(e) => setFind(e.target.value)} aria-label="Trova un pezzo" />
        </label>
        <button className="min-h-12 rounded-md bg-band px-5 font-semibold text-white hover:bg-band-deep">Trova</button>
      </form>
      {found && (
        <p className="-mt-2 mb-5 text-[15px]">
          <Link href={`/ricambi/${found.id}`} className="code font-bold text-band underline">{found.id}</Link> {found.description} → <b>{locLong(found.location)}</b>
        </p>
      )}
      {miss && <p className="-mt-2 mb-5 font-semibold text-danger">Nessun pezzo a magazzino con questo codice.</p>}

      <div className="mb-5 flex gap-2 overflow-x-auto pb-1" role="tablist">
        {WAREHOUSES.map((x) => {
          const n = stocked.filter((p) => p.location!.mag === x.id).length;
          return (
            <button
              key={x.id}
              role="tab"
              aria-selected={mag === x.id}
              onClick={() => { setMag(x.id); setSel(null); }}
              className={`min-w-[170px] shrink-0 rounded-md border px-4 py-2.5 text-left ${mag === x.id ? "border-band bg-band text-white" : "border-hair bg-label hover:border-ink-3"}`}
            >
              <span className="code block text-[22px] font-bold leading-none">{x.id === "P" ? "Piazzale" : `Mag. ${x.id}`}</span>
              <span className={`mt-1 block text-[13px] ${mag === x.id ? "text-white/80" : "text-ink-3"}`}>{x.desc}</span>
              <span className="code mt-1 block text-[15px] font-semibold">{n} pezzi</span>
            </button>
          );
        })}
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Panel className="min-w-0" title={`${w.name} · ${w.corsie} corsie × ${w.scaffali} scaffali · ${w.ripiani.length} ripiani${w.contenitori ? ` × ${w.contenitori} contenitori` : ""}`}>
          <div className="overflow-x-auto p-4">
            <table className="w-full min-w-[640px] table-fixed border-separate border-spacing-1.5 xl:min-w-0">
              <thead>
                <tr>
                  <th className="code w-12 text-left text-[13px] font-semibold uppercase tracking-wide text-ink-3">Corsia</th>
                  {Array.from({ length: w.scaffali }, (_, i) => (
                    <th key={i} className="code text-[13px] font-semibold text-ink-3">{scaffaleId(i + 1)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: w.corsie }, (_, ci) => {
                  const c = corsiaId(ci + 1);
                  return (
                    <tr key={c}>
                      <th className="code text-left text-[18px] font-bold">{c}</th>
                      {Array.from({ length: w.scaffali }, (_, si) => {
                        const s = scaffaleId(si + 1);
                        const n = count(c, s);
                        const fill = Math.min(1, n / cap);
                        const active = sel?.corsia === c && sel?.scaffale === s;
                        const hit = found?.location && sameShelf(found.location, mag, c, s);
                        return (
                          <td key={s}>
                            <button
                              onClick={() => setSel({ corsia: c, scaffale: s })}
                              className={`relative grid h-14 w-full min-w-11 place-items-center overflow-hidden rounded border text-center ${active ? "border-band ring-2 ring-band" : "border-hair"} ${hit ? "ring-4 ring-warn" : ""}`}
                              style={{ background: n ? `color-mix(in oklab, var(--band) ${Math.round(12 + fill * 70)}%, white)` : "var(--carton)" }}
                              aria-label={`Corsia ${c} scaffale ${s}: ${n} pezzi`}
                            >
                              <span className={`code text-[20px] font-bold ${fill > 0.45 ? "text-white" : n ? "text-band-deep" : "text-ink-3"}`}>{n || "·"}</span>
                            </button>
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p className="mt-3 text-[13px] text-ink-3">Intensità del blu = riempimento dello scaffale (capienza indicativa {cap} pezzi).</p>
          </div>
        </Panel>

        <Panel title={sel ? `Scaffale ${mag}/${sel.corsia}-${sel.scaffale}` : "Scaffale"}>
          {!sel ? (
            <p className="px-4 py-8 text-center text-ink-2">Seleziona uno scaffale dalla mappa.</p>
          ) : (
            <div className="p-4">
              {/* ripiani dall'alto verso il basso, come si vedono davanti allo scaffale */}
              <div className="space-y-1.5">
                {w.ripiani.split("").reverse().map((r) => (
                  <div key={r} className="grid grid-cols-[32px_1fr] items-stretch gap-2">
                    <span className="code grid place-items-center rounded bg-ink text-[18px] font-bold text-white">{r}</span>
                    <div className="grid gap-1.5" style={{ gridTemplateColumns: `repeat(${Math.max(w.contenitori, 1)}, minmax(0,1fr))` }}>
                      {Array.from({ length: Math.max(w.contenitori, 1) }, (_, bi) => {
                        const b = w.contenitori ? String(bi + 1) : undefined;
                        const here = shelfParts.filter((p) => p.location!.ripiano === r && (p.location!.contenitore ?? undefined) === b);
                        return (
                          <div key={bi} className="min-h-14 rounded border border-hair-soft bg-carton p-1.5">
                            {b && <span className="code block text-[11px] font-semibold text-ink-3">cont. {b}</span>}
                            {here.map((p) => (
                              <Link key={p.id} href={`/ricambi/${p.id}`} className={`code block truncate text-[14px] font-bold hover:underline ${found?.id === p.id ? "rounded bg-warn-bg text-warn" : "text-band"}`}>
                                {p.id}
                              </Link>
                            ))}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
              <ul className="mt-4 divide-y divide-hair-soft border-t border-hair-soft">
                {shelfParts.map((p) => (
                  <li key={p.id}>
                    <Link href={`/ricambi/${p.id}`} className="grid grid-cols-[44px_1fr_auto] items-center gap-3 py-2 hover:bg-carton">
                      <PartImage src={p.photos[0]} typeId={p.typeId} className="size-11 rounded bg-white [&>span]:hidden" />
                      <span className="min-w-0">
                        <span className="code block text-[16px] font-bold leading-none">{p.id} <span className="font-semibold text-ink-3">· {p.location!.ripiano}{p.location!.contenitore ? `-${p.location!.contenitore}` : ""}</span></span>
                        <span className="block truncate text-sm">{p.description}</span>
                      </span>
                      <StatusChip status={p.status} />
                    </Link>
                  </li>
                ))}
                {shelfParts.length === 0 && <li className="py-4 text-center text-ink-3">Scaffale vuoto</li>}
              </ul>
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
