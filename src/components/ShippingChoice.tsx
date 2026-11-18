"use client";

import { Store as StoreIcon, Truck } from "lucide-react";

// Due pulsanti grandi: il pezzo ingombrante si spedisce con corriere oppure resta solo ritiro.
export function ShippingChoice({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
  const opts: { v: boolean; label: string; Icon: typeof Truck }[] = [
    { v: true, label: "Sì, con corriere", Icon: Truck },
    { v: false, label: "No, solo ritiro in sede", Icon: StoreIcon },
  ];
  return (
    <fieldset>
      <legend className="mb-1.5 text-sm font-semibold">Si può spedire?</legend>
      <div className="grid grid-cols-2 gap-2">
        {opts.map(({ v, label, Icon }) => (
          <button
            key={String(v)}
            type="button"
            onClick={() => onChange(v)}
            aria-pressed={value === v}
            className={`flex min-h-16 items-center gap-3 rounded-md border px-3 text-left ${value === v ? "border-band bg-band text-white" : "border-hair bg-label"}`}
          >
            <Icon className="size-6 shrink-0" aria-hidden />
            <span className="text-[15px] font-semibold leading-tight">{label}</span>
          </button>
        ))}
      </div>
    </fieldset>
  );
}
