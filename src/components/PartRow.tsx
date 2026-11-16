"use client";

import Link from "next/link";
import type { Part } from "@/lib/types";
import { euro } from "@/lib/logic";
import { locToString } from "@/lib/warehouse";
import { ListingChip, PartImage, StatusChip } from "./ui";

export function PartRow({ part, href, right }: { part: Part; href?: string; right?: React.ReactNode }) {
  return (
    <Link href={href ?? `/ricambi/${part.id}`} className="grid grid-cols-[64px_1fr_auto] items-center gap-3 px-4 py-3 hover:bg-carton md:grid-cols-[64px_130px_1fr_120px_110px_90px]">
      <PartImage src={part.photos[0]} typeId={part.typeId} className="size-16 rounded bg-white [&>span]:hidden" />
      <span className="code hidden text-[24px] font-bold leading-none md:block">{part.id}</span>
      <span className="min-w-0">
        <span className="code block text-[20px] font-bold leading-none md:hidden">{part.id}</span>
        <span className="block truncate font-semibold">{part.description}</span>
        <span className="mt-0.5 flex flex-wrap items-center gap-x-3 text-sm text-ink-3">
          <span>da {part.vehicleId}</span>
          {part.legacyCode && <span className="code">{part.legacyCode}</span>}
          {part.oem && <span className="code">OE {part.oem}</span>}
          <ListingChip listing={part.listing} />
        </span>
      </span>
      <span className="hidden md:block">
        <StatusChip status={part.status} />
      </span>
      <span className="code hidden text-[18px] font-bold md:block">{locToString(part.location)}</span>
      <span className="text-right">
        {right ?? (
          <>
            <span className="code block text-[20px] font-bold">{euro(part.price)}</span>
            <span className="md:hidden"><StatusChip status={part.status} /></span>
          </>
        )}
      </span>
    </Link>
  );
}
