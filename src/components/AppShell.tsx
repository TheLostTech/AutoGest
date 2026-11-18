"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Boxes, Briefcase, CarFront, ClipboardList, LayoutGrid, Leaf, Menu, ScanLine, Send, Settings, ShoppingCart, Wrench, X, type LucideIcon } from "lucide-react";
import { useDeviceStorageFull, useStore } from "@/lib/store";
import { RUOLO_LABEL } from "@/lib/accesso/ruoli";
import { esci, useSessione } from "@/lib/accesso/client";
import { useSyncAvviso } from "@/lib/sync";
import type { Role } from "@/lib/types";
import { BRAND, DEMO_NOTICE } from "@/lib/config";
import { GlobalSearch } from "./GlobalSearch";
import { LostarCredit } from "./Lostar";
import { resetShared } from "@/lib/sync";
import { useEbaySync } from "@/lib/ebay-sync";

// Navigazione per aree di lavoro: poche voci, le sottosezioni compaiono solo dentro l'area aperta.
// Un'area senza sottosezioni visibili per il ruolo (o un modulo non attivo) non compare.
const ALL_ROLES: Role[] = ["accettazione", "smontatore", "magazziniere", "responsabile", "vendite"];

interface Sub {
  href: string;
  label: string;
  roles: Role[];
}
interface Area {
  id: string;
  label: string;
  icon: LucideIcon;
  subs: Sub[];
}

const AREAS: Area[] = [
  { id: "oggi", label: "Oggi", icon: LayoutGrid, subs: [{ href: "/", label: "Da fare", roles: [...ALL_ROLES, "consulente"] }] },
  {
    id: "veicoli",
    label: "Veicoli",
    icon: CarFront,
    subs: [
      { href: "/veicoli", label: "Elenco veicoli", roles: ALL_ROLES },
      { href: "/veicoli/nuovo", label: "Nuovo ingresso", roles: ["accettazione", "responsabile"] },
      { href: "/campo", label: "Smontaggio", roles: ["smontatore", "responsabile"] },
    ],
  },
  {
    id: "ricambi",
    label: "Ricambi",
    icon: Boxes,
    subs: [
      { href: "/ricambi", label: "Magazzino", roles: ["smontatore", "magazziniere", "responsabile", "vendite"] },
      { href: "/magazzino", label: "Ubicazioni", roles: ["magazziniere", "responsabile", "vendite"] },
      { href: "/inventario", label: "Inventario", roles: ["magazziniere", "responsabile"] },
      { href: "/rottami", label: "Area rottami", roles: ["smontatore", "magazziniere", "responsabile"] },
      { href: "/pubblicazione", label: "Pubblicazione", roles: ["responsabile"] },
      { href: "/regole", label: "Scorte minime", roles: ["responsabile"] },
    ],
  },
  {
    id: "vendite",
    label: "Vendite",
    icon: ShoppingCart,
    subs: [
      { href: "/vendite", label: "Banco e ordini", roles: ["vendite", "responsabile"] },
      { href: "/vendite/documenti", label: "Documenti", roles: ["vendite", "responsabile"] },
      { href: "/negozio", label: "Negozio online", roles: ["vendite", "responsabile"] },
    ],
  },
  {
    id: "ambiente",
    label: "Ambiente",
    icon: Leaf,
    subs: [
      { href: "/ambiente/periodo", label: "Periodo RENTRI", roles: ["accettazione", "responsabile", "consulente"] },
      { href: "/ambiente", label: "Registro rifiuti", roles: ["accettazione", "responsabile", "consulente"] },
      { href: "/ambiente/formulari", label: "Formulari", roles: ["accettazione", "responsabile", "consulente"] },
      { href: "/ambiente/soggetti", label: "Soggetti", roles: ["accettazione", "responsabile", "consulente"] },
    ],
  },
  {
    id: "ufficio",
    label: "Ufficio",
    icon: Briefcase,
    subs: [
      { href: "/registro", label: "Registro attività", roles: ["accettazione", "magazziniere", "responsabile"] },
      { href: "/listini", label: "Listini", roles: ["responsabile"] },
    ],
  },
  {
    id: "impostazioni",
    label: "Impostazioni",
    icon: Settings,
    subs: [
      { href: "/impostazioni/collegamenti", label: "Collegamenti", roles: ["responsabile"] },
      { href: "/impostazioni/dispositivi", label: "Dispositivi", roles: ["responsabile"] },
    ],
  },
];

