"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Boxes,
  CarFront,
  ClipboardCheck,
  History,
  LayoutGrid,
  Map as MapIcon,
  ScanLine,
  ShoppingCart,
  SlidersHorizontal,
  Store,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { ROLE_USER, useStore } from "@/lib/store";
import type { Role } from "@/lib/types";
import { BRAND, DEMO_NOTICE } from "@/lib/config";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

const ALL: Record<string, NavItem> = {
  oggi: { href: "/", label: "Oggi", icon: LayoutGrid },
  campo: { href: "/campo", label: "Smontaggio", icon: Wrench },
  veicoli: { href: "/veicoli", label: "Veicoli", icon: CarFront },
  ricambi: { href: "/ricambi", label: "Ricambi", icon: Boxes },
  mappa: { href: "/magazzino", label: "Ubicazioni", icon: MapIcon },
  scan: { href: "/scansione", label: "Scansiona", icon: ScanLine },
  pubblica: { href: "/pubblicazione", label: "Pubblicazione", icon: ClipboardCheck },
  vendite: { href: "/vendite", label: "Vendite", icon: ShoppingCart },
  regole: { href: "/regole", label: "Regole scorte", icon: SlidersHorizontal },
  registro: { href: "/registro", label: "Registro", icon: History },
};

const BY_ROLE: Record<Role, string[]> = {
  accettazione: ["oggi", "veicoli", "scan", "registro"],
  smontatore: ["campo", "scan", "ricambi", "veicoli"],
  magazziniere: ["scan", "mappa", "ricambi", "veicoli", "registro"],
  responsabile: ["oggi", "veicoli", "ricambi", "mappa", "pubblica", "vendite", "regole", "registro"],
  vendite: ["vendite", "ricambi", "mappa", "scan", "veicoli"],
};

const ROLES: Role[] = ["accettazione", "smontatore", "magazziniere", "responsabile", "vendite"];

export function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const role = useStore((s) => s.role);
  const setRole = useStore((s) => s.setRole);
  const items = BY_ROLE[role].map((k) => ALL[k]);
  const active = (href: string) => (href === "/" ? path === "/" : path === href || path.startsWith(href + "/"));

  return (
    <div className="min-h-dvh md:grid md:grid-cols-[232px_1fr]">
      {/* Fascia blu: come la stampa sulla scatola */}
      <aside className="no-print hidden bg-band text-white md:sticky md:top-0 md:flex md:h-dvh md:flex-col">
        <div className="px-5 pb-5 pt-6">
          <div className="code text-[26px] font-bold uppercase leading-none tracking-wide">{BRAND.azienda}</div>
          <div className="mt-1 text-[13px] font-medium text-white/75">Gestionale ricambi</div>
        </div>
        <nav className="flex-1 space-y-0.5 px-2" aria-label="Sezioni">
          {items.map((it) => (
            <Link
              key={it.href}
              href={it.href}
              className={`flex min-h-11 items-center gap-3 rounded px-3 text-[15px] font-semibold transition-colors ${
                active(it.href) ? "bg-white text-band" : "text-white/90 hover:bg-white/12"
              }`}
              aria-current={active(it.href) ? "page" : undefined}
            >
              <it.icon className="size-[18px]" strokeWidth={2} aria-hidden />
              {it.label}
            </Link>
          ))}
          <Link href="/negozio" className="mt-4 flex min-h-11 items-center gap-3 rounded border border-white/30 px-3 text-[15px] font-semibold text-white hover:bg-white/12">
            <Store className="size-[18px]" strokeWidth={2} aria-hidden />
            Negozio online
          </Link>
        </nav>
        <RoleSwitch role={role} setRole={setRole} />
      </aside>

      <div className="flex min-h-dvh min-w-0 flex-col">
        {/* Testata mobile */}
        <header className="no-print sticky top-0 z-30 flex items-center justify-between gap-3 bg-band px-4 py-2.5 text-white md:hidden">
          <Link href="/" className="code text-[20px] font-bold uppercase tracking-wide">{BRAND.azienda}</Link>
          <label className="flex items-center gap-2">
            <span className="sr-only">Ruolo</span>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as Role)}
              className="h-10 rounded border border-white/40 bg-band-deep px-2 text-[15px] font-semibold text-white"
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {ROLE_USER[r].label}
                </option>
              ))}
            </select>
          </label>
        </header>
        <div className="no-print border-b border-hair bg-carton px-4 py-1.5 text-center text-[12px] font-semibold uppercase tracking-[0.14em] text-ink-3 code md:text-right">
          {DEMO_NOTICE} · {ROLE_USER[role].user} · {ROLE_USER[role].device}
        </div>
        <main className="flex-1 px-4 pb-28 pt-5 md:px-8 md:pb-12 md:pt-7">{children}</main>

        {/* Barra inferiore mobile: bersagli grandi, usabili coi guanti */}
        <nav className="no-print fixed inset-x-0 bottom-0 z-30 grid border-t border-hair bg-label pb-[env(safe-area-inset-bottom)] md:hidden" style={{ gridTemplateColumns: `repeat(${Math.min(items.length, 4)}, 1fr)` }} aria-label="Sezioni">
          {items.slice(0, 4).map((it) => (
            <Link
              key={it.href}
              href={it.href}
              className={`flex min-h-16 flex-col items-center justify-center gap-1 text-[12px] font-semibold ${active(it.href) ? "text-band" : "text-ink-2"}`}
              aria-current={active(it.href) ? "page" : undefined}
            >
              <span className={`grid h-8 w-14 place-items-center rounded-full ${active(it.href) ? "bg-band-tint" : ""}`}>
                <it.icon className="size-[22px]" strokeWidth={2} aria-hidden />
              </span>
              {it.label}
            </Link>
          ))}
        </nav>
      </div>
    </div>
  );
}

function RoleSwitch({ role, setRole }: { role: Role; setRole: (r: Role) => void }) {
  const reset = useStore((s) => s.reset);
  return (
    <div className="border-t border-white/20 p-4">
      <label className="block">
        <span className="code mb-1 block text-[12px] font-semibold uppercase tracking-[0.14em] text-white/70">Stai usando come</span>
        <select value={role} onChange={(e) => setRole(e.target.value as Role)} className="h-10 w-full rounded border border-white/40 bg-band-deep px-2 text-[15px] font-semibold text-white">
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {ROLE_USER[r].label}
            </option>
          ))}
        </select>
      </label>
      <button
        onClick={() => {
          if (confirm("Ripristinare i dati dimostrativi iniziali? Le modifiche fatte nella demo andranno perse.")) reset();
        }}
        className="mt-3 text-[13px] font-semibold text-white/75 underline hover:text-white"
      >
        Ripristina dati demo
      </button>
    </div>
  );
}
