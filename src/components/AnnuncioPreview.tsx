"use client";

import { useEffect, useRef, useState } from "react";
import { useStore } from "@/lib/store";
import { PLATFORMS, typeById } from "@/lib/catalog";
import { euro } from "@/lib/logic";
import { bozzaFor } from "@/lib/annuncio-build";
import { EBAY_CATEGORY_QUERY, aspectsFor, compatVehicles } from "@/lib/annuncio-testo";
import { ONLINE_FEE_PCT, onlinePrice } from "@/lib/pricing";
import type { Part } from "@/lib/types";
import { GPSR_VUOTO, GpsrStep, gpsrDaScelta, type GpsrScelta } from "@/components/GpsrStep";
import { Button, Field, Notice, Panel, PartImage } from "@/components/ui";

const MAX_TITOLO = 80;
// Le caratteristiche che l'annuncio può avere: quelle che aspectsFor non riempie sono "mancanti"
const ASPETTI = Object.keys(aspectsFor({ tipo: "x", marca: "x", oem: "x", lato: "x" }));

/** Anteprima di un annuncio nuovo: testo, categoria, caratteristiche, GPSR e canali; "Pubblica" lo crea. */
export function AnnuncioPreview({ part, ebayDefault = false, onDone, onCancel }: { part: Part; ebayDefault?: boolean; onDone: (text: string, ok: boolean) => void; onCancel: () => void }) {
  const s = useStore();
  const [auto] = useState(() => bozzaFor(part, s.vehicles));
  const [titolo, setTitolo] = useState(auto.titolo);
  const [descrizione, setDescrizione] = useState(auto.descrizione);
  const [modificato, setModificato] = useState(false);
  const [negozio, setNegozio] = useState(true);
  const [ebay, setEbay] = useState(ebayDefault);
  const [scelta, setScelta] = useState<GpsrScelta>(GPSR_VUOTO);
  const radice = useRef<HTMLDivElement>(null);
  const titoloRef = useRef<HTMLInputElement>(null);
  // Si apre sopra la coda: portarlo in vista e mettere il cursore sul titolo
  useEffect(() => {
    radice.current?.scrollIntoView({ block: "start", behavior: "smooth" });
    titoloRef.current?.focus({ preventScroll: true });
  }, []);

  const t = typeById(part.typeId);
  const veicoli = compatVehicles([part], s.vehicles, PLATFORMS);
  const base = part.price;
  const online = onlinePrice(base);

  const daConfermare = auto.gpsr.tipo === "da confermare";
  const decisa = gpsrDaScelta(scelta);
  const gpsrOk = !daConfermare || !!decisa;
  const gpsr = !daConfermare ? auto.gpsr : (decisa ?? auto.gpsr);

  const lunghezza = titolo.trim().length;
  const motivo =
    !negozio && !ebay ? "Scegli almeno un canale"
    : !lunghezza ? "Scrivi il titolo"
    : lunghezza > MAX_TITOLO ? `Il titolo supera di ${lunghezza - MAX_TITOLO} caratteri il massimo`
    : ebay && !gpsrOk ? "Per eBay serve confermare i dati GPSR"
    : "";

  return (
    <div ref={radice} className="scroll-mt-4">
    <Panel title={`Anteprima annuncio · ${part.id}`} action={<Button size="sm" variant="quiet" onClick={onCancel}>Chiudi</Button>}>
      <div className="grid gap-5 p-4 lg:grid-cols-[200px_1fr]">
        <div className="space-y-2">
          <PartImage src={part.photos[0]} typeId={part.typeId} className="aspect-square w-full rounded border border-hair-soft bg-white" />
          <p className="text-sm text-ink-3">Foto del pezzo che parte per primo</p>
        </div>

        <div className="min-w-0 space-y-4">
          <Field label="Titolo">
            <input ref={titoloRef} className="field" value={titolo} onChange={(e) => { setTitolo(e.target.value); setModificato(true); }} aria-label="Titolo dell'annuncio" />
            <span className={`code mt-1 block text-sm font-semibold ${lunghezza > MAX_TITOLO ? "text-danger" : "text-ink-3"}`}>{lunghezza} / {MAX_TITOLO} caratteri</span>
          </Field>
          <Field label="Descrizione">
            <textarea className="field min-h-36" value={descrizione} onChange={(e) => { setDescrizione(e.target.value); setModificato(true); }} aria-label="Descrizione dell'annuncio" />
          </Field>
          <Button size="sm" variant="secondary" onClick={() => { setTitolo(auto.titolo); setDescrizione(auto.descrizione); setModificato(false); }}>Riscrivi in automatico</Button>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <h3 className="mb-1.5 text-sm font-semibold text-ink">Categoria eBay</h3>
              <p className="text-[15px]">{EBAY_CATEGORY_QUERY[part.typeId] ?? t.name}</p>
              <p className="text-sm text-ink-3">La categoria esatta la sceglie eBay alla pubblicazione.</p>
            </div>
            <div>
              <h3 className="mb-1.5 text-sm font-semibold text-ink">Caratteristiche</h3>
              <ul className="space-y-1 text-[15px]">
                {ASPETTI.map((k) => {
                  const v = auto.caratteristiche[k];
                  return (
                    <li key={k} className="flex flex-wrap gap-x-2">
                      <span className="text-ink-3">{k}</span>
                      {v ? <b>{v}</b> : <span className="rounded bg-warn-bg px-2 text-[13px] font-semibold text-warn">mancante</span>}
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>

          <div>
            <h3 className="mb-1.5 text-sm font-semibold text-ink">Veicoli compatibili</h3>
            {veicoli.length === 0 ? (
              <p className="text-[15px] text-ink-3">Nessun veicolo indicato</p>
            ) : (
              <ul className="space-y-1 text-[15px]">
                {veicoli.map((v) => (
                  <li key={`${v.marca}${v.modello}${v.anno}${v.anni}${v.motore}`}>
                    {v.marca} {v.modello}
                    <span className="text-ink-2"> {[v.motore, v.anno ?? v.anni].filter(Boolean).join(" · ")}</span>
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-1 text-sm text-ink-3">Quelli che eBay non riconosce compaiono evidenziati dopo la pubblicazione, nell&apos;elenco degli annunci.</p>
          </div>

          <p className="text-[17px]">
            Prezzo <b className="code">{euro(base)}</b> · online <b className="code">{euro(online)}</b> (+{ONLINE_FEE_PCT}%)
          </p>

          {daConfermare && <GpsrStep value={scelta} onChange={setScelta} />}

          <div className="space-y-1">
            <label className="flex min-h-11 items-center gap-3 text-[16px] font-semibold">
              <input type="checkbox" className="size-5" checked={negozio} onChange={(e) => setNegozio(e.target.checked)} />
              Negozio online
            </label>
            <label className="flex min-h-11 items-center gap-3 text-[16px] font-semibold">
              <input type="checkbox" className="size-5" checked={ebay} onChange={(e) => setEbay(e.target.checked)} />
              eBay
            </label>
            <p className="text-sm text-ink-3">Collegamento eBay: simulato finché non lo attivi in Collegamenti</p>
          </div>

          {motivo && <Notice tone="warn">{motivo}</Notice>}
          <div className="flex flex-wrap gap-2">
            <Button
              disabled={!!motivo}
              onClick={() => {
                const r = s.publishAnnuncio(part.id, { titolo: titolo.trim(), descrizione: descrizione.trim(), testoModificato: modificato, caratteristiche: auto.caratteristiche, gpsr, canali: { negozio, ebay } });
                onDone(r.ok ? `${part.id} pubblicato nell'annuncio ${r.value}` : `${part.id}: ${r.error}`, r.ok);
              }}
            >
              Pubblica
            </Button>
            <Button variant="quiet" onClick={onCancel}>Annulla</Button>
          </div>
        </div>
      </div>
    </Panel>
    </div>
  );
}