// Barra inferiore del telefono: le 4 cose che il ruolo usa davvero sul campo
type Tab = { label: string; icon: LucideIcon } & ({ area: string } | { href: string });
const MOBILE_TABS: Record<Role, Tab[]> = {
  accettazione: [
    { area: "oggi", label: "Oggi", icon: LayoutGrid },
    { area: "veicoli", label: "Veicoli", icon: CarFront },
    { area: "ambiente", label: "Ambiente", icon: Leaf },
    { area: "ufficio", label: "Ufficio", icon: Briefcase },
  ],
  smontatore: [
    { area: "oggi", label: "Oggi", icon: LayoutGrid },
    { href: "/campo", label: "Smontaggio", icon: Wrench },
    { href: "/scansione", label: "Scansiona", icon: ScanLine },
    { area: "ricambi", label: "Ricambi", icon: Boxes },
  ],
  magazziniere: [
    { area: "oggi", label: "Oggi", icon: LayoutGrid },
    { href: "/inventario", label: "Inventario", icon: ClipboardList },
    { href: "/scansione", label: "Scansiona", icon: ScanLine },
    { area: "ricambi", label: "Ricambi", icon: Boxes },
  ],
  responsabile: [
    { area: "oggi", label: "Oggi", icon: LayoutGrid },
    { area: "veicoli", label: "Veicoli", icon: CarFront },
    { area: "ricambi", label: "Ricambi", icon: Boxes },
    { area: "vendite", label: "Vendite", icon: ShoppingCart },
  ],
  vendite: [
    { area: "oggi", label: "Oggi", icon: LayoutGrid },
    { area: "vendite", label: "Vendite", icon: ShoppingCart },
    { area: "ricambi", label: "Ricambi", icon: Boxes },
    { href: "/scansione", label: "Scansiona", icon: ScanLine },
  ],
  consulente: [
    { area: "oggi", label: "Oggi", icon: LayoutGrid },
    { href: "/ambiente/periodo", label: "Periodo", icon: Send },
    { href: "/ambiente", label: "Registro", icon: Leaf },
    { href: "/ambiente/formulari", label: "Formulari", icon: ClipboardList },
  ],
};

const matches = (path: string, href: string) => (href === "/" ? path === "/" : path === href || path.startsWith(href + "/"));

function visibleAreas(role: Role) {
  return AREAS.map((a) => ({ ...a, subs: a.subs.filter((s) => s.roles.includes(role)) })).filter((a) => a.subs.length > 0);
}

