"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useStore } from "@/lib/store";
import { statoPonte } from "@/lib/ebay-sync";
import { publishChecks, euro } from "@/lib/logic";
import { groupKey, listingOf, placementFor, type Placement } from "@/lib/annunci";
import { bozzaFor } from "@/lib/annuncio-build";
import { typeById } from "@/lib/catalog";
import { isShippable } from "@/lib/spedizione";
import type { Part } from "@/lib/types";
import { AnnuncioPreview } from "@/components/AnnuncioPreview";
import { AnnunciList } from "@/components/AnnunciList";
import { Button, Empty, Notice, PageTitle, Panel, PartImage, StatusChip } from "@/components/ui";

export default function Pubblicazione() {
  const s = useStore();
  const [msg, setMsg] = useState<{ tone: "ok" | "danger"; text: string } | null>(null);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [ebayCollegato, setEbayCollegato] = useState(false);
  useEffect(() => {
    let vivo = true;
    void statoPonte().then((p) => vivo && setEbayCollegato(!!p?.collegato));
    return () => {
      vivo = false;
    };
  }, []);
  const vById = new Map(s.vehicles.map((v) => [v.id, v]));
  const keyOf = (p: Part) => groupKey(p, isShippable(p, typeById(p.typeId).shippable));
  const queue = s.parts
    .filter((p) => (p.status === "bozza" || p.status === "disponibile") && listingOf(p, s.annunci) !== "pubblicato")
    .map((p) => {
      const placement: Placement = p.annuncioId ? { kind: "annuncio ritirato", annuncioId: p.annuncioId } : placementFor(p, keyOf(p), s.annunci);
      return { p, placement, missing: publishChecks(p, vById.get(p.vehicleId)).filter((c) => c.blocking && !c.ok) };
    })
    .sort((a, b) => a.missing.length - b.missing.length);
  // In blocco si pubblicano solo i pezzi mai ritirati e senza prezzo diverso da un annuncio uguale
  const ready = queue.filter((x) => x.missing.length === 0 && x.p.status === "disponibile" && (x.placement.kind === "nuovo" || x.placement.kind === "unisci"));
  const preview = previewId ? s.parts.find((x) => x.id === previewId && !x.annuncioId) : undefined;

  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle
        title="Approvazione e pubblicazione"
        sub="Un ricambio va online solo con foto, prezzo, dati minimi validati e provenienza certa. Le schede incomplete restano in bozza."
        actions={
          ready.length > 0 && (
            <Button
              onClick={() => {
                // Un pezzo alla volta dallo stato aggiornato: i pezzi uguali entrano nell'annuncio appena creato
                const errors = ready.flatMap((x) => {
                  const p = useStore.getState().parts.find((y) => y.id === x.p.id);
                  if (!p || p.annuncioId) return [];
                  const r = useStore.getState().publishAnnuncio(p.id, bozzaFor(p, useStore.getState().vehicles));
                  return r.ok ? [] : [`${p.id}: ${r.error}`];
                });
                setMsg(
                  errors.length
                    ? { tone: "danger", text: `Pubblicati ${ready.length - errors.length} ricambi. Non pubblicati: ${errors.join(" · ")}` }
                    : { tone: "ok", text: `${ready.length} ricambi pubblicati sul negozio` },
                );
              }}
            >
              {ready.length === 1 ? "Pubblica l'unico pronto" : `Pubblica i ${ready.length} pronti`}
            </Button>
          )
        }
      />
      {msg && <div className="mb-4"><Notice tone={msg.tone}>{msg.text}</Notice></div>}
      {preview && (
        <div className="mb-6">
          <AnnuncioPreview
            key={`${preview.id}-${ebayCollegato}`}
            part={preview}
            ebayDefault={ebayCollegato}
            onCancel={() => setPreviewId(null)}
            onDone={(text, ok) => {
              setMsg({ tone: ok ? "ok" : "danger", text });
              if (ok) setPreviewId(null);
            }}
          />
        </div>
      )}
      <Panel title={`In coda · ${queue.length}`}>
        {queue.length === 0 ? (
          <Empty title="Nessuna scheda in attesa" />
        ) : (
          <ul className="divide-y divide-hair-soft">
            {queue.map(({ p, placement, missing }) => (
              <li key={p.id} className="grid grid-cols-[56px_1fr] gap-3 px-4 py-3 md:grid-cols-[56px_1fr_auto] md:items-center">
                <PartImage src={p.photos[0]} typeId={p.typeId} className="size-14 rounded bg-white [&>span]:hidden" />
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <Link href={`/ricambi/${p.id}`} className="code text-[22px] font-bold leading-none text-ink hover:text-band">{p.id}</Link>
                    <StatusChip status={p.status} />
                    <span className="code font-bold">{euro(p.price)}</span>
                  </div>
                  <div className="truncate font-medium">{p.description}</div>
                  {missing.length > 0 ? (
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {missing.map((m) => (
                        <span key={m.label} className="rounded bg-danger-bg px-2 py-0.5 text-[13px] font-semibold text-danger">{m.label}</span>
                      ))}
                    </div>
                  ) : placement.kind === "prezzo diverso" ? (
                    <div className="mt-1 text-sm font-semibold text-warn">
                      Prezzo diverso dall&apos;annuncio {placement.annuncioId}: {euro(p.price)} contro {euro(placement.prezzoAnnuncio)}
                    </div>
                  ) : placement.kind === "annuncio ritirato" ? (
                    <div className="mt-1 text-sm font-semibold text-warn">Annuncio {placement.annuncioId} ritirato</div>
                  ) : placement.kind === "unisci" ? (
                    <div className="mt-1 text-sm font-semibold text-ok">Uguale all&apos;annuncio {placement.annuncioId}: si aggiunge ai suoi pezzi</div>
                  ) : (
                    <div className="mt-1 text-sm font-semibold text-ok">Pronto per la pubblicazione</div>
                  )}
                </div>
                <div className="col-span-2 flex flex-wrap gap-2 md:col-span-1 md:justify-end">
                  {p.status === "bozza" && <Button size="sm" variant="secondary" onClick={() => s.setPartStatus(p.id, "disponibile", "Scheda approvata dal responsabile")}>Approva scheda</Button>}
                  {missing.length > 0 ? (
                    <Link href={`/ricambi/${p.id}`} className="inline-flex min-h-9 items-center rounded-md px-3 text-sm font-semibold text-band hover:bg-band-tint">Completa scheda</Link>
                  ) : placement.kind === "prezzo diverso" ? (
                    <>
                      <Button size="sm" variant="secondary" onClick={() => s.resolvePrice(p.id, "annuncio")}>Tieni {euro(placement.prezzoAnnuncio)}</Button>
                      <Button size="sm" onClick={() => s.resolvePrice(p.id, "pezzo")}>Usa {euro(p.price)} per tutti</Button>
                    </>
                  ) : placement.kind === "annuncio ritirato" ? (
                    <Button
                      size="sm"
                      onClick={() => {
                        const r = s.republishAnnuncio(placement.annuncioId, { negozio: true, ebay: false });
                        if (!r.ok) return setMsg({ tone: "danger", text: `${p.id}: ${r.error}` });
                        if (!p.annuncioId) s.placePart(p.id);
                        setMsg({ tone: "ok", text: `Annuncio ${placement.annuncioId} di nuovo sul negozio online` });
                      }}
                    >
                      Ripubblica l&apos;annuncio {placement.annuncioId}
                    </Button>
                  ) : placement.kind === "unisci" ? (
                    <Button size="sm" onClick={() => { s.placePart(p.id); setMsg({ tone: "ok", text: `${p.id} aggiunto all'annuncio ${placement.annuncioId}` }); }}>Aggiungi all&apos;annuncio</Button>
                  ) : (
                    <Button size="sm" onClick={() => { setMsg(null); setPreviewId(p.id); }}>Pubblica</Button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>
      <AnnunciList />
    </div>
  );
}
