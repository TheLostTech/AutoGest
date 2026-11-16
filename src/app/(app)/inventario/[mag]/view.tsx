"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, ClipboardCheck, Plus } from "lucide-react";
import { useStore } from "@/lib/store";
import { originLabel } from "@/lib/warehouse";
import { ButtonLink, Empty, StatusChip } from "@/components/ui";
import type { Part } from "@/lib/types";

// Il magazzino come elenco di ricambi, raggruppati per ubicazione; si aggiunge un pezzo alla volta.
export default function InventarioMagazzino() {
  const { mag } = useParams<{ mag: string }>();
  const id = decodeURIComponent(mag);
  const { warehouses, parts } = useStore();
  const w = warehouses.find((x) => x.id === id);
  const [q, setQ] = useState("");
  if (!w) return <Empty title={`Magazzino ${id} non trovato`} />;

  const norm = (x?: string) => (x ?? "").toUpperCase().replace(/[\s\-.]/g, "");
  const query = norm(q);
  const inside = parts
    .filter((p) => p.location?.mag === w.id && p.status !== "venduto" && p.status !== "scartato")
    .filter((p) => !query || [p.id, p.description, p.legacyCode, p.oem, p.pastDossier?.number, p.pastDossier?.model].some((x) => norm(x).includes(query)));

  // Gruppi per ripiano, in ordine di corsia, scaffale, ripiano
  const groups = new Map<string, Part[]>();
  for (const p of [...inside].sort((a, b) => key(a).localeCompare(key(b), "it", { numeric: true }))) {
    const k = `${p.location!.corsia}|${p.location!.scaffale}|${p.location!.ripiano}`;
    groups.set(k, [...(groups.get(k) ?? []), p]);
  }
  const addHref = `/inventario/${encodeURIComponent(w.id)}/nuovo`;

  return (
    <div className="mx-auto max-w-4xl">
      <Link href="/inventario" className="mb-3 inline-flex items-center gap-1.5 text-[15px] font-semibold text-band">
        <ArrowLeft className="size-4" aria-hidden /> Inventario
      </Link>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="code text-[44px] font-bold leading-none">Mag. {w.id}</h1>
          <p className="mt-1 text-ink-2">
            {w.name} · <b className="text-ink">{parts.filter((p) => p.location?.mag === w.id && p.status !== "venduto" && p.status !== "scartato").length}</b> ricambi
          </p>
        </div>
        <ButtonLink href={addHref} size="lg">
          <Plus className="size-6" aria-hidden /> Aggiungi ricambio
        </ButtonLink>
      </div>

      <input className="field mb-4" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cerca per ID, descrizione, codice vecchio, pratica, modello…" aria-label="Cerca nel magazzino" />

      {groups.size === 0 ? (
        <div className="label-sheet px-5 py-10 text-center">
          <p className="font-semibold">{q ? "Nessun ricambio trovato" : "Magazzino ancora vuoto"}</p>
          {!q && <p className="mt-1 text-ink-2">Inserisci i ricambi che ci sono già, uno alla volta, con la loro ubicazione.</p>}
          {!q && <ButtonLink href={addHref} className="mt-4"><Plus className="size-5" aria-hidden /> Aggiungi il primo ricambio</ButtonLink>}
        </div>
      ) : (
        <div className="space-y-4">
          {[...groups.entries()].map(([k, list]) => {
            const [c, s, r] = k.split("|");
            return (
              <section key={k} className="rounded-md border border-hair bg-label">
                <header className="flex items-center justify-between gap-3 border-b border-hair-soft px-4 py-2.5">
                  <h2 className="code text-[17px] font-bold">
                    {w.id}/{c} · Scaffale {s} · Ripiano {r}
                  </h2>
                  <Link
                    href={`/inventario/conta?mag=${encodeURIComponent(w.id)}&c=${c}&s=${s}&r=${r}`}
                    className="inline-flex shrink-0 items-center gap-1 text-sm font-semibold text-band"
                    title="Controlla che i pezzi registrati qui ci siano davvero"
                  >
                    <ClipboardCheck className="size-4" aria-hidden /> Verifica
                  </Link>
                </header>
                <ul className="divide-y divide-hair-soft">
                  {list.map((p) => (
                    <li key={p.id}>
                      <Link href={`/ricambi/${p.id}`} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-4 py-2.5 hover:bg-carton">
                        <span className="min-w-0">
                          <span className="flex items-baseline gap-2">
                            <span className="code text-[17px] font-bold">{p.id}</span>
                            {p.legacyCode && <span className="code text-sm text-ink-2">{p.legacyCode}</span>}
                            {p.location?.contenitore && <span className="text-sm text-ink-3">cont. {p.location.contenitore}</span>}
                          </span>
                          <span className="block truncate">{p.description}</span>
                          <span className={`block truncate text-sm ${p.missingSince ? "font-semibold text-danger" : "text-ink-3"}`}>
                            {p.missingSince ? "Non trovato all'ultima verifica" : `da ${originLabel(p)}`}
                          </span>
                        </span>
                        <StatusChip status={p.status} />
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}

const key = (p: Part) => `${p.location!.corsia} ${p.location!.scaffale} ${p.location!.ripiano} ${p.location!.contenitore ?? ""}`;
