"use client";

import { Wand2 } from "lucide-react";
import { useStore } from "@/lib/store";
import { firstFreeSlot, layoutOf, locLong, locToString, normLoc, warehouseFor, whById } from "@/lib/warehouse";
import { typeById } from "@/lib/catalog";
import type { Location, Part } from "@/lib/types";
import type { Warehouse } from "@/lib/warehouse";
import { Button, Field } from "./ui";

// Ubicazione vuota di un magazzino: la prima prevista, oppure la prima già usata, oppure da scrivere
export function startLocation(mag: string, warehouses: Warehouse[], parts: Part[]): Location {
  const w = whById(mag, warehouses) ?? warehouses[0];
  const lay = layoutOf(w, parts);
  const onFirst = lay.inside.filter((p) => p.location!.corsia === lay.corsie[0] && p.location!.scaffale === lay.scaffali[0]);
  return {
    mag: w.id,
    corsia: lay.corsie[0] ?? "",
    scaffale: lay.scaffali[0] ?? "",
    ripiano: lay.ripiani(onFirst)[0] ?? "",
    contenitore: w.contenitori ? "1" : undefined,
  };
}

export const locComplete = (l: Location) => !!(l.corsia && l.scaffale && l.ripiano);

// Magazzino → Corsia → Scaffale → Ripiano → Contenitore.
// Le scelte sono le posizioni previste dal magazzino più quelle già scritte sui ricambi;
// si può sempre scrivere una posizione nuova, come si fa sull'etichetta dello scaffale.
export function LocationPicker({ value, onChange, typeId }: { value: Location; onChange: (l: Location) => void; typeId: string }) {
  const parts = useStore((s) => s.parts);
  const WAREHOUSES = useStore((s) => s.warehouses);
  const w = whById(value.mag, WAREHOUSES) ?? WAREHOUSES[0];
  const t = typeById(typeId);
  const suggested = warehouseFor(t.category, t.shippable, WAREHOUSES);
  const free = firstFreeSlot(suggested, parts);
  const lay = layoutOf(w, parts);
  const onShelf = lay.inside.filter((p) => p.location!.corsia === value.corsia && p.location!.scaffale === value.scaffale);
  const set = (patch: Partial<Location>) => onChange({ ...value, ...patch });
  // Normalizza quando si esce dal campo: "04" e "4" sono lo stesso scaffale
  const tidy = () => onChange(normLoc(value.mag, value.corsia, value.scaffale, value.ripiano, value.contenitore));
  const inSlot = parts.filter((p) => p.location && locToString(p.location) === locToString(value) && p.status !== "venduto" && p.status !== "scartato").length;

  const slot = (label: string, key: "corsia" | "scaffale" | "ripiano" | "contenitore", options: string[]) => (
    <Field label={label}>
      <input
        className="field code text-[18px] font-bold uppercase"
        list={`loc-${key}`}
        value={value[key] ?? ""}
        onChange={(e) => set({ [key]: e.target.value.toUpperCase() || (key === "contenitore" ? undefined : "") })}
        onBlur={tidy}
        onFocus={(e) => e.currentTarget.select()}
        autoComplete="off"
      />
      <datalist id={`loc-${key}`}>
        {options.map((o) => <option key={o} value={o} />)}
      </datalist>
    </Field>
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-band-tint px-3 py-2 text-sm text-band-deep">
        <span>
          Consigliato per <b>{t.category.toLowerCase()}</b>: {suggested.name} · {suggested.desc}
        </span>
        {free && (
          <Button size="sm" variant="secondary" onClick={() => onChange(free)}>
            <Wand2 className="size-4" aria-hidden /> Prima posizione libera
          </Button>
        )}
      </div>
      <Field label="Magazzino">
        <select className="field" value={value.mag} onChange={(e) => onChange(startLocation(e.target.value, WAREHOUSES, parts))}>
          {WAREHOUSES.map((x) => (
            <option key={x.id} value={x.id}>{x.name} · {x.desc}</option>
          ))}
        </select>
      </Field>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {slot("Corsia", "corsia", lay.corsie)}
        {slot("Scaffale", "scaffale", lay.scaffali)}
        {slot("Ripiano", "ripiano", lay.ripiani(onShelf))}
        {slot("Contenitore", "contenitore", lay.contenitori(onShelf))}
      </div>
      <div>
        <p className="code text-[30px] font-bold leading-none">{locComplete(value) ? locToString(value) : "—"}</p>
        <p className="mt-1 text-sm text-ink-2">
          {locComplete(value) ? (
            <>
              {locLong(value)} · {inSlot === 0 ? "vuoto" : `${inSlot} pezzi già presenti`}
              {w.perSlot > 0 && inSlot >= w.perSlot && <b className="text-warn"> · pieno</b>}
            </>
          ) : (
            "Scrivi corsia, scaffale e ripiano"
          )}
        </p>
      </div>
    </div>
  );
}
