"use client";

import Link from "next/link";
import { ShoppingBag } from "lucide-react";
import { useCart } from "@/lib/cart";
import { BRAND, DEMO_NOTICE } from "@/lib/config";
import { LostarCredit } from "@/components/Lostar";

export default function ShopLayout({ children }: { children: React.ReactNode }) {
  const n = useCart((s) => s.ids.length);
  return (
    <div className="min-h-dvh bg-ground">
      <div className="bg-ink px-4 py-1.5 text-center text-[12px] font-semibold uppercase tracking-[0.14em] text-white/80 code">
        {DEMO_NOTICE} · negozio online · <Link href="/" className="underline">torna al gestionale</Link>
      </div>
      <header className="sticky top-0 z-30 border-b border-hair bg-label">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <Link href="/negozio" className="flex items-center gap-3">
            <span className="code grid h-10 place-items-center rounded bg-band px-3 text-[22px] font-bold uppercase leading-none tracking-wide text-white">{BRAND.negozio}</span>
            <span className="hidden text-sm font-medium text-ink-2 sm:block">Ricambi usati tracciati, dal veicolo al tuo ordine</span>
          </Link>
          <Link href="/negozio/carrello" className="relative inline-flex min-h-11 items-center gap-2 rounded-md border border-hair px-4 font-semibold hover:border-ink-3">
            <ShoppingBag className="size-5" aria-hidden />
            Carrello
            {n > 0 && <span className="code grid size-6 place-items-center rounded-full bg-band text-[14px] font-bold text-white">{n}</span>}
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 pb-16 pt-6">{children}</main>
      <footer className="border-t border-hair bg-label px-4 py-6 text-center text-sm text-ink-3">
        {BRAND.azienda} · {BRAND.sede} · Ogni ricambio ha un codice univoco e la provenienza dal veicolo d&apos;origine.
        <div className="mt-3">
          <LostarCredit className="text-ink-3 hover:text-ink" />
        </div>
      </footer>
    </div>
  );
}
