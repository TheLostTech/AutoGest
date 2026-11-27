"use client";

import Link from "next/link";
import { useState } from "react";
import { CircleCheck, Send } from "lucide-react";
import { CAUSALE_LABEL, isDraft, mudVeicoliRicevuti, periodsOf, type MudVeicoli } from "@/lib/periodo";
import { useStore } from "@/lib/store";
import { EER, eerByCode, fmtKg, stockByEer } from "@/lib/ambiente";
import { dateIt } from "@/lib/logic";
import { ButtonLink, PageTitle, Panel } from "@/components/ui";

export default function RegistroRifiuti() {
  const { wasteMoves, firs, vehicles } = useStore();
  const [eer, setEer] = useState("tutti");
  const [all, setAll] = useState(false);
  const [allStock, setAllStock] = useState(false);
  const toSend = periodsOf(wasteMoves, firs).filter((p) => p.status === "da trasmettere");
  const stock = stockByEer(wasteMoves)
    .filter((s) => s.kg > 0)
    .sort((a, b) => b.pct - a.pct);
  const list = [...wasteMoves].reverse().filter((m) => eer === "tutti" || m.eer === eer);
  const shown = all ? list : list.slice(0, 40);
  // MUD: si dichiara entro l'anno successivo; si mostrano l'anno scorso e quello in corso
  const annoDi = (id: string) => vehicles.find((v) => v.id === id)?.year;
  const adesso = new Date().getFullYear();
  const mud = [adesso - 1, adesso].map((a) => mudVeicoliRicevuti(wasteMoves, annoDi, a)).filter((x) => x.veicoli > 0);

  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle
        title="Registro rifiuti"
        sub="Carico e scarico si scrivono da soli: ingresso dei veicoli, bonifiche e formulari generano i movimenti. Qui si controlla e si trasmette."
        actions={
          <ButtonLink href={toSend.length ? `/ambiente/periodo?mese=${toSend[0].key}` : "/ambiente/periodo"}>
            <Send className="size-5" aria-hidden /> {toSend.length ? `Periodo di ${toSend[0].label} da trasmettere` : "Periodi RENTRI"}
          </ButtonLink>
        }
      />

      <section aria-labelledby="giacenze" className="mb-6">
        <h2 id="giacenze" className="code mb-2 text-[15px] font-bold uppercase tracking-wide text-ink-2">Giacenze e limiti dell&apos;autorizzazione</h2>
        <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {(allStock ? stock : stock.slice(0, 6)).map((s) => {
            const tone = s.pct >= 0.95 ? "bg-danger" : s.pct >= 0.8 ? "bg-[#d99a00]" : "bg-band";
            const text = s.pct >= 0.95 ? "text-danger" : s.pct >= 0.8 ? "text-warn" : "text-ink-2";
            return (
              <li key={s.code}>
                <Link href={s.code === "16 01 04*" ? "/veicoli" : `/ambiente/formulari?eer=${encodeURIComponent(s.code)}`} className="label-sheet block p-4 hover:border-ink-3">
                  <span className="flex items-baseline justify-between gap-3">
                    <span className="min-w-0 truncate font-semibold">{s.short}</span>
                    <span className="code shrink-0 text-[13px] text-ink-3">{s.code}</span>
                  </span>
                  <span className="mt-2 flex items-baseline justify-between gap-3">
                    <span className="code text-[24px] font-bold leading-none">{fmtKg(s.kg)}</span>
                    <span className={`text-sm font-semibold ${text}`}>{Math.round(s.pct * 100)}% di {fmtKg(s.limitKg)}</span>
                  </span>
                  <span className="mt-2 block h-2 overflow-hidden rounded-full bg-hair-soft" role="img" aria-label={`${Math.round(s.pct * 100)} per cento del limite`}>
                    <span className={`block h-full rounded-full ${tone}`} style={{ width: `${Math.min(100, s.pct * 100)}%` }} />
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
        {stock.length > 6 && (
          <button className="mt-2 text-[15px] font-semibold text-band" onClick={() => setAllStock(!allStock)}>
            {allStock ? "Mostra solo i più vicini al limite" : `Mostra gli altri ${stock.length - 6} codici in giacenza`}
          </button>
        )}
      </section>

      {mud.length > 0 && (
        <section aria-labelledby="mud" className="mb-6">
          <h2 id="mud" className="code mb-2 text-[15px] font-bold uppercase tracking-wide text-ink-2">MUD · veicoli fuori uso ricevuti (16 01 04)</h2>
          <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {mud.map((x) => <MudAnno key={x.anno} x={x} inCorso={x.anno === adesso} />)}
          </ul>
          <p className="mt-2 text-[13px] text-ink-3">La Scheda AUT chiede il peso dei veicoli ricevuti diviso per anno di immatricolazione, prima o dal 1° gennaio 1980. Sono contati i carichi registrati, con rettifiche e annullamenti.</p>
        </section>
      )}

      <Panel
        title={`Movimenti · ${list.length}`}
        action={
          <select className="h-10 max-w-[48vw] rounded border border-hair bg-label px-2 text-sm font-semibold" value={eer} onChange={(e) => setEer(e.target.value)} aria-label="Filtra per codice rifiuto">
            <option value="tutti">Tutti i codici</option>
            {EER.filter((e) => wasteMoves.some((m) => m.eer === e.code)).map((e) => <option key={e.code} value={e.code}>{e.code} · {e.short}</option>)}
          </select>
        }
      >
        <ul className="divide-y divide-hair-soft">
          {shown.map((m) => {
            const e = eerByCode(m.eer);
            const isVeh = m.origin.startsWith("V-");
            return (
              <li key={`${m.id}|${m.at}`} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 px-4 py-3 md:grid-cols-[96px_118px_minmax(0,1fr)_110px_120px]">
                <span className="code text-[15px] font-semibold text-ink-2 md:order-none">{isDraft(m) ? <span className="text-warn">bozza</span> : `n. ${m.numero}`}</span>
                <span className="text-sm text-ink-3 md:text-[15px]">{dateIt(m.at, true)}</span>
                <span className="col-span-2 min-w-0 md:col-span-1">
                  <span className={`code mr-2 inline-flex h-6 items-center rounded px-2 text-[12px] font-bold uppercase tracking-wide ${m.kind === "carico" ? "bg-band-tint text-band" : "bg-ink text-white"}`}>{m.kind}</span>
                  <span className="code font-semibold">{m.eer}</span> <span className="text-ink-2">{e?.short}</span>
                  {m.causale && <span className="ml-2 text-sm text-ink-3">{CAUSALE_LABEL[m.causale]}</span>}
                  <span className="block truncate text-sm text-ink-3">
                    {m.note} ·{" "}
                    <Link href={isVeh ? `/veicoli/${m.origin}` : "/ambiente/formulari"} className="code font-semibold text-band underline">{m.origin}</Link>
                    {m.motivo && <> · {m.motivo}</>}
                  </span>
                </span>
                <span className={`code text-[18px] font-bold md:text-right ${m.kind === "carico" ? "" : "text-ink-2"}`}>{m.causale === "ANN" ? "annulla" : `${m.causale === "RETT" ? "= " : m.kind === "carico" ? "+" : "−"}${fmtKg(m.kg)}`}</span>
                <span className="text-right text-sm">
                  {m.rentri === "trasmesso" ? (
                    <span className="inline-flex items-center gap-1 font-semibold text-ok"><CircleCheck className="size-4" aria-hidden /> RENTRI</span>
                  ) : (
                    <span className="font-semibold text-warn">da trasmettere</span>
                  )}
                </span>
              </li>
            );
          })}
        </ul>
        {!all && list.length > shown.length && (
          <div className="border-t border-hair-soft p-3 text-center">
            <button className="font-semibold text-band" onClick={() => setAll(true)}>Mostra tutti i {list.length} movimenti</button>
          </div>
        )}
      </Panel>
      <p className="mt-3 text-[13px] text-ink-3">Codici rifiuto, limiti e trasmissione sono dimostrativi: il collegamento reale al RENTRI richiede l&apos;accreditamento e va validato con la consulente ambientale.</p>
    </div>
  );
}

function MudAnno({ x, inCorso }: { x: MudVeicoli; inCorso: boolean }) {
  return (
    <li className="label-sheet p-4">
      <span className="flex items-baseline justify-between gap-3">
        <span className="font-semibold">Anno {x.anno}{inCorso ? " (in corso)" : ""}</span>
        <span className="text-sm text-ink-3">{x.veicoli} {x.veicoli === 1 ? "veicolo" : "veicoli"}</span>
      </span>
      <span className="code mt-2 block text-[24px] font-bold leading-none">{fmtKg(x.totaleKg)}</span>
      <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
        <div>
          <dt className="text-ink-3">Immatricolati prima del 1980</dt>
          <dd className="code font-semibold">{fmtKg(x.prima1980Kg)}</dd>
        </div>
        <div>
          <dt className="text-ink-3">Dal 1980</dt>
          <dd className="code font-semibold">{fmtKg(x.dal1980Kg)}</dd>
        </div>
      </dl>
      {x.senzaAnno > 0 && <p className="mt-2 text-sm font-semibold text-warn">{x.senzaAnno} {x.senzaAnno === 1 ? "veicolo" : "veicoli"} senza anno di immatricolazione: da completare</p>}
    </li>
  );
}
