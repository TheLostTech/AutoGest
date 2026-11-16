"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowRight, Plus } from "lucide-react";
import { useStore } from "@/lib/store";
import { PART_TYPES } from "@/lib/catalog";
import { corsiaId, locToString, ripianiCount, scaffaleId, type Warehouse } from "@/lib/warehouse";
import { Button, Field, Notice, PageTitle, Panel } from "@/components/ui";

const CATEGORIES = [...new Set(PART_TYPES.map((t) => t.category))];
const LETTERS = "ABCDEFGHIJ";

export default function Inventario() {
  const { warehouses, inventory, parts, addWarehouse } = useStore();
  const [open, setOpen] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  // Ripiani contati: l'ultima conta di ciascun ripiano vale per l'avanzamento
  const counted = (w: Warehouse) => new Set(inventory.filter((c) => c.mag === w.id).map((c) => `${c.corsia}-${c.scaffale}-${c.ripiano}`)).size;
  const missing = parts.filter((p) => p.missingSince).length;

  return (
    <div className="mx-auto max-w-5xl">
      <PageTitle
        title="Inventario"
        sub="Cataloga quello che è già a scaffale, un ripiano alla volta: la posizione la dà lo scaffale su cui stai lavorando, il tipo di pezzo lo propone la foto."
        actions={!open && <Button onClick={() => setOpen(true)}><Plus className="size-5" aria-hidden /> Nuovo magazzino</Button>}
      />
      {msg && <div className="mb-5"><Notice tone="ok">{msg}</Notice></div>}
      {missing > 0 && (
        <div className="mb-5">
          <Notice tone="warn">
            {missing} {missing === 1 ? "ricambio registrato non è stato trovato" : "ricambi registrati non sono stati trovati"} al suo posto durante le conte.{" "}
            <Link href="/ricambi" className="font-semibold underline">Cercali nel magazzino</Link>
          </Notice>
        </div>
      )}

      {open && (
        <NewWarehouse
          existing={warehouses}
          onCancel={() => setOpen(false)}
          onSave={(w) => {
            addWarehouse(w);
            setOpen(false);
            setMsg(`${w.name} creato: ${ripianiCount(w)} ripiani da contare. Le posizioni vanno da ${w.id}/${corsiaId(1)}-${scaffaleId(1)}-A a ${w.id}/${corsiaId(w.corsie)}-${scaffaleId(w.scaffali)}-${w.ripiani.at(-1)}.`);
          }}
        />
      )}

      <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {warehouses.map((w) => {
          const tot = ripianiCount(w);
          const done = counted(w);
          const inside = parts.filter((p) => p.location?.mag === w.id && p.status !== "venduto" && p.status !== "scartato").length;
          return (
            <li key={w.id}>
              <Link href={`/inventario/${encodeURIComponent(w.id)}`} className="label-sheet block p-4 hover:border-ink-3">
                <span className="flex items-start justify-between gap-3">
                  <span className="min-w-0">
                    <span className="code block text-[26px] font-bold leading-none">Mag. {w.id}</span>
                    <span className="mt-1 block truncate font-semibold">{w.name}</span>
                    <span className="block truncate text-sm text-ink-2">{w.desc}</span>
                  </span>
                  <ArrowRight className="mt-1 size-5 shrink-0 text-band" aria-hidden />
                </span>
                <span className="mt-3 flex items-baseline justify-between gap-3 text-sm">
                  <span className="text-ink-2">
                    {w.corsie} corsie × {w.scaffali} scaffali × {w.ripiani.length} ripiani{w.contenitori ? ` × ${w.contenitori} contenitori` : ""}
                  </span>
                  <span className="code shrink-0 font-semibold">{inside} pezzi</span>
                </span>
                <span className="mt-2 block h-2 overflow-hidden rounded-full bg-hair-soft" role="img" aria-label={`${done} ripiani contati su ${tot}`}>
                  <span className="block h-full rounded-full bg-band" style={{ width: `${(done / tot) * 100}%` }} />
                </span>
                <span className="mt-1 block text-sm text-ink-3">{done === 0 ? "Conta non iniziata" : `${done} di ${tot} ripiani contati`}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function NewWarehouse({ existing, onSave, onCancel }: { existing: Warehouse[]; onSave: (w: Warehouse) => void; onCancel: () => void }) {
  const [id, setId] = useState(String(existing.filter((w) => /^\d+$/.test(w.id)).length + 1));
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [cats, setCats] = useState<string[]>([]);
  const [corsie, setCorsie] = useState("4");
  const [scaffali, setScaffali] = useState("6");
  const [ripiani, setRipiani] = useState("4");
  const [contenitori, setContenitori] = useState("0");
  const [perSlot, setPerSlot] = useState("2");
  const num = (x: string, min: number, max: number) => Math.min(max, Math.max(min, Number(x) || min));
  const code = id.trim().toUpperCase();
  const taken = existing.some((w) => w.id.toUpperCase() === code);
  const valid = /^[A-Z0-9]{1,3}$/.test(code) && !taken && name.trim().length > 1;
  const w: Warehouse = {
    id: code,
    name: name.trim(),
    desc: desc.trim() || cats.join(", ") || "Magazzino",
    categories: cats,
    corsie: num(corsie, 1, 40),
    scaffali: num(scaffali, 1, 60),
    ripiani: LETTERS.slice(0, num(ripiani, 1, 10)),
    contenitori: num(contenitori, 0, 20),
    perSlot: num(perSlot, 1, 50),
  };
  const intField = (label: string, v: string, set: (x: string) => void, hint?: string) => (
    <Field label={label} hint={hint}>
      <input className="field code text-[18px] font-bold" inputMode="numeric" value={v} onChange={(e) => set(e.target.value.replace(/[^0-9]/g, ""))} />
    </Field>
  );

  return (
    <Panel title="Nuovo magazzino" className="mb-6">
      <div className="grid gap-4 p-4 sm:grid-cols-2">
        <Field label="Codice" hint="Il numero o la sigla che usate già (es. 5, P, M2)" error={taken ? "Codice già usato da un altro magazzino" : undefined}>
          <input className="field code text-[18px] font-bold uppercase" value={id} maxLength={3} onChange={(e) => setId(e.target.value)} />
        </Field>
        <Field label="Nome">
          <input className="field" value={name} onChange={(e) => setName(e.target.value)} placeholder="Es. Magazzino 5 – soppalco" />
        </Field>
        <div className="sm:col-span-2">
          <span className="mb-1.5 block text-sm font-semibold">Cosa contiene</span>
          <div className="flex flex-wrap gap-1.5">
            {CATEGORIES.map((c) => {
              const on = cats.includes(c);
              return (
                <button
                  key={c}
                  type="button"
                  aria-pressed={on}
                  onClick={() => setCats((xs) => (on ? xs.filter((x) => x !== c) : [...xs, c]))}
                  className={`h-9 rounded-full border px-3 text-[14px] font-semibold ${on ? "border-band bg-band-tint text-band" : "border-hair bg-label text-ink-2"}`}
                >
                  {c}
                </button>
              );
            })}
          </div>
          <span className="mt-1 block text-sm text-ink-3">Serve a proporre il magazzino giusto quando si cataloga, e a restringere il riconoscimento da foto.</span>
        </div>
        <Field label="Descrizione (facoltativa)">
          <input className="field" value={desc} onChange={(e) => setDesc(e.target.value)} />
        </Field>
        <div className="grid grid-cols-2 gap-3 sm:col-span-2 sm:grid-cols-5">
          {intField("Corsie", corsie, setCorsie)}
          {intField("Scaffali per corsia", scaffali, setScaffali)}
          {intField("Ripiani", ripiani, setRipiani, `A–${w.ripiani.at(-1)}`)}
          {intField("Contenitori", contenitori, setContenitori, "0 = ripiano libero")}
          {intField("Pezzi per posto", perSlot, setPerSlot)}
        </div>
        <p className="rounded-md bg-carton px-4 py-3 text-[15px] sm:col-span-2">
          <span className="text-ink-3">Posizioni da </span>
          <b className="code">{locToString({ mag: code || "?", corsia: corsiaId(1), scaffale: scaffaleId(1), ripiano: "A", contenitore: w.contenitori ? "1" : undefined })}</b>
          <span className="text-ink-3"> a </span>
          <b className="code">{locToString({ mag: code || "?", corsia: corsiaId(w.corsie), scaffale: scaffaleId(w.scaffali), ripiano: w.ripiani.at(-1)!, contenitore: w.contenitori ? String(w.contenitori) : undefined })}</b>
          <span className="text-ink-3"> · {ripianiCount(w)} ripiani</span>
        </p>
        <div className="flex flex-wrap gap-2 sm:col-span-2">
          <Button disabled={!valid} onClick={() => onSave(w)}>Crea magazzino</Button>
          <Button variant="quiet" onClick={onCancel}>Annulla</Button>
        </div>
      </div>
    </Panel>
  );
}
