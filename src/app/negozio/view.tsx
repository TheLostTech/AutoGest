"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import { useStore } from "@/lib/store";
import { PART_TYPES, PLATFORMS, CONDITIONS, TYPE_GROUPS, miniRender, typeById } from "@/lib/catalog";
import { euro, fits } from "@/lib/logic";
import { onlinePrice } from "@/lib/pricing";
import { nextToShip, partsOf, quantityOf } from "@/lib/annunci";
import type { Annuncio, Part } from "@/lib/types";
import { PartImage } from "@/components/ui";

// Le tipologie sono centinaia: prima si sceglie la categoria, poi il tipo tra quelli in vendita.
// La copertina di una categoria è il primo tipo del catalogo con un'immagine.
const CATS = TYPE_GROUPS.map(([cat]) => ({ cat, cover: PART_TYPES.find((t) => t.category === cat && t.render) }));

export default function Negozio() {
  const { parts, vehicles, annunci } = useStore();
  // Negozio chiuso (azienda bloccata): il server lo dice nel catalogo
  const [chiuso, setChiuso] = useState(false);
  useEffect(() => {
    fetch("/api/negozio/catalogo", { cache: "no-store" })
      .then((r) => r.json())
      .then((j: { chiuso?: boolean }) => setChiuso(j.chiuso === true))
      .catch(() => undefined);
  }, []);
  const [make, setMake] = useState("");
  const [platform, setPlatform] = useState("");
  const [cat, setCat] = useState("");
  const [type, setType] = useState("");
  const [q, setQ] = useState("");
  const vById = useMemo(() => new Map(vehicles.map((v) => [v.id, v])), [vehicles]);
  const makes = [...new Set(PLATFORMS.map((p) => p.make))];

  // Annunci del negozio con il pezzo da mostrare: il prossimo a partire o, se esauriti, l'ultimo entrato
  const shown = annunci
    .filter((a) => a.negozio && a.negozio.stato !== "ritirato")
    .flatMap((a) => {
      const qty = quantityOf(a, parts);
      const mine = partsOf(a, parts);
      const rep: Part | undefined = qty > 0 ? nextToShip(a, parts)[0] : [...mine].sort((x, y) => y.createdAt.localeCompare(x.createdAt))[0];
      return rep ? [{ a, qty, rep }] : [];
    });
  const query = q.trim().toLowerCase();
  const matches = shown.filter(({ a, rep: p }) => {
    const v = vById.get(p.vehicleId);
    if (platform && !fits(p, v?.platform, platform)) return false;
    if (make && !platform && v?.make !== make && !p.compat?.platforms.some((pl) => PLATFORMS.find((x) => x.id === pl)?.make === make)) return false;
    if (cat && typeById(a.typeId).category !== cat) return false;
    if (type && a.typeId !== type) return false;
    if (query && !`${a.titolo} ${a.descrizione} ${a.oem ?? ""} ${a.oem?.replace(/[\s.-]/g, "") ?? ""} ${p.manufacturer ?? ""} ${a.id}`.toLowerCase().includes(query)) return false;
    return true;
  });
  const list = matches.filter((x) => x.qty > 0);
  const esauriti = matches.filter((x) => x.qty === 0);

  const card = ({ a, qty, rep: p }: { a: Annuncio; qty: number; rep: Part }) => {
    const v = vById.get(p.vehicleId);
    return (
      <li key={a.id}>
        <Link href={`/negozio/${a.id}`} className={`label-sheet flex h-full flex-col overflow-hidden transition-colors hover:border-band ${qty === 0 ? "opacity-70" : ""}`}>
          <div className="flex items-center justify-between bg-band px-3 py-1 text-white">
            <span className="code text-[11px] font-semibold uppercase tracking-[0.12em]">{typeById(a.typeId).category}</span>
            {qty === 0 ? <span className="code text-[11px] font-semibold uppercase tracking-[0.12em]">Esaurito</span> : p.compat?.verified && <span className="code text-[11px] font-semibold uppercase tracking-[0.12em]">OE verificato</span>}
          </div>
          <PartImage src={p.photos[0]} typeId={a.typeId} className="aspect-square w-full bg-white p-3" />
          <div className="flex flex-1 flex-col border-t border-hair-soft p-3">
            <span className="code text-[26px] font-bold leading-none">{a.id}</span>
            <span className="mt-1 line-clamp-2 font-semibold leading-snug">{a.titolo}</span>
            <span className="mt-1 text-[13px] text-ink-2">
              {v ? <>da {v.make} {v.model} {v.year} · <span className="code font-semibold">{p.vehicleId}</span></> : p.pastDossier?.model ? `da ${p.pastDossier.model}` : "dal nostro magazzino"}
            </span>
            {qty > 1 && <span className="mt-1 text-[13px] font-semibold text-band">{qty} disponibili</span>}
            {platform && v?.platform !== platform && <span className="mt-1 text-[13px] font-semibold text-ok">Compatibile con la tua auto (codice OE verificato)</span>}
            <span className="mt-auto flex items-end justify-between pt-3">
              <span className="code text-[26px] font-bold leading-none">{euro(onlinePrice(a.price))}</span>
              <span className="flex items-center gap-1.5" title={CONDITIONS[a.condition].label}>
                <span className="text-[12px] text-ink-3">cond.</span>
                <span className="code grid size-8 place-items-center rounded border-2 border-ink text-[20px] font-bold leading-none">{a.condition}</span>
              </span>
            </span>
          </div>
        </Link>
      </li>
    );
  };

  if (chiuso) {
    return (
      <div className="mx-auto max-w-xl py-16 text-center" role="status">
        <h1 className="text-[28px] font-bold tracking-tight">Negozio momentaneamente chiuso</h1>
        <p className="mt-3 text-ink-2">Il catalogo non è disponibile in questo momento. Torna a trovarci tra poco.</p>
      </div>
    );
  }

  return (
    <div>
      <section className="grid items-center gap-6 overflow-hidden rounded-md bg-band text-white md:grid-cols-[1.1fr_1fr]">
        <div className="p-6 md:p-10">
          <h1 className="text-[34px] font-bold leading-[1.05] tracking-tight md:text-[48px]">Il ricambio giusto, dal veicolo da cui proviene.</h1>
          <p className="mt-3 max-w-[48ch] text-[17px] text-white/85">Ogni pezzo è fotografato, controllato e identificato da un codice univoco. Scegli la tua auto e vedi solo ciò che è davvero disponibile.</p>
          <div className="mt-6 grid gap-2 sm:grid-cols-2">
            <select className="h-12 rounded-md border-0 bg-white px-3 font-semibold text-ink" value={make} onChange={(e) => { setMake(e.target.value); setPlatform(""); }} aria-label="Marca">
              <option value="">Marca</option>
              {makes.map((m) => <option key={m}>{m}</option>)}
            </select>
            <select className="h-12 rounded-md border-0 bg-white px-3 font-semibold text-ink disabled:text-ink-3" value={platform} onChange={(e) => setPlatform(e.target.value)} disabled={!make} aria-label="Modello">
              <option value="">Modello</option>
              {PLATFORMS.filter((p) => p.make === make).map((p) => <option key={p.id} value={p.id}>{p.model} · {p.years}</option>)}
            </select>
            <label className="relative sm:col-span-2">
              <Search className="absolute left-3 top-1/2 size-5 -translate-y-1/2 text-ink-3" aria-hidden />
              <input className="h-12 w-full rounded-md border-0 bg-white pl-10 pr-3 font-medium text-ink placeholder:text-ink-3" placeholder="Cerca pezzo o codice OEM" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Cerca" />
            </label>
          </div>
        </div>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/renders/scatola.png" alt="Scatola ricambio con etichetta" className="mx-auto hidden max-h-[380px] w-full object-contain p-6 md:block" />
      </section>

      <nav className="mt-6 flex gap-2 overflow-x-auto pb-2" aria-label="Categorie">
        <button onClick={() => { setCat(""); setType(""); }} className={`flex min-h-24 shrink-0 flex-col items-center justify-center rounded-md border px-5 font-semibold ${!cat ? "border-band bg-band-tint text-band" : "border-hair bg-label"}`}>
          Tutto
        </button>
        {CATS.map(({ cat: c, cover }) => (
          <button key={c} onClick={() => { setCat(c === cat ? "" : c); setType(""); }} className={`flex w-32 shrink-0 flex-col items-center gap-1 rounded-md border p-2 text-sm font-semibold ${cat === c ? "border-band bg-band-tint text-band" : "border-hair bg-label"}`}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            {cover?.render ? <img src={miniRender(cover.render)} alt="" loading="lazy" className="size-16 object-contain" /> : <span className="size-16" />}
            {c}
          </button>
        ))}
      </nav>
      {cat && (
        <nav className="mt-2 flex flex-wrap gap-2" aria-label={`Tipi di ${cat}`}>
          {[...new Set(shown.filter(({ a }) => typeById(a.typeId).category === cat).map(({ a }) => a.typeId))]
            .map((id) => typeById(id))
            .sort((x, y) => x.name.localeCompare(y.name, "it"))
            .map((t) => (
              <button key={t.id} onClick={() => setType(t.id === type ? "" : t.id)} className={`flex min-h-12 items-center gap-2 rounded-md border px-3 text-sm font-semibold ${type === t.id ? "border-band bg-band-tint text-band" : "border-hair bg-label"}`}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                {t.render && <img src={miniRender(t.render)} alt="" loading="lazy" className="size-9 object-contain" />}
                {t.name}
              </button>
            ))}
        </nav>
      )}

      <div className="mt-4 flex items-baseline justify-between">
        <h2 className="text-[22px] font-bold">{list.length} {list.length === 1 ? "ricambio disponibile" : "ricambi disponibili"}</h2>
        {(make || cat || type || q) && <button onClick={() => { setMake(""); setPlatform(""); setCat(""); setType(""); setQ(""); }} className="text-sm font-semibold text-band">Azzera filtri</button>}
      </div>

      <ul className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">{list.map(card)}</ul>
      {list.length === 0 && (
        <p className="mt-6 rounded-md border border-hair bg-label p-6 text-center text-ink-2">
          Nessun ricambio online per questa ricerca. I ricambi compaiono solo quando la scheda è completa e verificata.
        </p>
      )}
      {esauriti.length > 0 && (
        <section className="mt-10">
          <h2 className="text-[22px] font-bold">Esauriti</h2>
          <p className="text-sm text-ink-2">Chiamaci: potremmo averne altri o trovarli per te.</p>
          <ul className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">{esauriti.map(card)}</ul>
        </section>
      )}
    </div>
  );
}
