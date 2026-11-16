"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Boxes, CarFront, FileText, Leaf, PackageCheck, Search, X, type LucideIcon } from "lucide-react";
import { useStore } from "@/lib/store";
import { eerByCode, fmtKg } from "@/lib/ambiente";
import { euro } from "@/lib/logic";
import { DOC_LABEL } from "@/lib/docs";

interface Hit {
  group: string;
  icon: LucideIcon;
  id: string;
  title: string;
  sub: string;
  href: string;
}

const norm = (s: string) => s.toUpperCase().replace(/[\s\-.]/g, "");

// Una sola ricerca per tutto: targa, telaio, ID veicolo e ricambio, codice OE, vecchio codice, cliente, ordine, formulario, documento.
export function GlobalSearch({ variant }: { variant: "sidebar" | "icon" }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = e.target instanceof HTMLElement && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName);
      if ((e.key === "k" && (e.metaKey || e.ctrlKey)) || (e.key === "/" && !typing)) {
        e.preventDefault();
        setOpen(true);
      }
    };
    // Solo la variante della barra laterale ascolta la tastiera, per non aprire due finestre
    if (variant === "sidebar") window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [variant]);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);

  return (
    <>
      {variant === "sidebar" ? (
        <button
          onClick={() => setOpen(true)}
          className="flex min-h-11 w-full items-center gap-2 rounded-md border border-white/30 px-3 text-left text-[15px] text-white/80 hover:bg-white/12"
        >
          <Search className="size-[18px]" aria-hidden />
          <span className="flex-1">Cerca</span>
          <kbd className="code rounded border border-white/30 px-1.5 text-[12px] font-semibold text-white/70">⌘K</kbd>
        </button>
      ) : (
        <button onClick={() => setOpen(true)} className="grid size-10 place-items-center rounded border border-white/40" aria-label="Cerca">
          <Search className="size-5" aria-hidden />
        </button>
      )}
      <dialog
        ref={ref}
        onClose={() => setOpen(false)}
        onClick={(e) => e.target === e.currentTarget && setOpen(false)}
        aria-label="Cerca"
        className="m-0 mx-auto mt-0 h-dvh max-h-dvh w-full max-w-full bg-transparent p-0 backdrop:bg-ink/50 md:mt-[12vh] md:h-auto md:max-h-[80vh] md:max-w-[640px]"
      >
        {open && <SearchBox onClose={() => setOpen(false)} />}
      </dialog>
    </>
  );
}

