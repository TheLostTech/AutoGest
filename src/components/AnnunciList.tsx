"use client";

import Link from "next/link";
import { useState } from "react";
import { useStore } from "@/lib/store";
import { euro } from "@/lib/logic";
import { gpsrBlocksEbay, isWithdrawn, negozioStato, nextToShip, quantityOf } from "@/lib/annunci";
import { typeById } from "@/lib/catalog";
import type { Annuncio } from "@/lib/types";
import { GPSR_VUOTO, GpsrStep, gpsrDaScelta, type GpsrScelta } from "@/components/GpsrStep";
import { Button, Empty, Notice, Panel } from "@/components/ui";

const TONO: Record<string, string> = {
  online: "bg-ok-bg text-ok",
  esaurito: "bg-warn-bg text-warn",
  ritirato: "bg-hair-soft text-ink-2",
  errore: "bg-danger-bg text-danger",
};
const chip = (tono: string) => `code inline-flex h-7 items-center rounded px-2.5 text-[13px] font-semibold uppercase tracking-wide ${TONO[tono] ?? "bg-band-tint text-band-deep"}`;

function AnnuncioRiga({ a }: { a: Annuncio }) {
  const s = useStore();
  const [edit, setEdit] = useState(false);
  const [titolo, setTitolo] = useState(a.titolo);
  const [descrizione, setDescrizione] = useState(a.descrizione);
  const [err, setErr] = useState("");
  const [gpsrAperto, setGpsrAperto] = useState(false);
  const [scelta, setScelta] = useState<GpsrScelta>(GPSR_VUOTO);
  // Errore del negozio (es. GPSR da confermare, già ritirato) in chiaro sotto l'annuncio
  const esito = (r: { ok: boolean } & { error?: string }) => setErr(r.ok ? "" : (r.error ?? "Operazione non riuscita"));
  const decisa = gpsrDaScelta(scelta);
  const qty = quantityOf(a, s.parts);
  const neg = negozioStato(a, qty);
  const eb = a.ebay;
  const negAttivo = !!a.negozio && a.negozio.stato !== "ritirato";
  const ebAttivo = !!eb && eb.stato !== "ritirato";
  const negRipubblica = !a.negozio || a.negozio.stato === "ritirato";
  const ebRipubblica = !eb || !["online", "esaurito", "in pubblicazione"].includes(eb.stato);
  const next = nextToShip(a, s.parts)[0];
  const lungo = titolo.trim().length;

  return (
    <li className="space-y-2 px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="code text-[20px] font-bold leading-none">{a.id}</span>
        <span className="code font-bold">{qty} {qty === 1 ? "disponibile" : "disponibili"}</span>
        <span className="text-ink-2">{typeById(a.typeId).name} · {euro(a.price)}</span>
        {next && <Link href={`/ricambi/${next.id}`} className="code text-sm text-band underline">parte {next.id}</Link>}
      </div>
      <div className="font-medium">{a.titolo}</div>
      <div className="flex flex-wrap items-center gap-2">
        {neg && <span className={chip(neg)}>negozio {neg}</span>}
        {eb && (
          <>
            <span className={chip(eb.stato === "errore" ? "errore" : eb.stato)}>eBay {eb.stato}</span>
            {eb.daRiallineare && <span className="rounded bg-warn-bg px-2 py-0.5 text-[13px] font-semibold text-warn">da riallineare</span>}
            {eb.url && <a href={eb.url} target="_blank" rel="noreferrer" className="text-sm font-semibold text-band underline">Vedi su eBay</a>}
          </>
        )}
        {isWithdrawn(a) && <span className="text-sm text-ink-3">ritirato da tutti i canali</span>}
      </div>
      {eb?.errore && <p className="text-sm font-semibold text-danger">{eb.errore}</p>}
      {eb?.avvisi && eb.avvisi.length > 0 && (
        <ul className="space-y-1 text-sm text-warn">
          {eb.avvisi.map((v) => <li key={v} className="rounded bg-warn-bg px-2 py-0.5">{v}</li>)}
        </ul>
      )}

      {err && <Notice tone="danger">{err}</Notice>}
      {gpsrAperto && (
        <div className="space-y-2">
          <GpsrStep value={scelta} onChange={setScelta} />
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              disabled={!decisa}
              onClick={() => {
                if (!decisa) return;
                s.setAnnuncioGpsr(a.id, decisa);
                const r = s.republishAnnuncio(a.id, { negozio: false, ebay: true });
                esito(r);
                if (r.ok) setGpsrAperto(false);
              }}
            >
              Conferma e pubblica su eBay
            </Button>
            <Button size="sm" variant="quiet" onClick={() => setGpsrAperto(false)}>Annulla</Button>
          </div>
        </div>
      )}

      {edit && (
        <div className="space-y-2 rounded-md border border-hair-soft bg-carton p-3">
          <input className="field" value={titolo} onChange={(e) => setTitolo(e.target.value)} aria-label={`Titolo ${a.id}`} />
          <span className={`code block text-sm font-semibold ${lungo > 80 ? "text-danger" : "text-ink-3"}`}>{lungo} / 80 caratteri</span>
          <textarea className="field min-h-28" value={descrizione} onChange={(e) => setDescrizione(e.target.value)} aria-label={`Descrizione ${a.id}`} />
          <div className="flex flex-wrap gap-2">
            <Button size="sm" disabled={!lungo || lungo > 80} onClick={() => { s.editAnnuncioText(a.id, titolo, descrizione); setEdit(false); }}>Salva testo</Button>
            <Button size="sm" variant="secondary" onClick={() => { s.regenerateText(a.id); setEdit(false); }}>Riscrivi in automatico</Button>
            <Button size="sm" variant="quiet" onClick={() => setEdit(false)}>Annulla</Button>
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {!edit && <Button size="sm" variant="secondary" onClick={() => { setTitolo(a.titolo); setDescrizione(a.descrizione); setEdit(true); }}>Modifica testo</Button>}
        {negAttivo && ebAttivo && <Button size="sm" variant="danger" onClick={() => esito(s.withdrawAnnuncio(a.id, "tutti"))}>Ritira da tutti</Button>}
        {negAttivo && <Button size="sm" variant="danger" onClick={() => esito(s.withdrawAnnuncio(a.id, "negozio"))}>Ritira dal negozio</Button>}
        {ebAttivo && <Button size="sm" variant="danger" onClick={() => esito(s.withdrawAnnuncio(a.id, "ebay"))}>Ritira da eBay</Button>}
        {negRipubblica && <Button size="sm" variant="secondary" onClick={() => esito(s.republishAnnuncio(a.id, { negozio: true, ebay: false }))}>Ripubblica sul negozio</Button>}
        {ebRipubblica && <Button size="sm" variant="secondary" onClick={() => (gpsrBlocksEbay(a.gpsr) ? (setErr(""), setGpsrAperto(true)) : esito(s.republishAnnuncio(a.id, { negozio: false, ebay: true })))}>{eb ? "Ripubblica su eBay" : "Pubblica su eBay"}</Button>}
      </div>
    </li>
  );
}

export function AnnunciList() {
  const annunci = useStore((s) => s.annunci);
  return (
    <Panel title={`Annunci · ${annunci.length}`} className="mt-6">
      {annunci.length === 0 ? (
        <Empty title="Nessun annuncio">Pubblica un pezzo dalla coda per crearne uno.</Empty>
      ) : (
        <ul className="divide-y divide-hair-soft">
          {annunci.map((a) => <AnnuncioRiga key={a.id} a={a} />)}
        </ul>
      )}
    </Panel>
  );
}
