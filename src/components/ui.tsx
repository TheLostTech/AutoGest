"use client";

import Link from "next/link";
import { ImageOff } from "lucide-react";
import type { ComponentProps, ReactNode } from "react";
import type { ListingStatus, OrderStatus, PartStatus } from "@/lib/types";
import type { StockLevel } from "@/lib/logic";
import { typeById } from "@/lib/catalog";

type Variant = "primary" | "secondary" | "quiet" | "danger";

const BTN: Record<Variant, string> = {
  primary: "bg-band text-white hover:bg-band-deep active:bg-band-deep disabled:bg-hair disabled:text-ink-3",
  secondary: "bg-label text-ink border border-hair hover:border-ink-3 active:bg-carton disabled:text-ink-3",
  quiet: "text-band hover:bg-band-tint active:bg-band-tint disabled:text-ink-3",
  danger: "bg-label text-danger border border-danger/40 hover:bg-danger-bg disabled:text-ink-3",
};

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  ...props
}: ComponentProps<"button"> & { variant?: Variant; size?: "md" | "lg" | "sm" }) {
  const sz = size === "lg" ? "min-h-14 px-6 text-lg" : size === "sm" ? "min-h-9 px-3 text-sm" : "min-h-12 px-5 text-base";
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-2 rounded-md font-semibold transition-colors duration-150 disabled:cursor-not-allowed ${sz} ${BTN[variant]} ${className}`}
    />
  );
}

export function ButtonLink({
  variant = "primary",
  size = "md",
  className = "",
  ...props
}: ComponentProps<typeof Link> & { variant?: Variant; size?: "md" | "lg" | "sm" }) {
  const sz = size === "lg" ? "min-h-14 px-6 text-lg" : size === "sm" ? "min-h-9 px-3 text-sm" : "min-h-12 px-5 text-base";
  return <Link {...props} className={`inline-flex items-center justify-center gap-2 rounded-md font-semibold transition-colors duration-150 ${sz} ${BTN[variant]} ${className}`} />;
}

const PART_STATUS: Record<PartStatus, string> = {
  bozza: "border border-dashed border-draft text-draft bg-label",
  disponibile: "bg-ok-bg text-ok",
  riservato: "bg-warn-bg text-warn",
  venduto: "bg-ink text-white",
  invendibile: "bg-danger-bg text-danger",
  scartato: "bg-hair-soft text-ink-2 line-through",
};

export function StatusChip({ status, className = "" }: { status: PartStatus; className?: string }) {
  return <span className={`inline-flex h-7 items-center rounded px-2.5 text-[13px] font-semibold uppercase tracking-wide code ${PART_STATUS[status]} ${className}`}>{status}</span>;
}

const LISTING: Record<ListingStatus, string> = {
  "non pubblicato": "text-ink-3",
  pubblicato: "text-band",
  ritirato: "text-warn",
};
export function ListingChip({ listing }: { listing: ListingStatus }) {
  return (
    <span className={`code inline-flex items-center gap-1.5 text-[13px] font-semibold uppercase tracking-wide ${LISTING[listing]}`}>
      {listing === "pubblicato" && <span className="size-2 rounded-full bg-band" aria-hidden />}
      {listing === "pubblicato" ? "online" : listing === "ritirato" ? "ritirato" : "non online"}
    </span>
  );
}

const ORDER: Record<OrderStatus, string> = {
  "in attesa di pagamento": "bg-warn-bg text-warn",
  pagato: "bg-ok-bg text-ok",
  "pagamento fallito": "bg-danger-bg text-danger",
  annullato: "bg-hair-soft text-ink-2",
  spedito: "bg-band-tint text-band",
  consegnato: "bg-ink text-white",
  reso: "bg-danger-bg text-danger",
};
export function OrderChip({ status }: { status: OrderStatus }) {
  return <span className={`code inline-flex h-7 items-center rounded px-2.5 text-[13px] font-semibold uppercase tracking-wide ${ORDER[status]}`}>{status}</span>;
}

const LEVEL: Record<StockLevel, string> = {
  manca: "bg-danger text-white",
  "sotto soglia": "bg-warn-bg text-warn",
  sufficiente: "bg-ok-bg text-ok",
  eccesso: "bg-hair-soft text-ink-2",
};
export function LevelChip({ level }: { level: StockLevel }) {
  return <span className={`code inline-flex h-7 items-center rounded px-2.5 text-[13px] font-semibold uppercase tracking-wide ${LEVEL[level]}`}>{level}</span>;
}

// Targa: rappresentazione funzionale, riconoscibile a colpo d'occhio
export function Plate({ plate, size = "md" }: { plate: string; size?: "sm" | "md" | "lg" }) {
  const s = size === "lg" ? "h-11 text-[26px]" : size === "sm" ? "h-6 text-[14px]" : "h-8 text-[19px]";
  const band = size === "lg" ? "w-5" : size === "sm" ? "w-2.5" : "w-3.5";
  return (
    <span className={`inline-flex items-stretch overflow-hidden rounded-[4px] border border-ink/70 bg-white ${s}`}>
      <span className={`${band} bg-band`} aria-hidden />
      <span className="code flex items-center px-2 font-semibold tracking-[0.06em] text-ink">{plate.slice(0, 2)} {plate.slice(2, 5)} {plate.slice(5)}</span>
      <span className={`${band} bg-band`} aria-hidden />
    </span>
  );
}

export function PartImage({ src, typeId, className = "", alt }: { src?: string; typeId: string; className?: string; alt?: string }) {
  if (src) {
    // I render da catalogo non sono foto del pezzo reale: vanno dichiarati.
    const demo = src.startsWith("/renders/");
    return (
      <div className={`relative ${className}`}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={src} alt={alt ?? typeById(typeId).name} className="size-full object-contain" />
        {demo && <span className="absolute bottom-1 right-1 rounded bg-white/90 px-1.5 py-0.5 text-[11px] font-medium text-ink-2">immagine dimostrativa</span>}
      </div>
    );
  }
  return (
    <div className={`flex flex-col items-center justify-center gap-1 border border-dashed border-hair bg-carton text-ink-3 ${className}`}>
      <ImageOff className="size-6" strokeWidth={1.6} aria-hidden />
      <span className="text-xs font-medium">foto mancante</span>
    </div>
  );
}

export function PageTitle({ title, sub, actions }: { title: ReactNode; sub?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-[28px] font-bold leading-tight tracking-tight text-ink md:text-[34px]">{title}</h1>
        {sub && <p className="mt-1 max-w-[70ch] text-ink-2">{sub}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Panel({ title, action, children, className = "" }: { title?: ReactNode; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-md border border-hair bg-label ${className}`}>
      {title && (
        <header className="flex items-center justify-between gap-3 border-b border-hair-soft px-4 py-3">
          <h2 className="text-[15px] font-bold uppercase tracking-wide text-ink-2 code">{title}</h2>
          {action}
        </header>
      )}
      <div>{children}</div>
    </section>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="px-5 py-10 text-center">
      <p className="font-semibold text-ink">{title}</p>
      {children && <div className="mt-1 text-sm text-ink-2">{children}</div>}
    </div>
  );
}

export function Field({ label, hint, children, error }: { label: string; hint?: string; children: ReactNode; error?: string }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-semibold text-ink">{label}</span>
      {children}
      {error ? <span className="mt-1 block text-sm font-medium text-danger">{error}</span> : hint ? <span className="mt-1 block text-sm text-ink-3">{hint}</span> : null}
    </label>
  );
}

export function Notice({ tone = "info", children }: { tone?: "info" | "warn" | "danger" | "ok"; children: ReactNode }) {
  const t = tone === "warn" ? "bg-warn-bg text-warn" : tone === "danger" ? "bg-danger-bg text-danger" : tone === "ok" ? "bg-ok-bg text-ok" : "bg-band-tint text-band-deep";
  return <div className={`rounded-md px-4 py-3 text-[15px] font-medium ${t}`}>{children}</div>;
}
