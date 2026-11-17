"use client";

import { absUrl, Barcode, Qr } from "./codes";
import { shelfCode, shelfPath } from "@/lib/warehouse";
import type { Location } from "@/lib/types";
import { BRAND } from "@/lib/config";

// Etichetta di ripiano (o contenitore), stesso formato 100 × 50 mm dell'etichetta ricambio.
// La lettera del ripiano è enorme: si legge da lontano, a scaffale pieno.
export function ShelfLabel({ loc, warehouseName }: { loc: Location; warehouseName: string }) {
  const code = shelfCode(loc);
  return (
    <article className="label-sheet flex h-[50mm] w-[100mm] shrink-0 flex-col overflow-hidden rounded-none shadow-none print:border-0" aria-label={`Etichetta scaffale ${code}`}>
      <div className="flex items-center justify-between bg-ink px-[3mm] py-[1mm] text-white">
        <span className="code text-[7pt] font-semibold uppercase tracking-[0.12em]">{BRAND.azienda}</span>
        <span className="code text-[7pt] font-semibold uppercase tracking-[0.12em]">{warehouseName}</span>
      </div>
      <div className="flex min-h-0 flex-1 gap-[3mm] px-[3mm] pt-[1.5mm]">
        <div className="flex min-w-0 flex-1 flex-col">
          <dl className="code grid grid-cols-[auto_1fr] items-baseline gap-x-[2mm] text-[8pt] leading-tight">
            <dt className="text-ink-3">CORSIA</dt>
            <dd className="text-[13pt] font-bold">{loc.corsia}</dd>
            <dt className="text-ink-3">SCAFFALE</dt>
            <dd className="text-[13pt] font-bold">{loc.scaffale}</dd>
          </dl>
          <div className="mt-auto flex items-end gap-[2mm]">
            <span className="code text-[40pt] font-bold leading-[0.8]">{loc.ripiano}</span>
            {loc.contenitore && <span className="code pb-[1mm] text-[16pt] font-bold leading-none">· {loc.contenitore}</span>}
          </div>
          <span className="code mt-[0.5mm] text-[6.5pt] font-semibold uppercase tracking-wide text-ink-3">{loc.contenitore ? "Ripiano · contenitore" : "Ripiano"}</span>
        </div>
        <div className="flex shrink-0 flex-col items-center">
          <Qr value={absUrl(shelfPath(loc))} size={92} />
          <span className="code mt-0.5 text-[9pt] font-bold">{code}</span>
        </div>
      </div>
      <div className="px-[3mm] pb-[1.5mm] pt-[1mm]">
        <Barcode value={code} height={20} className="h-[20px] w-full" />
      </div>
    </article>
  );
}
