"use client";

import Link from "next/link";
import { Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, Printer } from "lucide-react";
import { useStore } from "@/lib/store";
import { corsiaId, layoutOf, natural, normLoc, scaffaleId } from "@/lib/warehouse";
import { ShelfLabel } from "@/components/ShelfLabel";
import type { Location } from "@/lib/types";

export default function Page() {
  return (
    <Suspense>
      <Stampa />
    </Suspense>
  );
}

// "A-E" → A B C D E · "1-6" → 1…6 · "A, C, F" → A C F
function parseList(raw: string): string[] {
  const out: string[] = [];
  for (const piece of raw.toUpperCase().split(/[,;\s]+/).filter(Boolean)) {
    const m = piece.match(/^([A-Z]|\d+)-([A-Z]|\d+)$/);
    if (m && /\d/.test(m[1]) === /\d/.test(m[2])) {
      const num = /\d/.test(m[1]);
      const a = num ? Number(m[1]) : m[1].charCodeAt(0);
      const b = num ? Number(m[2]) : m[2].charCodeAt(0);
      for (let i = Math.min(a, b); i <= Math.max(a, b) && out.length < 60; i++) out.push(num ? String(i) : String.fromCharCode(i));
    } else out.push(piece);
  }
  return [...new Set(out)];
}

function Stampa() {
  const sp = useSearchParams();
  const warehouses = useStore((s) => s.warehouses);
  const parts = useStore((s) => s.parts);
  const [mag, setMag] = useState(sp.get("mag") ?? warehouses[0]?.id ?? "1");
  const [corsia, setCorsia] = useState(sp.get("c") ?? "");
  const [scaffale, setScaffale] = useState(sp.get("s") ?? "");
  const [ripiani, setRipiani] = useState("");
  const [boxes, setBoxes] = useState(false);
  const w = warehouses.find((x) => x.id === mag) ?? warehouses[0];

  const labels = useMemo(() => {
    const lay = layoutOf(w, parts);
    const want = normLoc(w.id, corsia || "X", scaffale || "X", "X");
    // Scaffali da etichettare: quelli previsti dal magazzino più quelli già usati; uno scaffale scritto a mano vale anche se vuoto
    const combos = new Map<string, [string, string]>();
    for (let c = 1; c <= w.corsie; c++) for (let s = 1; s <= w.scaffali; s++) combos.set(`${corsiaId(c)}|${scaffaleId(s, w)}`, [corsiaId(c), scaffaleId(s, w)]);
    for (const p of lay.inside) combos.set(`${p.location!.corsia}|${p.location!.scaffale}`, [p.location!.corsia, p.location!.scaffale]);
    if (corsia && scaffale) combos.set(`${want.corsia}|${want.scaffale}`, [want.corsia, want.scaffale]);
    const picked = [...combos.values()]
      .filter(([c, s]) => (!corsia || c === want.corsia) && (!scaffale || s === want.scaffale))
      .sort((a, b) => natural(a[0], b[0]) || natural(a[1], b[1]));

    const out: Location[] = [];
    for (const [c, s] of picked) {
      const onShelf = lay.inside.filter((p) => p.location!.corsia === c && p.location!.scaffale === s);
      const rips = ripiani.trim() ? parseList(ripiani) : lay.ripiani(onShelf);
      for (const r of rips) {
        out.push({ mag: w.id, corsia: c, scaffale: s, ripiano: r });
        if (boxes) for (const b of lay.contenitori(onShelf.filter((p) => p.location!.ripiano === r))) out.push({ mag: w.id, corsia: c, scaffale: s, ripiano: r, contenitore: b });
      }
    }
    return out;
  }, [w, parts, corsia, scaffale, ripiani, boxes]);

  const tooMany = labels.length > 600;
  const shown = tooMany ? labels.slice(0, 600) : labels;

  return (
    <div className="min-h-dvh bg-ground p-4 print:bg-white print:p-0 md:p-8">
      <style>{`@page { size: 100mm 50mm; margin: 0; } @media print { .shelf-label { break-after: page; } } @media screen and (max-width: 440px) { .shelf-label { zoom: 0.84; } }`}</style>
      <div className="no-print mx-auto max-w-4xl">
        <Link href={`/magazzino?mag=${encodeURIComponent(w.id)}`} className="mb-3 inline-flex items-center gap-1.5 text-[15px] font-semibold text-band">
          <ArrowLeft className="size-4" aria-hidden /> Mappa del magazzino
        </Link>
        <h1 className="text-[30px] font-bold leading-tight">Etichette scaffale</h1>
        <p className="mt-1 text-ink-2">
          Una per ripiano: si attacca sul bordo del ripiano. Con la scansione, <b>pezzo → scaffale</b> mette a posto il pezzo e <b>scaffale → pezzo</b> lo preleva.
        </p>

        <div className="mt-5 grid gap-3 rounded-md border border-hair bg-label p-4 sm:grid-cols-4">
          <label className="block">
            <span className="mb-1 block text-sm font-semibold">Magazzino</span>
            <select className="field" value={w.id} onChange={(e) => { setMag(e.target.value); setCorsia(""); setScaffale(""); }}>
              {warehouses.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-semibold">Corsia</span>
            <input className="field code text-[18px] font-bold uppercase" value={corsia} onChange={(e) => setCorsia(e.target.value)} placeholder="tutte" />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-semibold">Scaffale</span>
            <input className="field code text-[18px] font-bold uppercase" value={scaffale} onChange={(e) => setScaffale(e.target.value)} placeholder="tutti" />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-semibold">Ripiani</span>
            <input className="field code text-[18px] font-bold uppercase" value={ripiani} onChange={(e) => setRipiani(e.target.value)} placeholder={w.ripiani ? `${w.ripiani[0]}-${w.ripiani.at(-1)}` : "A-E o 1-6"} />
          </label>
          <label className="flex min-h-11 items-center gap-2 sm:col-span-4">
            <input type="checkbox" className="size-5 accent-[var(--band)]" checked={boxes} onChange={(e) => setBoxes(e.target.checked)} />
            <span>Anche un&apos;etichetta per ogni contenitore</span>
          </label>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-ink-2">
            <b className="code text-[20px] text-ink">{labels.length}</b> etichette · formato 100 × 50 mm, una per foglio sulla stampante etichette
            {tooMany && <span className="text-warn"> · mostro le prime 600: stampa per corsia</span>}
          </p>
          <button onClick={() => window.print()} disabled={labels.length === 0} className="inline-flex min-h-12 items-center gap-2 rounded-md bg-band px-5 font-semibold text-white hover:bg-band-deep disabled:opacity-40">
            <Printer className="size-5" aria-hidden /> Stampa
          </button>
        </div>
        {labels.length === 0 && (
          <p className="mt-6 rounded-md border border-hair bg-label px-5 py-8 text-center text-ink-2">
            Nessuno scaffale da etichettare. Scrivi corsia, scaffale e ripiani (es. <b className="code">A-E</b>) per stampare le etichette di uno scaffale ancora vuoto.
          </p>
        )}
      </div>

      <div className="mx-auto mt-6 flex max-w-4xl flex-wrap justify-center gap-4 print:m-0 print:block print:max-w-none">
        {shown.map((l) => (
          <div key={`${l.corsia}-${l.scaffale}-${l.ripiano}-${l.contenitore ?? ""}`} className="shelf-label">
            <ShelfLabel loc={l} warehouseName={w.name} />
          </div>
        ))}
      </div>
    </div>
  );
}