function SearchBox({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const { vehicles, parts, orders, firs, docs } = useStore();
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const query = norm(q.trim());

  const hits: Hit[] = [];
  if (query.length >= 2) {
    const has = (...xs: (string | undefined)[]) => xs.some((x) => x && norm(x).includes(query));
    vehicles
      .filter((v) => has(v.id, v.plate, v.vin, `${v.make}${v.model}`, v.dossier.number, v.conferente?.nome))
      .slice(0, 5)
      .forEach((v) => hits.push({ group: "Veicoli", icon: CarFront, id: v.id, title: `${v.make} ${v.model}`, sub: `${v.plate} · ${v.vin || "telaio non acquisito"} · ${v.work}`, href: `/veicoli/${v.id}` }));
    parts
      .filter((p) => has(p.id, p.legacyCode, p.oem, p.description, p.manufacturer))
      .slice(0, 6)
      .forEach((p) =>
        hits.push({
          group: "Ricambi",
          icon: Boxes,
          id: p.id,
          title: p.description,
          sub: [p.status, p.price ? euro(p.price) : undefined, p.oem && `OE ${p.oem}`, p.legacyCode && `vecchio ${p.legacyCode}`].filter(Boolean).join(" · "),
          href: `/ricambi/${p.id}`,
        }),
      );
    orders
      .filter((o) => has(o.id, o.customer, ...o.partIds))
      .slice(0, 4)
      .forEach((o) => hits.push({ group: "Ordini", icon: PackageCheck, id: o.id, title: o.customer, sub: `${o.channel} · ${o.status} · ${euro(o.amount)}`, href: "/vendite" }));
    firs
      .filter((f) => has(f.id, f.eer, f.destinatario, eerByCode(f.eer)?.short))
      .slice(0, 4)
      .forEach((f) => hits.push({ group: "Formulari", icon: Leaf, id: f.id, title: `${eerByCode(f.eer)?.short} · ${fmtKg(f.kg)}`, sub: `${f.status} · ${f.destinatario}`, href: "/ambiente/formulari" }));
    docs
      .filter((d) => has(d.id, d.customer.name, d.customer.taxId, d.orderId))
      .slice(0, 4)
      .forEach((d) => hits.push({ group: "Documenti", icon: FileText, id: d.id, title: `${DOC_LABEL[d.type]} · ${d.customer.name}`, sub: `${euro(d.total)} · ${d.status}`, href: `/documento/${d.id}` }));
  }
  const cur = Math.min(sel, Math.max(0, hits.length - 1));
  const go = (h: Hit) => {
    onClose();
    router.push(h.href);
  };
  let last = "";

  return (
    <div className="flex h-full flex-col overflow-hidden bg-label shadow-[0_30px_80px_-24px_rgb(17_20_24/0.55)] md:h-auto md:rounded-md">
      {/* Campo di ricerca: grande, senza riquadri; la finestra stessa è il segnale che si sta cercando */}
      <div className="flex items-center gap-3 border-b-2 border-band px-4">
        <Search className="size-6 shrink-0 text-band" strokeWidth={2.2} aria-hidden />
        <input
          autoFocus
          className="h-16 focus-visible:outline-none min-w-0 flex-1 bg-transparent text-[20px] font-medium text-ink placeholder:font-normal placeholder:text-ink-3"
          placeholder="Cerca targa, telaio, codice…"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setSel(0);
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setSel(Math.min(cur + 1, hits.length - 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setSel(Math.max(cur - 1, 0));
            } else if (e.key === "Enter" && hits[cur]) go(hits[cur]);
          }}
          aria-label="Cerca in tutto il gestionale"
        />
        {q && (
          <button onClick={() => setQ("")} className="code shrink-0 rounded px-2 py-1 text-[13px] font-semibold uppercase tracking-wide text-ink-3 hover:text-ink">
            Svuota
          </button>
        )}
        <button onClick={onClose} className="grid size-10 shrink-0 place-items-center rounded-full text-ink-3 hover:bg-carton hover:text-ink" aria-label="Chiudi ricerca">
          <X className="size-5" aria-hidden />
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto md:max-h-[58vh] md:flex-none">
        {query.length < 2 ? (
          // A vuoto: cosa si può cercare, con un esempio da toccare
          <div className="p-4">
            <p className="code mb-2.5 text-[13px] font-bold uppercase tracking-wide text-ink-3">Cerca per</p>
            <ul className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
              {EXAMPLES.map((x) => (
                <li key={x.label}>
                  <button onClick={() => setQ(x.example)} className="flex w-full items-center justify-between gap-3 rounded-md border border-hair-soft bg-carton px-3 py-2.5 text-left hover:border-band hover:bg-band-tint">
                    <span className="text-[15px] font-semibold">{x.label}</span>
                    <span className="code truncate text-[15px] text-ink-2">{x.example}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : hits.length === 0 ? (
          <div className="px-4 py-8 text-center">
            <p className="font-semibold">Nessun risultato per «{q}»</p>
            <p className="mt-1 text-sm text-ink-2">Prova con una parte del codice o della targa.</p>
          </div>
        ) : (
          <ul className="py-1.5">
            {hits.map((h, i) => {
              const header = h.group !== last;
              last = h.group;
              const on = i === cur;
              return (
                <li key={h.group + h.id}>
                  {header && <p className="code px-4 pb-1 pt-3 text-[13px] font-bold uppercase tracking-wide text-ink-3">{h.group}</p>}
                  <button
                    onClick={() => go(h)}
                    onMouseEnter={() => setSel(i)}
                    className={`grid w-full grid-cols-[36px_minmax(0,1fr)_auto] items-center gap-3 border-l-4 px-3 py-2 text-left ${on ? "border-band bg-band-tint" : "border-transparent"}`}
                  >
                    <span className={`grid size-9 place-items-center rounded ${on ? "bg-band text-white" : "bg-carton text-ink-2"}`}>
                      <h.icon className="size-5" aria-hidden />
                    </span>
                    <span className="min-w-0">
                      <span className="flex items-baseline gap-2">
                        <span className="code shrink-0 text-[17px] font-bold">{h.id}</span>
                        <span className="truncate font-semibold">{h.title}</span>
                      </span>
                      <span className="block truncate text-sm text-ink-2">{h.sub}</span>
                    </span>
                    {on && <span className="code hidden text-[12px] font-semibold uppercase tracking-wide text-band md:block">Invio</span>}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
      <p className="hidden items-center gap-4 border-t border-hair-soft bg-carton px-4 py-2 text-[13px] text-ink-3 md:flex">
        <span><Kbd>↑</Kbd> <Kbd>↓</Kbd> scegli</span>
        <span><Kbd>Invio</Kbd> apri</span>
        <span><Kbd>Esc</Kbd> chiudi</span>
      </p>
    </div>
  );
}

const Kbd = ({ children }: { children: React.ReactNode }) => (
  <kbd className="code inline-grid h-6 min-w-6 place-items-center rounded border border-hair bg-label px-1.5 text-[12px] font-semibold text-ink-2 shadow-[0_1px_0_var(--hair)]">{children}</kbd>
);

const EXAMPLES = [
  { label: "Targa", example: "EK 482" },
  { label: "Ricambio", example: "R-002306" },
  { label: "Codice vecchio", example: "K000" },
  { label: "Codice OE", example: "1K0 510" },
  { label: "Veicolo o pratica", example: "V-000117" },
  { label: "Cliente o documento", example: "Officina" },
];
