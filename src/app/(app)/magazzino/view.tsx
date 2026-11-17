"use client";

import Link from "next/link";
import { Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Printer, Search } from "lucide-react";
import { useStore } from "@/lib/store";
import { layoutOf, locLong, sameShelf, slotCapacity } from "@/lib/warehouse";
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
const compact = (x?: string) => (x ?? "").toUpperCase().replace(/[\s\-.]/g, "");

// Trova accetta il codice come lo dice la gente: "R-002304", "r2304", "2304", il codice vecchio o l'OE
function matches(p: Part, raw: string) {
  const q = compact(raw);
  if (!q) return false;
  const digits = q.replace(/^R/, "");
  return compact(p.id) === q || (/^\d+$/.test(digits) && Number(p.id.replace(/\D/g, "")) === Number(digits)) || compact(p.legacyCode) === q || compact(p.oem) === q;
}

function Mappa() {
  const sp = useSearchParams();
  const parts = useStore((s) => s.parts);
  const WAREHOUSES = useStore((s) => s.warehouses);
  const stocked = useMemo(() => parts.filter(present), [parts]);
  const [mag, setMag] = useState(sp.get("mag") ?? "1");
  // Dal QR di un'etichetta scaffale (/u/…) si arriva qui con lo scaffale già aperto
  const [sel, setSel] = useState<{ corsia: string; scaffale: string } | null>(sp.get("c") && sp.get("s") ? { corsia: sp.get("c")!, scaffale: sp.get("s")! } : null);
  const fromLabel = sel && sel.corsia === sp.get("c") && sel.scaffale === sp.get("s") ? sp.get("r") : null;
  const [find, setFind] = useState("");
  const [found, setFound] = useState<Part | null>(null);
  const [miss, setMiss] = useState(false);

  const w = WAREHOUSES.find((x) => x.id === mag) ?? WAREHOUSES[0];
  const lay = layoutOf(w, stocked);
  const inMag = lay.inside;
  const count = (c: string, s: string) => inMag.filter((p) => sameShelf(p.location, w.id, c, s)).length;
  // Capienza prevista se il magazzino ha una struttura; altrimenti si confronta con lo scaffale più pieno
  const cap = slotCapacity(w) || Math.max(1, ...lay.corsie.flatMap((c) => lay.scaffali.map((s) => count(c, s))));
  const shelfParts = sel ? inMag.filter((p) => sameShelf(p.location, w.id, sel.corsia, sel.scaffale)) : [];
  const usedShelves = new Set(inMag.map((p) => `${p.location!.corsia}|${p.location!.scaffale}`)).size;

  function locate(e: React.FormEvent) {
    e.preventDefault();
    const p = stocked.find((x) => matches(x, find));
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
              <span className="code mt-1 block text-[15px] font-semibold">{n === 1 ? "1 pezzo" : `${n} pezzi`}</span>
            </button>
          );
        })}
      </div>

      <div className="mb-3 flex justify-end">
        <Link href={`/etichette-scaffale?mag=${encodeURIComponent(w.id)}`} className="inline-flex min-h-10 items-center gap-1.5 text-[15px] font-semibold text-band">
          <Printer className="size-4" aria-hidden /> Etichette scaffale di {w.name}
        </Link>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Panel className="min-w-0" title={`${w.name} · ${lay.corsie.length === 1 ? "1 corsia" : `${lay.corsie.length} corsie`} · ${usedShelves === 1 ? "1 scaffale occupato" : `${usedShelves} scaffali occupati`}`}>
          {lay.corsie.length === 0 ? (
            <div className="px-5 py-10 text-center">
              <p className="font-semibold">Ancora nessuna ubicazione in questo magazzino</p>
              <p className="mt-1 text-ink-2">La mappa si compone da sola con le ubicazioni che scrivete inserendo i ricambi.</p>
              <Link href={`/inventario/${encodeURIComponent(w.id)}/nuovo`} className="mt-4 inline-flex min-h-11 items-center rounded-md bg-band px-4 font-semibold text-white hover:bg-band-deep">Aggiungi un ricambio</Link>
            </div>
          ) : (
          <div className="overflow-x-auto p-4">
            <table className="w-full table-fixed border-separate border-spacing-1.5" style={{ minWidth: 56 + lay.scaffali.length * 52 }}>
              <thead>
                <tr>
                  <th className="code w-14 text-left text-[13px] font-semibold uppercase tracking-wide text-ink-3">Corsia</th>
                  {lay.scaffali.map((s) => (
                    <th key={s} className="code truncate text-[13px] font-semibold text-ink-3" title={`Scaffale ${s}`}>{s}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {lay.corsie.map((c) => {
                  return (
                    <tr key={c}>
                      <th className="code truncate text-left text-[18px] font-bold" title={`Corsia ${c}`}>{c}</th>
                      {lay.scaffali.map((s) => {
                        const n = count(c, s);
                        const fill = Math.min(1, n / cap);
                        const active = sel?.corsia === c && sel?.scaffale === s;
                        const hit = found?.location && sameShelf(found.location, w.id, c, s);
                        return (
                          <td key={s}>
                            <button
                              onClick={() => setSel({ corsia: c, scaffale: s })}
                              className={`relative grid h-14 w-full min-w-11 place-items-center overflow-hidden rounded border text-center ${active ? "border-band ring-2 ring-band" : "border-hair"} ${hit ? "ring-4 ring-warn" : ""}`}
                              style={{ background: n ? `color-mix(in oklab, var(--band) ${Math.round(12 + fill * 70)}%, white)` : "var(--carton)" }}
                              aria-label={`Corsia ${c} scaffale ${s}: ${n === 1 ? "1 pezzo" : `${n} pezzi`}`}
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
            <p className="mt-3 text-[13px] text-ink-3">
              {slotCapacity(w) ? `Intensità del blu = riempimento dello scaffale (capienza indicativa ${cap} pezzi).` : "Intensità del blu = quanti pezzi ci sono rispetto allo scaffale più pieno."}
            </p>
          </div>
          )}
        </Panel>

        <Panel title={sel ? `Scaffale ${w.id}/${sel.corsia}-${sel.scaffale}` : "Scaffale"}>
          {!sel ? (
            <p className="px-4 py-8 text-center text-ink-2">Seleziona uno scaffale dalla mappa.</p>
          ) : (
            <div className="p-4">
              {/* ripiani dall'alto verso il basso, come si vedono davanti allo scaffale */}
              <div className="space-y-1.5">
                {lay.ripiani(shelfParts).reverse().map((r) => {
                  const onRip = shelfParts.filter((p) => p.location!.ripiano === r);
                  const boxes = lay.contenitori(onRip);
                  // Pezzi messi sul ripiano senza contenitore: hanno la loro casella
                  const slots: (string | undefined)[] = [...boxes, ...(boxes.length === 0 || onRip.some((p) => !p.location!.contenitore) ? [undefined] : [])];
                  return (
                    <div key={r} className="grid grid-cols-[32px_1fr] items-stretch gap-2">
                      <span className={`code grid place-items-center rounded text-[18px] font-bold text-white ${fromLabel === r ? "bg-warn ring-2 ring-warn" : "bg-ink"}`}>{r}</span>
                      <div className="grid gap-1.5" style={{ gridTemplateColumns: `repeat(${Math.min(slots.length, 4)}, minmax(0,1fr))` }}>
                        {slots.map((b) => {
                          const here = onRip.filter((p) => (p.location!.contenitore || undefined) === b);
                          return (
                            <div key={b ?? "-"} className="min-h-14 rounded border border-hair-soft bg-carton p-1.5">
                              {b ? <span className="code block text-[11px] font-semibold text-ink-3">cont. {b}</span> : boxes.length > 0 && <span className="code block text-[11px] font-semibold text-ink-3">sul ripiano</span>}
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
                  );
                })}
              </div>
              <Link
                href={`/etichette-scaffale?${new URLSearchParams({ mag: w.id, c: sel.corsia, s: sel.scaffale })}`}
                className="mt-3 inline-flex min-h-10 items-center gap-1.5 text-sm font-semibold text-band"
              >
                <Printer className="size-4" aria-hidden /> Stampa le etichette di questo scaffale
              </Link>
              <ul className="mt-2 divide-y divide-hair-soft border-t border-hair-soft">
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
