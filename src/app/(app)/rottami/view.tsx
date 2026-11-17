"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Scale, Trash2 } from "lucide-react";
import { useStore } from "@/lib/store";
import { typeById } from "@/lib/catalog";
import { Button, Field, Notice, PageTitle, Panel } from "@/components/ui";
import type { Part, ScrapPickup } from "@/lib/types";

const day = (iso: string) => new Date(iso).toLocaleDateString("it-IT", { day: "numeric", month: "short", year: "numeric" });
const eur = (n: number) => n.toLocaleString("it-IT", { style: "currency", currency: "EUR" });
const num = (raw: string) => Number(raw.replace(",", "."));

// Area rottami: i pezzi scartati aspettano qui il ritiro. Si vendono a peso: quando passa il ritiro si pesa il carico e lo si registra.
export default function Rottami() {
  const parts = useStore((s) => s.parts);
  const scrapPickup = useStore((s) => s.scrapPickup);
  const waiting = useMemo(() => parts.filter((p) => p.status === "scartato" && !p.scrap?.pickup).sort((a, b) => (b.scrap?.at ?? "").localeCompare(a.scrap?.at ?? "")), [parts]);
  const pickups = useMemo(() => {
    const by = new Map<string, { pickup: ScrapPickup; parts: Part[] }>();
    for (const p of parts) {
      const pk = p.scrap?.pickup;
      if (!pk) continue;
      const g = by.get(pk.id) ?? { pickup: pk, parts: [] };
      g.parts.push(p);
      by.set(pk.id, g);
    }
    return [...by.values()].sort((a, b) => b.pickup.at.localeCompare(a.pickup.at));
  }, [parts]);

  const [off, setOff] = useState<Set<string>>(new Set()); // pezzi esclusi dal ritiro
  const [kg, setKg] = useState("");
  const [rate, setRate] = useState("");
  const [buyer, setBuyer] = useState("");
  const [msg, setMsg] = useState<{ tone: "ok" | "danger"; text: string } | null>(null);
  const chosen = waiting.filter((p) => !off.has(p.id));
  const total = num(kg) > 0 && num(rate) >= 0 ? Math.round(num(kg) * num(rate) * 100) / 100 : 0;
  const canSave = chosen.length > 0 && num(kg) > 0 && Number.isFinite(num(rate)) && rate.trim() !== "";

  return (
    <div className="mx-auto max-w-3xl">
      <PageTitle title="Area rottami" sub="Pezzi scartati in attesa di ritiro. Si vendono a peso: quando passa il ritiro, pesa il carico e registralo qui." />
      {msg && <div className="mb-5"><Notice tone={msg.tone}>{msg.text}</Notice></div>}

      <Panel title={`In attesa di ritiro · ${waiting.length}`}>
        {waiting.length === 0 ? (
          <p className="px-4 py-8 text-center text-ink-2">
            Nessun pezzo nei rottami. Si scarta da <Link href="/scansione" className="font-semibold text-band underline">Scansiona</Link> (pezzo → Scarta) o dalla scheda del ricambio.
          </p>
        ) : (
          <ul className="divide-y divide-hair-soft">
            {waiting.map((p) => (
              <li key={p.id} className="flex items-start gap-3 px-4 py-3">
                <input type="checkbox" className="mt-1.5 size-5 shrink-0 accent-[var(--band)]" checked={!off.has(p.id)} onChange={(e) => setOff((s) => { const n = new Set(s); if (e.target.checked) n.delete(p.id); else n.add(p.id); return n; })} aria-label={`Includi ${p.id} nel ritiro`} />
                <div className="min-w-0 flex-1">
                  <Link href={`/ricambi/${p.id}`} className="code text-[17px] font-bold text-band">{p.id}</Link>
                  <span className="ml-2 text-ink">{p.description || typeById(p.typeId).name}</span>
                  <p className="text-sm text-ink-2">
                    {p.scrap?.reason ?? "Scartato"}
                    {p.scrap?.from && <> · tolto da <span className="code">{p.scrap.from}</span></>}
                    {p.scrap?.at && <> · {day(p.scrap.at)}</>}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      {waiting.length > 0 && (
        <Panel title="Registra il ritiro a peso" className="mt-6">
          <div className="grid gap-3 p-4 sm:grid-cols-3">
            <Field label="Peso del carico (kg)" hint="Dalla pesa o dalla bolla">
              <input className="field code text-[18px] font-bold" inputMode="decimal" value={kg} onChange={(e) => setKg(e.target.value.replace(/[^0-9.,]/g, ""))} />
            </Field>
            <Field label="Prezzo al kg (€)">
              <input className="field code text-[18px] font-bold" inputMode="decimal" value={rate} onChange={(e) => setRate(e.target.value.replace(/[^0-9.,]/g, ""))} placeholder="0,25" />
            </Field>
            <Field label="Chi ritira">
              <input className="field" value={buyer} onChange={(e) => setBuyer(e.target.value)} placeholder="Ditta del rottame" />
            </Field>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-hair-soft p-4">
            <p className="text-ink-2">
              <b className="text-ink">{chosen.length}</b> {chosen.length === 1 ? "pezzo" : "pezzi"}
              {total > 0 && <> · incasso <b className="code text-[20px] text-ink">{eur(total)}</b></>}
            </p>
            <Button
              disabled={!canSave}
              onClick={() => {
                const r = scrapPickup(chosen.map((p) => p.id), num(kg), num(rate), buyer);
                if (!r.ok) return setMsg({ tone: "danger", text: r.error });
                setMsg({ tone: "ok", text: `Ritiro ${r.value} registrato: ${chosen.length} ${chosen.length === 1 ? "pezzo" : "pezzi"}, ${num(kg).toLocaleString("it-IT")} kg, ${eur(total)}.` });
                setKg("");
                setRate("");
                setBuyer("");
                setOff(new Set());
              }}
            >
              <Scale className="size-5" aria-hidden /> Registra ritiro
            </Button>
          </div>
        </Panel>
      )}

      <Panel title="Ritiri fatti" className="mt-6">
        {pickups.length === 0 ? (
          <p className="px-4 py-6 text-center text-ink-2">Ancora nessun ritiro registrato.</p>
        ) : (
          <ul className="divide-y divide-hair-soft">
            {pickups.map(({ pickup, parts: ps }) => (
              <li key={pickup.id} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-4 py-3">
                <span>
                  <b className="code">{pickup.id}</b> · {day(pickup.at)} · {pickup.buyer}
                </span>
                <span className="text-ink-2">
                  {ps.length} {ps.length === 1 ? "pezzo" : "pezzi"} · {pickup.kg.toLocaleString("it-IT")} kg × {eur(pickup.eurPerKg)} = <b className="text-ink">{eur(Math.round(pickup.kg * pickup.eurPerKg * 100) / 100)}</b>
                </span>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <p className="mt-4 flex items-start gap-2 text-[13px] text-ink-3">
        <Trash2 className="mt-0.5 size-4 shrink-0" aria-hidden />
        Da definire con il cliente: codice EER dei ricambi scartati per il registro rifiuti, formulario per il ritiro, documento di vendita del rottame.
      </p>
    </div>
  );
}
