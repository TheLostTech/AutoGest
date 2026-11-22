"use client";

import { useState } from "react";
import { Check, Plus } from "lucide-react";
import { BRAND } from "@/lib/config";
import { MODULI, ORDINE_MODULI, type Modulo } from "@/lib/moduli";
import { COMMISSIONE_ONLINE, LISTINO, euro, prezzo, risparmioAnnuale, totale, type Periodo } from "@/lib/listino";
import { REGISTRAZIONE } from "@/components/sito/Sito";

const PER: Record<Periodo, string> = { mese: "al mese", anno: "all'anno" };

// L'offerta: il Magazzino c'è sempre, gli altri si aggiungono. Lo scontrino accanto somma quello che scegli.
export function Offerta() {
  const [periodo, setPeriodo] = useState<Periodo>("mese");
  const [aggiunti, setAggiunti] = useState<Set<Modulo>>(() => new Set());
  const scelti = ORDINE_MODULI.filter((m) => m === "magazzino" || aggiunti.has(m));
  const risparmio = scelti.reduce((s, m) => s + risparmioAnnuale(m), 0);

  const cambia = (m: Modulo) =>
    setAggiunti((prima) => {
      const dopo = new Set(prima);
      if (dopo.has(m)) dopo.delete(m);
      else dopo.add(m);
      return dopo;
    });

  return (
    <div className="mt-10 grid items-start gap-10 lg:grid-cols-[minmax(0,1fr)_360px] lg:gap-14">
      <div className="min-w-0">
        <div role="group" aria-label="Come vuoi pagare" className="inline-flex rounded-md border border-hair bg-label p-1">
          {(["mese", "anno"] as const).map((p) => (
            <button
              key={p}
              type="button"
              aria-pressed={periodo === p}
              onClick={() => setPeriodo(p)}
              className={`min-h-11 rounded px-4 text-[16px] font-semibold transition-colors ${periodo === p ? "bg-band text-white" : "text-ink-2 hover:bg-carton"}`}
            >
              {p === "mese" ? "Mensile" : "Annuale, circa il 10% in meno"}
            </button>
          ))}
        </div>

        <ul className="mt-6 space-y-3">
          {ORDINE_MODULI.map((m) => {
            const base = m === "magazzino";
            const dentro = base || aggiunti.has(m);
            return (
              <li key={m} className={`rounded-md border p-5 md:p-6 ${base ? "border-band bg-band-tint" : dentro ? "border-band bg-label" : "border-hair bg-label"}`}>
                <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
                  <div className="min-w-0 flex-1 basis-[280px]">
                    <h3 className="text-[24px] font-bold leading-tight tracking-[-0.01em]">
                      {LISTINO[m].nome}
                      {base && <span className="ml-3 align-middle text-[15px] font-semibold text-band">sempre compreso</span>}
                    </h3>
                    <p className="mt-1.5 max-w-[56ch] text-[16px] leading-[1.55] text-ink-2">{MODULI[m].frase}</p>
                  </div>
                  <div className="sm:text-right">
                    <div className="code text-[30px] font-bold leading-none">{euro(prezzo(m, periodo))}</div>
                    <div className="mt-1 text-[14px] text-ink-3">
                      {PER[periodo]}
                      {periodo === "anno" && <span className="block">invece di {euro(LISTINO[m].mese * 12)}</span>}
                    </div>
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap items-end justify-between gap-4">
                  <ul className="grid max-w-[640px] flex-1 basis-[280px] gap-x-6 gap-y-1.5 text-[15px] leading-snug text-ink-2 md:grid-cols-2">
                    {MODULI[m].punti.map((p) => (
                      <li key={p} className="relative pl-4">
                        <span className="absolute left-0 top-[0.5em] size-1.5 rounded-full bg-band" aria-hidden />
                        {p}
                      </li>
                    ))}
                  </ul>
                  {!base && (
                    <button
                      type="button"
                      aria-pressed={dentro}
                      aria-label={`${dentro ? "Togli" : "Aggiungi"} ${LISTINO[m].nome}`}
                      onClick={() => cambia(m)}
                      className={`inline-flex min-h-11 shrink-0 items-center gap-2 rounded-md px-4 text-[16px] font-semibold transition-colors ${
                        dentro ? "bg-band text-white hover:bg-band-deep" : "border border-band text-band hover:bg-band-tint"
                      }`}
                    >
                      {dentro ? <Check className="size-[18px]" aria-hidden /> : <Plus className="size-[18px]" aria-hidden />}
                      {dentro ? "Aggiunto" : "Aggiungi"}
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="lg:sticky lg:top-6">
        <figure className="scopri-scontrino mx-auto w-full max-w-[360px]" aria-label="Il tuo abbonamento">
          <div className="code px-6 pb-1 pt-6 text-center text-[17px] font-bold uppercase tracking-[0.08em]">{BRAND.azienda}</div>
          <div className="code px-6 text-center text-[14px] text-ink-3">Il tuo abbonamento</div>
          <dl className="code mt-5 space-y-2 border-t border-dashed border-hair px-6 pt-4 text-[18px]">
            {scelti.map((m) => (
              <div key={m} className="flex justify-between gap-4">
                <dt>{LISTINO[m].nome}</dt>
                <dd className="font-bold">{euro(prezzo(m, periodo))}</dd>
              </div>
            ))}
          </dl>
          <div className="code mt-4 border-t border-dashed border-hair px-6 pt-4" aria-live="polite">
            <div className="flex items-baseline justify-between gap-4">
              <span className="text-[18px]">Totale {PER[periodo]}</span>
              <span className="text-[30px] font-bold leading-none">{euro(totale(scelti, periodo))}</span>
            </div>
            <p className="mt-1 text-right text-[14px] text-ink-3">IVA esclusa</p>
            {periodo === "anno" && <p className="mt-2 text-[15px] text-ok">Risparmi {euro(risparmio)} rispetto al mensile, in un unico pagamento.</p>}
          </div>
          <dl className="code mt-4 space-y-1 border-t border-dashed border-hair px-6 pt-4 text-[16px]">
            <div className="flex justify-between gap-4">
              <dt>Pezzi venduti online</dt>
              <dd className="font-bold">+{Math.round(COMMISSIONE_ONLINE * 100)}%</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt>Pezzi venduti al banco</dt>
              <dd className="font-bold">0</dd>
            </div>
          </dl>
          <div className="code mt-5 border-t border-dashed border-hair px-6 pb-9 pt-4 text-center text-[14px] text-ink-3">Pagamento con carta su Stripe</div>
        </figure>
        <a
          href={REGISTRAZIONE}
          className="mx-auto mt-6 flex h-14 w-full max-w-[360px] items-center justify-center rounded-md bg-band px-6 text-[17px] font-semibold text-white hover:bg-band-deep"
        >
          Inizia dal primo veicolo
        </a>
        <p className="mx-auto mt-3 max-w-[360px] text-center text-[15px] leading-[1.5] text-ink-3">Si paga dopo il primo veicolo, quando hai visto come lavora.</p>
      </div>
    </div>
  );
}
