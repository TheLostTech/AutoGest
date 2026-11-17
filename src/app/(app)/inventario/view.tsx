"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowRight, Plus } from "lucide-react";
import { useStore } from "@/lib/store";
import { type Warehouse } from "@/lib/warehouse";
import { Button, Field, Notice, PageTitle, Panel } from "@/components/ui";

const LETTERS = "ABCDEFGHIJ";

export default function Inventario() {
  const { warehouses, parts, addWarehouse } = useStore();
  const router = useRouter();
  const [open, setOpen] = useState(false);

  const missing = parts.filter((p) => p.missingSince && p.status !== "venduto" && p.status !== "scartato").length;

  return (
    <div className="mx-auto max-w-5xl">
      <PageTitle
        title="Inventario"
        sub="Apri un magazzino e aggiungi i ricambi che ci sono già, con la loro ubicazione. Crea un magazzino nuovo quando serve."
        actions={!open && <Button onClick={() => setOpen(true)}><Plus className="size-5" aria-hidden /> Crea magazzino</Button>}
      />
      {missing > 0 && (
        <div className="mb-5">
          <Notice tone="warn">
            {missing} {missing === 1 ? "ricambio registrato non è stato trovato" : "ricambi registrati non sono stati trovati"} al suo posto durante le conte.{" "}
            <Link href="/ricambi?filtro=mancanti" className="font-semibold underline">Vedi quali sono</Link>
          </Notice>
        </div>
      )}

      {open && (
        <NewWarehouse
          existing={warehouses}
          onCancel={() => setOpen(false)}
          onSave={(w) => {
            addWarehouse(w);
            router.push(`/inventario/${encodeURIComponent(w.id)}`);
          }}
        />
      )}

      <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {warehouses.map((w) => {
          const inside = parts.filter((p) => p.location?.mag === w.id && p.status !== "venduto" && p.status !== "scartato");
          const fromInv = inside.filter((p) => p.origin === "inventario").length;
          return (
            <li key={w.id}>
              <Link href={`/inventario/${encodeURIComponent(w.id)}`} className="label-sheet flex items-center gap-4 p-4 hover:border-ink-3">
                <span className="code grid size-16 shrink-0 place-items-center rounded bg-band text-[26px] font-bold text-white">{w.id}</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[18px] font-semibold">{w.name}</span>
                  <span className="block text-sm text-ink-2">
                    <b className="code text-[16px] text-ink">{inside.length}</b> {inside.length === 1 ? "ricambio" : "ricambi"}
                    {fromInv > 0 && ` · ${fromInv} inseriti con l'inventario`}
                  </span>
                </span>
                <ArrowRight className="size-5 shrink-0 text-band" aria-hidden />
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
  const [corsie, setCorsie] = useState("10");
  const [scaffali, setScaffali] = useState("20");
  const [ripiani, setRipiani] = useState("6");
  const [withDims, setWithDims] = useState(false);
  const num = (x: string, min: number, max: number) => Math.min(max, Math.max(min, Number(x) || min));
  const code = id.trim().toUpperCase();
  const taken = existing.some((w) => w.id.toUpperCase() === code);
  const valid = /^[A-Z0-9]{1,3}$/.test(code) && !taken;
  const w: Warehouse = {
    id: code,
    name: name.trim() || `Magazzino ${code}`,
    desc: "Magazzino",
    categories: [],
    // Senza dimensioni la mappa si compone dalle ubicazioni scritte sui ricambi
    corsie: withDims ? num(corsie, 1, 99) : 0,
    scaffali: withDims ? num(scaffali, 1, 999) : 0,
    primoScaffale: 1,
    ripiani: withDims ? LETTERS.slice(0, num(ripiani, 1, 10)) : "",
    contenitori: 0,
    perSlot: withDims ? 50 : 0,
  };

  return (
    <Panel title="Crea magazzino" className="mb-6">
      <div className="grid gap-4 p-4 sm:grid-cols-[160px_1fr]">
        <Field label="Numero o sigla" hint="Come lo chiamate già (es. 1, 5, P)" error={taken ? "Esiste già un magazzino con questo codice" : undefined}>
          <input className="field code text-[22px] font-bold uppercase" value={id} maxLength={3} onChange={(e) => setId(e.target.value)} autoFocus />
        </Field>
        <Field label="Nome (facoltativo)">
          <input className="field" value={name} onChange={(e) => setName(e.target.value)} placeholder={`Magazzino ${code || "…"}`} />
        </Field>
        <details className="sm:col-span-2" onToggle={(e) => setWithDims(e.currentTarget.open)}>
          <summary className="flex min-h-10 cursor-pointer list-none items-center gap-1.5 text-[15px] font-semibold text-band">Dimensioni per la mappa (facoltative)</summary>
          <div className="mt-2 grid grid-cols-3 gap-3">
            {(
              [
                ["Corsie", corsie, setCorsie],
                ["Scaffali per corsia", scaffali, setScaffali],
                ["Ripiani", ripiani, setRipiani],
              ] as const
            ).map(([label, v, set]) => (
              <Field key={label} label={label}>
                <input className="field code text-[18px] font-bold" inputMode="numeric" value={v} onChange={(e) => set(e.target.value.replace(/[^0-9]/g, ""))} />
              </Field>
            ))}
          </div>
          <p className="mt-1 text-sm text-ink-3">Disegnano in anticipo la mappa, con scaffali numerati da 1. Se non le indicate, la mappa si compone da sola con le ubicazioni che scrivete inserendo i ricambi.</p>
        </details>
        <div className="flex flex-wrap gap-2 sm:col-span-2">
          <Button disabled={!valid} onClick={() => onSave(w)}>Crea e apri</Button>
          <Button variant="quiet" onClick={onCancel}>Annulla</Button>
        </div>
      </div>
    </Panel>
  );
}
