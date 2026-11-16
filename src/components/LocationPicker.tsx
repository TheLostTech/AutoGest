"use client";

import { Wand2 } from "lucide-react";
import { useStore } from "@/lib/store";
import { corsiaId, firstFreeSlot, locLong, locToString, scaffaleId, warehouseFor, WAREHOUSES, whById } from "@/lib/warehouse";
import { typeById } from "@/lib/catalog";
import type { Location } from "@/lib/types";
import { Button, Field } from "./ui";

// Selezione a cascata: Magazzino → Corsia → Scaffale → Ripiano → Contenitore
export function LocationPicker({ value, onChange, typeId }: { value: Location; onChange: (l: Location) => void; typeId: string }) {
  const parts = useStore((s) => s.parts);
  const w = whById(value.mag) ?? WAREHOUSES[0];
  const t = typeById(typeId);
  const suggested = warehouseFor(t.category, t.shippable);
  const range = (n: number) => Array.from({ length: n }, (_, i) => i + 1);
  const setMag = (mag: string) => {
    const nw = whById(mag)!;
    onChange({ mag, corsia: corsiaId(1), scaffale: scaffaleId(1), ripiano: nw.ripiani[0], contenitore: nw.contenitori ? "1" : undefined });
  };
  const inSlot = parts.filter((p) => p.location && locToString(p.location) === locToString(value) && p.status !== "venduto" && p.status !== "scartato").length;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-band-tint px-3 py-2 text-sm text-band-deep">
        <span>
          Consigliato per <b>{t.category.toLowerCase()}</b>: {suggested.name} · {suggested.desc}
        </span>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => {
            const free = firstFreeSlot(suggested, parts);
            if (free) onChange(free);
          }}
        >
          <Wand2 className="size-4" aria-hidden /> Prima posizione libera
        </Button>
      </div>
      <Field label="Magazzino">
        <select className="field" value={value.mag} onChange={(e) => setMag(e.target.value)}>
          {WAREHOUSES.map((x) => (
            <option key={x.id} value={x.id}>{x.id === "P" ? x.name : `${x.name}`} · {x.desc}</option>
          ))}
        </select>
      </Field>
      <div className={`grid gap-3 ${w.contenitori ? "grid-cols-2 sm:grid-cols-4" : "grid-cols-3"}`}>
        <Field label="Corsia">
          <select className="field code text-[18px] font-bold" value={value.corsia} onChange={(e) => onChange({ ...value, corsia: e.target.value })}>
            {range(w.corsie).map((n) => <option key={n}>{corsiaId(n)}</option>)}
          </select>
        </Field>
        <Field label="Scaffale">
          <select className="field code text-[18px] font-bold" value={value.scaffale} onChange={(e) => onChange({ ...value, scaffale: e.target.value })}>
            {range(w.scaffali).map((n) => <option key={n}>{scaffaleId(n)}</option>)}
          </select>
        </Field>
        <Field label="Ripiano">
          <select className="field code text-[18px] font-bold" value={value.ripiano} onChange={(e) => onChange({ ...value, ripiano: e.target.value })}>
            {w.ripiani.split("").map((r) => <option key={r}>{r}</option>)}
          </select>
        </Field>
        {w.contenitori > 0 && (
          <Field label="Contenitore">
            <select className="field code text-[18px] font-bold" value={value.contenitore ?? "1"} onChange={(e) => onChange({ ...value, contenitore: e.target.value })}>
              {range(w.contenitori).map((n) => <option key={n}>{n}</option>)}
            </select>
          </Field>
        )}
      </div>
      <div>
        <p className="code text-[30px] font-bold leading-none">{locToString(value)}</p>
        <p className="mt-1 text-sm text-ink-2">
          {locLong(value)} · {inSlot === 0 ? "vuoto" : `${inSlot} pezzi già presenti`}
          {inSlot >= w.perSlot && <b className="text-warn"> · pieno</b>}
        </p>
      </div>
    </div>
  );
}
