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
        className="m-0 mx-auto mt-0 w-full max-w-full bg-transparent p-0 backdrop:bg-ink/50 md:mt-[12vh] md:max-w-[640px]"
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
    <div className="overflow-hidden border-hair bg-label shadow-[0_24px_60px_-20px_rgb(17_20_24/0.5)] md:rounded-md md:border">
      <div className="flex items-center gap-2 border-b border-hair px-3">
        <Search className="size-5 shrink-0 text-ink-3" aria-hidden />
        <input
          autoFocus
          className="h-14 min-w-0 flex-1 bg-transparent text-[18px] outline-none"
          placeholder="Targa, telaio, ID, codice OE, cliente…"
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
        <button onClick={onClose} className="grid size-10 place-items-center rounded text-ink-3 hover:text-ink" aria-label="Chiudi ricerca">
          <X className="size-5" aria-hidden />
        </button>
      </div>
      <div className="max-h-[70vh] overflow-y-auto md:max-h-[60vh]">
        {query.length < 2 ? (
          <p className="px-4 py-6 text-ink-3">Scrivi almeno due caratteri. Le targhe si trovano anche con gli spazi (es. «EK 482»).</p>
        ) : hits.length === 0 ? (
          <p className="px-4 py-6 text-ink-2">Nessun risultato per «{q}».</p>
        ) : (
          <ul className="pb-2">
            {hits.map((h, i) => {
              const header = h.group !== last;
              last = h.group;
              return (
                <li key={h.group + h.id}>
                  {header && <p className="code px-4 pb-1 pt-3 text-[13px] font-bold uppercase tracking-wide text-ink-3">{h.group}</p>}
                  <button
                    onClick={() => go(h)}
                    onMouseEnter={() => setSel(i)}
                    className={`grid w-full grid-cols-[20px_auto_minmax(0,1fr)] items-center gap-3 px-4 py-2.5 text-left ${i === cur ? "bg-band-tint" : ""}`}
                  >
                    <h.icon className="size-5 text-ink-3" aria-hidden />
                    <span className="code text-[17px] font-bold">{h.id}</span>
                    <span className="min-w-0">
                      <span className="block truncate font-semibold">{h.title}</span>
                      <span className="block truncate text-sm text-ink-2">{h.sub}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
      <p className="hidden border-t border-hair-soft px-4 py-2 text-[12px] text-ink-3 md:block">
↑ ↓ per scegliere · Invio per aprire · Esc per chiudere
      </p>
    </div>
  );
}