// La sottosezione più specifica che corrisponde al percorso (es. /veicoli/nuovo batte /veicoli)
function currentSub(path: string, areas: Area[]) {
  let best: { area: Area; sub: Sub } | undefined;
  for (const area of AREAS) {
    for (const sub of area.subs) {
      if (matches(path, sub.href) && (!best || sub.href.length > best.sub.href.length)) best = { area, sub };
    }
  }
  if (!best) return undefined;
  // Se il ruolo non vede quella sottosezione, resta comunque evidenziata l'area
  const visible = areas.find((a) => a.id === best!.area.id);
  return { areaId: best.area.id, subHref: best.sub.href, area: visible };
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const role = useStore((s) => s.role);
  const setRole = useStore((s) => s.setRole);
  const ruoliPermessi = useStore((s) => s.ruoliPermessi);
  const operatore = useStore((s) => s.operatore);
  const { accesso } = useSessione();
  const avviso = useSyncAvviso();
  const [uscendo, setUscendo] = useState(false);
  const storageFull = useDeviceStorageFull();
  useEbaySync();
  const areas = visibleAreas(role);
  const cur = currentSub(path, areas);
  const tabs = MOBILE_TABS[role];
  const hasScanTab = tabs.some((t) => "href" in t && t.href === "/scansione");
  // Aree che non stanno nella barra inferiore: finiscono sotto "Altro"
  const tabAreas = new Set(tabs.flatMap((t) => ("area" in t ? [t.area] : [])));
  const moreAreas = areas.filter((a) => !tabAreas.has(a.id));
  const [more, setMore] = useState(false);
  const moreRef = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = moreRef.current;
    if (!d) return;
    if (more && !d.open) d.showModal();
    if (!more && d.open) d.close();
  }, [more]);
  const subTabs = cur?.area && cur.area.subs.length > 1 ? cur.area.subs : [];

  // Nella barra inferiore vince la voce più specifica: se una scheda punta proprio a questa pagina, l'area non si accende
  const hrefTabActive = tabs.some((t) => "href" in t && matches(path, t.href));
  const tabActive = (t: Tab) => ("href" in t ? matches(path, t.href) : !hrefTabActive && cur?.areaId === t.area);
  const tabHref = (t: Tab) => ("href" in t ? t.href : (areas.find((a) => a.id === t.area)?.subs[0].href ?? "/"));

  return (
    <div className={`min-h-dvh md:grid md:grid-cols-[232px_1fr] ${accesso?.assistenza ? "pt-11" : ""}`}>
      {accesso?.assistenza && (
        <div role="status" className="no-print fixed inset-x-0 top-0 z-50 flex h-11 items-center justify-center gap-3 bg-ink px-4 text-[14px] font-semibold text-white">
          <span className="truncate">Assistenza in corso · {accesso.azienda.nome}</span>
          <button
            onClick={async () => {
              await fetch("/api/piattaforma/assistenza", { method: "DELETE" }).catch(() => undefined);
              window.location.assign("/piattaforma");
            }}
            className="shrink-0 rounded border border-white/60 px-3 py-1 hover:bg-white/15"
          >
            Esci
          </button>
        </div>
      )}
      {/* Fascia blu: come la stampa sulla scatola */}
      <aside className="no-print hidden bg-band text-white md:sticky md:top-0 md:flex md:h-dvh md:flex-col">
        <div className="px-5 pb-4 pt-6">
          <div className="code text-[26px] font-bold uppercase leading-none tracking-wide">
            {BRAND.azienda.replace(/\s*4\.0$/, "")} <span className="text-[#F4B500]">4.0</span>
          </div>
          <div className="mt-1 text-[13px] font-medium text-white/75">Gestionale autodemolizione</div>
        </div>
        <div className="space-y-2 px-3 pb-4">
          <GlobalSearch variant="sidebar" />
          <Link
            href="/scansione"
            className={`flex min-h-11 items-center justify-center gap-2 rounded-md text-[15px] font-semibold transition-colors ${matches(path, "/scansione") ? "bg-white text-band" : "bg-band-deep text-white hover:bg-white hover:text-band"}`}
          >
            <ScanLine className="size-[18px]" aria-hidden />
            Scansiona etichetta
          </Link>
        </div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto px-2" aria-label="Aree">
          {areas.map((a) => {
            const open = cur?.areaId === a.id;
            return (
              <div key={a.id}>
                <Link
                  href={a.subs[0].href}
                  className={`flex min-h-11 items-center gap-3 rounded px-3 text-[15px] font-semibold transition-colors ${
                    open ? (a.subs.length > 1 ? "text-white" : "bg-white text-band") : "text-white/85 hover:bg-white/12"
                  }`}
                  aria-current={open && a.subs.length === 1 ? "page" : undefined}
                >
                  <a.icon className="size-[18px]" strokeWidth={2} aria-hidden />
                  {a.label}
                </Link>
                {open && a.subs.length > 1 && (
                  <ul className="mb-2 ml-[22px] space-y-0.5 border-l border-white/25 pl-2">
                    {a.subs.map((s) => {
                      const on = cur?.subHref === s.href;
                      return (
                        <li key={s.href}>
                          <Link
                            href={s.href}
                            className={`flex min-h-10 items-center rounded px-3 text-[15px] transition-colors ${on ? "bg-white font-semibold text-band" : "text-white/85 hover:bg-white/12"}`}
                            aria-current={on ? "page" : undefined}
                          >
                            {s.label}
                          </Link>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            );
          })}
        </nav>
        <RoleSwitch role={role} setRole={setRole} ruoli={ruoliPermessi} demo={!!accesso?.azienda.demo && ruoliPermessi.includes("responsabile")} />
        {operatore && (
          <div className="border-t border-white/20 px-4 py-3 text-[13px] text-white/80">
            <p className="font-semibold text-white">{operatore.nome}{operatore.assistenza ? " (assistenza)" : ""}</p>
            <p>{operatore.dispositivo}</p>
            <button onClick={() => { setUscendo(true); void esci(); }} disabled={uscendo} className="mt-1 font-semibold underline hover:text-white">
              Esci
            </button>
          </div>
        )}
        <div className="border-t border-white/20 px-4 py-3">
          <LostarCredit className="text-white/75 hover:text-white" />
        </div>
      </aside>

      <div className="flex min-h-dvh min-w-0 flex-col">
        {/* Testata mobile */}
        <header className="no-print sticky top-0 z-30 bg-band text-white md:hidden">
          <div className="flex items-center justify-between gap-3 px-4 py-2.5">
            <Link href="/" className="code min-w-0 text-[17px] font-bold uppercase leading-[1.05] tracking-normal" aria-label={BRAND.azienda}>
              <span className="block truncate">{BRAND.azienda.replace(/\s*4\.0$/, "")}</span>
              <span className="block text-[#F4B500]">4.0</span>
            </Link>
            <div className="flex shrink-0 items-center gap-2">
              <GlobalSearch variant="icon" />
              {!hasScanTab && (
                <Link href="/scansione" className="grid size-10 place-items-center rounded border border-white/40" aria-label="Scansiona etichetta">
                  <ScanLine className="size-5" aria-hidden />
                </Link>
              )}
              {ruoliPermessi.length > 1 && (
                <label>
                  <span className="sr-only">Ruolo</span>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value as Role)}
                    className="h-10 rounded border border-white/40 bg-band-deep px-2 text-[15px] font-semibold text-white"
                  >
                    {ruoliPermessi.map((r) => (
                      <option key={r} value={r}>
                        {RUOLO_LABEL[r]}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <button onClick={() => { setUscendo(true); void esci(); }} disabled={uscendo} className="grid h-10 place-items-center rounded border border-white/40 px-2.5 text-[14px] font-semibold md:hidden">
                Esci
              </button>
            </div>
          </div>
          {/* Sottosezioni dell'area aperta */}
          {subTabs.length > 0 && (
            <nav className="flex gap-1 overflow-x-auto px-3 pb-2" aria-label={`Sezioni di ${cur?.area?.label}`}>
              {subTabs.map((s) => {
                const on = cur?.subHref === s.href;
                return (
                  <Link
                    key={s.href}
                    href={s.href}
                    className={`flex h-9 shrink-0 items-center rounded-full px-3.5 text-[14px] font-semibold ${on ? "bg-white text-band" : "text-white/85 hover:bg-white/12"}`}
                    aria-current={on ? "page" : undefined}
                  >
                    {s.label}
                  </Link>
                );
              })}
            </nav>
          )}
        </header>
        <div className="no-print border-b border-hair bg-carton px-4 py-1.5 text-center text-[12px] font-semibold uppercase tracking-[0.14em] text-ink-3 code md:text-right">
          {accesso && !accesso.azienda.demo ? accesso.azienda.nome : DEMO_NOTICE}
          {operatore ? ` · ${operatore.nome}${operatore.assistenza ? " (assistenza)" : ""} · ${operatore.dispositivo}` : ""}
        </div>
        {avviso && (
          <p role="alert" className="no-print border-b border-warn/40 bg-warn-bg px-4 py-2 text-center text-[14px] text-ink">
            <b>{avviso.titolo}</b> {avviso.testo}
          </p>
        )}
        {storageFull && (
          <p role="status" className="no-print border-b border-warn/40 bg-warn-bg px-4 py-2 text-center text-[14px] text-ink">
            <b>Memoria di questo dispositivo piena.</b> Il lavoro si salva sul server dell&apos;azienda: tieni il telefono collegato alla rete.
          </p>
        )}
        <main className="flex-1 px-4 pb-6 pt-5 md:px-8 md:pb-12 md:pt-7">{children}</main>
        <footer className="no-print flex justify-center px-4 pb-28 md:hidden">
          <LostarCredit className="text-ink-3" />
        </footer>

        {/* Barra inferiore mobile: bersagli grandi, usabili coi guanti */}
        <nav className={`no-print fixed inset-x-0 bottom-0 z-30 grid border-t border-hair bg-label pb-[env(safe-area-inset-bottom)] md:hidden ${moreAreas.length ? "grid-cols-5" : "grid-cols-4"}`} aria-label="Aree">
          {tabs.map((t) => {
            const on = tabActive(t);
            return (
              <Link
                key={t.label}
                href={tabHref(t)}
                className={`flex min-h-16 flex-col items-center justify-center gap-1 text-[12px] font-semibold ${on ? "text-band" : "text-ink-2"}`}
                aria-current={on ? "page" : undefined}
              >
                <span className={`grid h-8 w-14 place-items-center rounded-full ${on ? "bg-band-tint" : ""}`}>
                  <t.icon className="size-[22px]" strokeWidth={2} aria-hidden />
                </span>
                {t.label}
              </Link>
            );
          })}
          {moreAreas.length > 0 && (
            <button
              onClick={() => setMore(true)}
              className={`flex min-h-16 flex-col items-center justify-center gap-1 text-[12px] font-semibold ${moreAreas.some((a) => a.id === cur?.areaId) ? "text-band" : "text-ink-2"}`}
            >
              <span className={`grid h-8 w-14 place-items-center rounded-full ${moreAreas.some((a) => a.id === cur?.areaId) ? "bg-band-tint" : ""}`}>
                <Menu className="size-[22px]" strokeWidth={2} aria-hidden />
              </span>
              Altro
            </button>
          )}
        </nav>

        {/* Foglio "Altro": le aree che non stanno nella barra */}
        <dialog
          ref={moreRef}
          onClose={() => setMore(false)}
          onClick={(e) => e.target === e.currentTarget && setMore(false)}
          aria-label="Altre aree"
          className="sheet m-0 mt-auto w-full max-w-full rounded-t-xl bg-label p-0 text-ink backdrop:bg-ink/50 md:hidden"
        >
          <div className="flex items-center justify-between border-b border-hair-soft px-4 py-3">
            <span className="code text-[15px] font-bold uppercase tracking-wide text-ink-2">Altre aree</span>
            <button onClick={() => setMore(false)} className="grid size-10 place-items-center text-ink-3" aria-label="Chiudi">
              <X className="size-5" aria-hidden />
            </button>
          </div>
          <ul className="px-2 pb-[max(1rem,env(safe-area-inset-bottom))] pt-2">
            {moreAreas.map((a) => (
              <li key={a.id} className="mb-2">
                <p className="flex items-center gap-2 px-2 py-1 font-semibold"><a.icon className="size-5 text-ink-3" aria-hidden /> {a.label}</p>
                <ul className="grid grid-cols-2 gap-1.5 px-2">
                  {a.subs.map((sub) => (
                    <li key={sub.href}>
                      <Link
                        href={sub.href}
                        onClick={() => setMore(false)}
                        className={`flex min-h-12 items-center rounded-md border px-3 text-[15px] font-semibold ${cur?.subHref === sub.href ? "border-band bg-band-tint text-band" : "border-hair text-ink"}`}
                      >
                        {sub.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </dialog>
      </div>
    </div>
  );
}

function RoleSwitch({ role, setRole, ruoli, demo }: { role: Role; setRole: (r: Role) => void; ruoli: Role[]; demo: boolean }) {
  if (ruoli.length <= 1 && !demo) return null;
  return (
    <div className="border-t border-white/20 p-4">
      {ruoli.length > 1 && (
        <label className="block">
          <span className="code mb-1 block text-[12px] font-semibold uppercase tracking-[0.14em] text-white/70">Stai usando come</span>
          <select value={role} onChange={(e) => setRole(e.target.value as Role)} className="h-10 w-full rounded border border-white/40 bg-band-deep px-2 text-[15px] font-semibold text-white">
            {ruoli.map((r) => (
              <option key={r} value={r}>
                {RUOLO_LABEL[r]}
              </option>
            ))}
          </select>
        </label>
      )}
      {demo && <button
        onClick={() => {
          if (confirm("Ripristinare i dati dimostrativi iniziali su tutti i dispositivi collegati? Le modifiche fatte nella demo andranno perse.")) void resetShared();
        }}
        className="mt-3 text-[13px] font-semibold text-white/75 underline hover:text-white"
      >
        Ripristina dati demo
      </button>}
    </div>
  );
}
