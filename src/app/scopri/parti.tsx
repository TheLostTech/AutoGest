"use client";

import { useEffect, useRef, useState } from "react";
import { Barcode, Qr } from "@/components/codes";
import { BRAND } from "@/lib/config";

const ID = "R-000417";
const QR = ID;

// L'etichetta dell'apertura: esce dalla fessura della fascia blu come da una stampante termica.
export function EtichettaStampata() {
  return (
    <article className="scopri-etichetta label-sheet @container relative mx-auto flex w-full max-w-[460px] flex-col overflow-hidden" aria-label={`Etichetta del ricambio ${ID}`}>
      <div className="flex items-center justify-between bg-band px-4 py-1.5 text-white">
        <span className="code text-[12px] font-semibold uppercase tracking-[0.12em]">{BRAND.azienda}</span>
        <span className="code text-[12px] font-semibold uppercase tracking-[0.12em]">Ottica</span>
      </div>
      <div className="flex gap-3 px-4 pt-3">
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="code whitespace-nowrap text-[min(15.5cqw,76px)] font-bold leading-[0.88] tracking-[-0.01em]">{ID}</div>
          <div className="mt-1.5 text-[17px] font-semibold leading-tight">Faro anteriore sinistro</div>
          <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-2 text-[13px] leading-snug text-ink-2">
            <dt className="font-semibold text-ink-3">Da</dt>
            <dd className="code truncate font-semibold text-ink">V-000118 · Grande Punto · GH 482 KL</dd>
            <dt className="font-semibold text-ink-3">Pratica</dt>
            <dd className="code truncate">CR-2026/0381</dd>
            <dt className="font-semibold text-ink-3">Stato</dt>
            <dd className="truncate">B · Buono · Anteriore sx</dd>
          </dl>
        </div>
        <div className="flex shrink-0 flex-col items-center">
          <Qr value={QR} size={104} />
          <span className="code mt-0.5 text-[17px] font-bold">3/T03-104-B-1</span>
        </div>
      </div>
      <div className="px-4 pb-3 pt-2">
        <Barcode value={ID} height={34} className="h-[30px] w-full" />
      </div>
    </article>
  );
}

// La stessa etichetta, già stampata, nella fermata «Etichetta»
export function EtichettaPiccola() {
  return (
    <div className="relative">
      <div className="mx-auto max-w-[460px] -rotate-[1.2deg] lg:mx-0">
        <EtichettaStampata />
      </div>
      <p className="mt-4 text-[14px] text-ink-3">Formato 100×50 mm, per le stampanti di etichette più comuni.</p>
    </div>
  );
}

// La linea a fermate del percorso: si riempie di blu mentre scorri.
export function Percorso({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLOListElement>(null);
  const [fill, setFill] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let raf = 0;
    const misura = () => {
      raf = 0;
      const r = el.getBoundingClientRect();
      const punto = window.innerHeight * 0.55;
      const p = Math.min(1, Math.max(0, (punto - r.top) / r.height));
      setFill(p);
      el.querySelectorAll<HTMLElement>("[data-fermata]").forEach((li) => {
        const t = li.getBoundingClientRect().top + 14;
        li.toggleAttribute("data-raggiunta", t < punto);
      });
    };
    const chiedi = () => {
      if (!raf) raf = requestAnimationFrame(misura);
    };
    misura();
    window.addEventListener("scroll", chiedi, { passive: true });
    window.addEventListener("resize", chiedi);
    return () => {
      window.removeEventListener("scroll", chiedi);
      window.removeEventListener("resize", chiedi);
      cancelAnimationFrame(raf);
    };
  }, []);
  return (
    <ol ref={ref} className="scopri-percorso" style={{ "--riempimento": fill } as React.CSSProperties} aria-label="Le fermate di un ricambio">
      {children}
    </ol>
  );
}
