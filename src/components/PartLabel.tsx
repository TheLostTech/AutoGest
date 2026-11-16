"use client";

import { Barcode, partUrl, Qr } from "./codes";
import { typeById, CONDITIONS } from "@/lib/catalog";
import { locToString } from "@/lib/warehouse";
import type { Part, Vehicle } from "@/lib/types";
import { BRAND } from "@/lib/config";

// Firma del sistema: la scheda ricambio È l'etichetta che verrà stampata e applicata al pezzo.
export function PartLabel({ part, vehicle, size = "md", className = "" }: { part: Part; vehicle?: Vehicle; size?: "md" | "print"; className?: string }) {
  const t = typeById(part.typeId);
  const print = size === "print";
  return (
    <article
      className={`label-sheet relative flex flex-col overflow-hidden ${print ? "h-[50mm] w-[100mm] rounded-none shadow-none" : "w-full"} ${className}`}
      aria-label={`Etichetta ricambio ${part.id}`}
    >
      <div className={`flex items-center justify-between bg-band text-white ${print ? "px-[3mm] py-[1mm]" : "px-4 py-1.5"}`}>
        <span className={`code font-semibold uppercase tracking-[0.12em] ${print ? "text-[7pt]" : "text-[12px]"}`}>{BRAND.azienda}</span>
        <span className={`code font-semibold uppercase tracking-[0.12em] ${print ? "text-[7pt]" : "text-[12px]"}`}>{t.category}</span>
      </div>
      <div className={`flex min-h-0 flex-1 gap-3 ${print ? "px-[3mm] pt-[1.5mm]" : "px-4 pt-3"}`}>
        <div className="flex min-w-0 flex-1 flex-col">
          <div className={`code font-bold leading-[0.9] tracking-tight text-ink ${print ? "text-[30pt]" : "text-[clamp(44px,12vw,68px)]"}`}>{part.id}</div>
          <div className={`mt-1 font-semibold leading-tight text-ink ${print ? "truncate text-[8.5pt]" : "line-clamp-2 text-[17px]"}`}>{part.description}</div>
          <dl className={`mt-auto grid grid-cols-[auto_1fr] gap-x-2 text-ink-2 ${print ? "text-[7pt] leading-tight" : "mt-2 text-[13px] leading-snug"}`}>
            <dt className="font-semibold text-ink-3">Da</dt>
            <dd className="code truncate font-semibold text-ink">
              {part.vehicleId}
              {vehicle && <span className="font-medium text-ink-2"> · {vehicle.make} {vehicle.model} · {vehicle.plate}</span>}
            </dd>
            <dt className="font-semibold text-ink-3">Pratica</dt>
            <dd className="code truncate">{vehicle?.dossier.number || "da registrare"}</dd>
            <dt className="font-semibold text-ink-3">Stato</dt>
            <dd className="truncate">
              {part.condition} · {CONDITIONS[part.condition].label}
              {part.side ? ` · ${part.side}` : ""}
            </dd>
          </dl>
        </div>
        <div className="flex shrink-0 flex-col items-center">
          <Qr value={partUrl(part.id)} size={print ? 82 : 112} />
          {part.location ? (
            <span className={`code mt-0.5 font-bold text-ink ${print ? "text-[9pt]" : "text-[18px]"}`}>{locToString(part.location)}</span>
          ) : (
            <span className={`mt-0.5 font-semibold text-ink-3 ${print ? "text-[6pt]" : "text-[12px]"}`}>posizione da assegnare</span>
          )}
        </div>
      </div>
      <div className={print ? "px-[3mm] pb-[1.5mm] pt-[1mm]" : "px-4 pb-3 pt-2"}>
        <Barcode value={part.id} height={print ? 22 : 34} className="h-[22px] w-full md:h-[30px]" />
      </div>
    </article>
  );
}
