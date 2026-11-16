"use client";

import { useParams } from "next/navigation";
import { Printer } from "lucide-react";
import { useStore } from "@/lib/store";
import { BRAND } from "@/lib/config";
import { CONFERENTI, docsFor } from "@/lib/pratica";
import { dateIt } from "@/lib/logic";
import { fmtKg } from "@/lib/ambiente";

// Fac-simile del certificato di rottamazione: il modello ufficiale va verificato.
export default function Certificato() {
  const { id } = useParams<{ id: string }>();
  const v = useStore((s) => s.vehicles.find((x) => x.id === id));
  if (!v) return <p className="p-8">Veicolo {id} non trovato.</p>;
  if (!v.presaInCarico) return <p className="p-8">Il veicolo {id} non è ancora stato preso in carico: il certificato non è disponibile.</p>;

  const row = (k: string, val: React.ReactNode) => (
    <>
      <dt className="text-ink-3">{k}</dt>
      <dd className="font-semibold">{val}</dd>
    </>
  );

  return (
    <div className="min-h-dvh bg-ground p-4 print:bg-white print:p-0 sm:p-8">
      <style>{`@page { size: A4; margin: 16mm; }`}</style>
      <div className="no-print mx-auto mb-4 flex max-w-[210mm] items-center justify-between gap-3">
        <p className="text-sm text-ink-2">Fac-simile dimostrativo: modello e dati obbligatori da verificare.</p>
        <button onClick={() => window.print()} className="inline-flex min-h-11 items-center gap-2 rounded-md bg-band px-4 font-semibold text-white">
          <Printer className="size-5" aria-hidden /> Stampa
        </button>
      </div>

      <article className="mx-auto max-w-[210mm] rounded-md border border-hair bg-white p-8 text-[15px] text-ink print:border-0 print:p-0">
        <header className="flex items-start justify-between gap-6 border-b-4 border-band pb-4">
          <div>
            <p className="code text-[22px] font-bold uppercase leading-none tracking-wide">{BRAND.azienda}</p>
            <p className="mt-1 text-sm text-ink-2">{BRAND.sede} · Centro di raccolta veicoli fuori uso</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-ink-3">Numero</p>
            <p className="code text-[24px] font-bold leading-none">{v.dossier.number}</p>
          </div>
        </header>

        <h1 className="mt-6 text-[26px] font-bold">Certificato di rottamazione</h1>
        <p className="mt-1 text-ink-2">Presa in carico del {dateIt(v.presaInCarico.at, true)} · ID interno {v.id}</p>

        <section className="mt-6">
          <h2 className="code mb-2 text-[13px] font-bold uppercase tracking-[0.14em] text-ink-2">Veicolo</h2>
          <dl className="grid grid-cols-[160px_1fr] gap-x-6 gap-y-1.5">
            {row("Targa", <span className="code text-[18px]">{v.plate}</span>)}
            {row("Telaio (VIN)", <span className="code text-[18px]">{v.vin || "non acquisito"}</span>)}
            {row("Marca e modello", `${v.make} ${v.model} ${v.version}`)}
            {row("Anno · alimentazione", `${v.year || "—"} · ${v.fuel}`)}
            {row("Peso in ingresso", v.weightKg ? fmtKg(v.weightKg) : "—")}
          </dl>
        </section>

        <section className="mt-6">
          <h2 className="code mb-2 text-[13px] font-bold uppercase tracking-[0.14em] text-ink-2">Chi conferisce</h2>
          <dl className="grid grid-cols-[160px_1fr] gap-x-6 gap-y-1.5">
            {row("Tipo", CONFERENTI.find((c) => c.value === v.conferente?.tipo)?.label ?? "—")}
            {row("Nome", v.conferente?.nome ?? "—")}
            {row("Intestatario da visura", v.visura?.intestatario ?? "—")}
            {row("Fermo amministrativo", v.visura ? (v.visura.fermo ? "presente" : "assente") : "—")}
          </dl>
        </section>

        <section className="mt-6">
          <h2 className="code mb-2 text-[13px] font-bold uppercase tracking-[0.14em] text-ink-2">Documenti e targhe ritirati</h2>
          <ul className="grid grid-cols-2 gap-x-6 gap-y-1">
            {docsFor(v).map((d) => (
              <li key={d.key} className="flex items-center gap-2">
                <span className="code w-5 font-bold">{v.documenti?.includes(d.key) ? "✓" : "—"}</span>
                {d.label}
              </li>
            ))}
          </ul>
        </section>

        <p className="mt-8 max-w-[70ch] text-ink-2">
          Il centro di raccolta dichiara di aver preso in carico il veicolo sopra descritto per la demolizione, e si impegna a curarne la radiazione dal Pubblico Registro Automobilistico.
        </p>

        <div className="mt-14 grid grid-cols-2 gap-10">
          <div className="border-t border-ink pt-2 text-sm text-ink-2">Firma di chi conferisce</div>
          <div className="border-t border-ink pt-2 text-sm text-ink-2">Timbro e firma del centro di raccolta</div>
        </div>

        <p className="mt-10 border-t border-hair-soft pt-3 text-[12px] text-ink-3">Fac-simile dimostrativo generato dal prototipo: il modello ufficiale e i dati obbligatori vanno verificati sulla normativa vigente.</p>
      </article>
    </div>
  );
}
