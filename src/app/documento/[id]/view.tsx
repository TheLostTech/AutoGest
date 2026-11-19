"use client";

import { useParams } from "next/navigation";
import { Printer } from "lucide-react";
import { useStore } from "@/lib/store";
import { BRAND } from "@/lib/config";
import { DOC_LABEL, splitVat, VAT } from "@/lib/docs";
import { dateIt, euro } from "@/lib/logic";
import { moduloDoc } from "@/lib/moduli";
import { useModuli } from "@/lib/use-moduli";
import { ModuloBloccato } from "@/components/ModuloBloccato";

const money = (n: number) => n.toLocaleString("it-IT", { style: "currency", currency: "EUR" });

export default function Documento() {
  const { id } = useParams<{ id: string }>();
  const d = useStore((s) => s.docs.find((x) => x.id === id));
  const orders = useStore((s) => s.orders);
  const moduli = useModuli();
  if (!d) return <p className="p-8">Documento {id} non trovato.</p>;
  // Pagina di stampa fuori dall'area dell'app: i documenti del banco sono del modulo Vendite
  const modulo = moduloDoc(d, orders);
  if (!moduli.has(modulo))
    return (
      <div className="min-h-dvh bg-ground p-4 sm:p-8">
        <ModuloBloccato modulo={modulo} />
      </div>
    );
  const { net, vat } = splitVat(d.total);
  const receipt = d.type === "documento commerciale";

  return (
    <div className="min-h-dvh bg-ground p-4 print:bg-white print:p-0 sm:p-8">
      <style>{receipt ? `@page { size: 80mm auto; margin: 4mm; }` : `@page { size: A4; margin: 16mm; }`}</style>
      <div className={`no-print mx-auto mb-4 flex items-center justify-between gap-3 ${receipt ? "max-w-[80mm]" : "max-w-[210mm]"}`}>
        <p className="text-sm text-ink-2">Fac-simile dimostrativo</p>
        <button onClick={() => window.print()} className="inline-flex min-h-11 items-center gap-2 rounded-md bg-band px-4 font-semibold text-white">
          <Printer className="size-5" aria-hidden /> Stampa
        </button>
      </div>

      <article className={`mx-auto rounded-md border border-hair bg-white text-ink print:border-0 print:p-0 ${receipt ? "max-w-[80mm] p-4 text-[13px]" : "max-w-[210mm] p-8 text-[15px]"}`}>
        <header className={`flex justify-between gap-6 border-b-4 border-band pb-4 ${receipt ? "flex-col gap-2 text-center" : "items-start"}`}>
          <div>
            <p className={`code font-bold uppercase leading-none tracking-wide ${receipt ? "text-[18px]" : "text-[22px]"}`}>{BRAND.azienda}</p>
            <p className="mt-1 text-sm text-ink-2">{BRAND.sede}</p>
          </div>
          <div className={receipt ? "" : "text-right"}>
            <p className="text-sm text-ink-3">{DOC_LABEL[d.type]}</p>
            <p className="code text-[22px] font-bold leading-none">{d.id}</p>
            <p className="mt-1 text-sm text-ink-2">{dateIt(d.at, true)}</p>
          </div>
        </header>

        <section className="mt-5">
          <p className="text-sm text-ink-3">{d.type === "preventivo" ? "Preventivo per" : "Cliente"}</p>
          <p className="font-semibold">{d.customer.name}</p>
          {d.customer.taxId && <p className="code">{d.customer.taxId}</p>}
          {d.refDocId && <p className="mt-1 text-sm text-ink-2">Rettifica del documento <span className="code font-semibold">{d.refDocId}</span></p>}
        </section>

        <table className="mt-5 w-full border-collapse">
          <thead>
            <tr className="border-b border-ink text-left text-sm text-ink-3">
              <th className="py-1.5 font-semibold">Descrizione</th>
              <th className="py-1.5 text-right font-semibold">Importo</th>
            </tr>
          </thead>
          <tbody>
            {d.lines.map((l, i) => (
              <tr key={i} className="border-b border-hair-soft align-top">
                <td className="py-2 pr-4">{l.description}</td>
                <td className="code py-2 text-right font-semibold">{money(l.price)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <dl className={`mt-4 ml-auto grid grid-cols-[1fr_auto] gap-x-6 gap-y-1 ${receipt ? "" : "max-w-[300px]"}`}>
          <dt className="text-ink-2">Imponibile</dt>
          <dd className="code text-right">{money(net)}</dd>
          <dt className="text-ink-2">IVA {Math.round(VAT * 100)}%</dt>
          <dd className="code text-right">{money(vat)}</dd>
          <dt className="border-t border-ink pt-1 font-bold">Totale</dt>
          <dd className="code border-t border-ink pt-1 text-right text-[20px] font-bold">{euro(d.total)}</dd>
        </dl>

        {d.type === "preventivo" && <p className="mt-6 text-ink-2">Validità 15 giorni. Ogni ricambio è identificato dal suo codice e dal veicolo di provenienza; la disponibilità è confermata al momento dell&apos;ordine.</p>}
        {d.type === "fattura" && <p className="mt-6 text-sm text-ink-2">Fattura elettronica trasmessa al Sistema di Interscambio (simulato). Questa è una copia di cortesia.</p>}

        <p className="mt-8 border-t border-hair-soft pt-3 text-[12px] text-ink-3">Documento dimostrativo generato dal prototipo: numerazione, dati fiscali e regime IVA da definire con il commercialista.</p>
      </article>
    </div>
  );
}
