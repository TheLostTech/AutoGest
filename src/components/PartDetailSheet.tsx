"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { CircleAlert, ExternalLink, Plus, X } from "lucide-react";
import { useStore } from "@/lib/store";
import { CONDITIONS, platformById, typeById } from "@/lib/catalog";
import { platformLabel } from "@/lib/partsdb";
import { locLong } from "@/lib/warehouse";
import { dateIt, euro } from "@/lib/logic";
import { Button, ListingChip, PartImage, Plate, StatusChip } from "./ui";

// Scheda di consultazione del ricambio, aperta sopra la pagina corrente (es. dal banco vendite):
// tutto quello che sappiamo del pezzo e della sua provenienza, senza perdere il conto in corso.
export function PartDetailSheet({
  partId,
  onClose,
  inCart,
  onAdd,
}: {
  partId: string | null;
  onClose: () => void;
  inCart?: boolean;
  onAdd?: (id: string) => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const s = useStore();
  const p = partId ? s.parts.find((x) => x.id === partId) : undefined;
  const v = p ? s.vehicles.find((x) => x.id === p.vehicleId) : undefined;

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (partId && !d.open) d.showModal();
    if (!partId && d.open) d.close();
  }, [partId]);

  const t = p ? typeById(p.typeId) : undefined;
  const platform = v ? platformById(v.platform) : undefined;
  const order = p ? s.orders.find((o) => o.partIds.includes(p.id) && o.status !== "annullato") : undefined;
  const history = p ? s.audit.filter((e) => e.entityId === p.id || e.detail?.includes(p.id)).reverse() : [];

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={(e) => e.target === e.currentTarget && onClose()}
      aria-label={p ? `Dettaglio ricambio ${p.id}` : "Dettaglio ricambio"}
      className="sheet m-0 ml-auto h-dvh max-h-dvh w-full max-w-full bg-ground p-0 text-ink backdrop:bg-ink/50 md:max-w-[560px] md:border-l md:border-hair"
    >
      {p && t && (
        <div className="flex h-full flex-col">
          {/* Testata a fascia: l'ID è il titolo, come sull'etichetta */}
          <header className="bg-band px-4 pb-4 pt-3 text-white">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="code text-[13px] font-semibold uppercase tracking-[0.14em] text-white/80">{t.category}</p>
                <h2 className="code text-[44px] font-bold leading-none">{p.id}</h2>
              </div>
              <button onClick={onClose} className="-mr-2 grid size-11 shrink-0 place-items-center rounded-md hover:bg-band-deep" aria-label="Chiudi dettaglio">
                <X className="size-6" aria-hidden />
              </button>
            </div>
            <p className="mt-2 text-[19px] font-semibold leading-snug">{p.description}</p>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <span className="code text-[32px] font-bold leading-none">{euro(p.price)}</span>
              <StatusChip status={p.status} className="border-white" />
            </div>
          </header>

          <div className="flex-1 space-y-5 overflow-y-auto px-4 py-4">
            {/* Foto */}
            <div className="-mx-4 flex snap-x gap-2 overflow-x-auto px-4">
              {p.photos.length ? (
                p.photos.map((src, i) => (
                  <PartImage
                    key={i}
                    src={src}
                    typeId={p.typeId}
                    className={`shrink-0 snap-start rounded border border-hair-soft bg-white ${p.photos.length === 1 ? "aspect-[16/9] w-full" : "aspect-square w-[44%]"}`}
                  />
                ))
              ) : (
                <PartImage typeId={p.typeId} className="aspect-[2/1] w-full rounded" />
              )}
            </div>

            <Section title="Prodotto">
              <Row k="Tipologia">{t.name} · {t.category}</Row>
              {p.side && <Row k="Lato">{p.side}</Row>}
              <Row k="Condizioni">
                <b className="code text-[18px]">{p.condition}</b> {CONDITIONS[p.condition].label}
                <span className="block text-sm text-ink-3">{CONDITIONS[p.condition].hint}</span>
              </Row>
              {p.defects && <Row k="Difetti">{p.defects}</Row>}
              {p.km != null && <Row k="Km del pezzo"><span className="code">{p.km.toLocaleString("it-IT")}</span></Row>}
              <Row k="Spedizione">{t.shippable ? "Spedibile" : "Solo ritiro in sede"}</Row>
              {p.notes && <Row k="Note">{p.notes}</Row>}
            </Section>

            <Section title="Codici e compatibilità">
              <Row k="Codice OE">
                {p.oem ? (
                  <>
                    <span className="code text-[18px] font-semibold">{p.oem}</span>{" "}
                    <span className={`text-sm font-semibold ${p.oemVerified ? "text-ok" : "text-warn"}`}>{p.oemVerified ? "verificato sul pezzo" : "non verificato"}</span>
                  </>
                ) : (
                  "—"
                )}
              </Row>
              <Row k="Costruttore">{p.manufacturer ?? "—"}</Row>
              {p.legacyCode && <Row k="Codice precedente"><span className="code text-[17px]">{p.legacyCode}</span></Row>}
              <Row k="Montabile su">
                {p.compat?.verified ? (
                  <>
                    <ul className="flex flex-wrap gap-1.5">
                      {p.compat.platforms.map((pl) => (
                        <li key={pl} className="rounded border border-hair bg-carton px-2 py-0.5 text-sm font-medium">{platformLabel(pl)}</li>
                      ))}
                    </ul>
                    <span className="mt-1 block text-sm text-ink-3">{p.compat.source}{p.compat.checkedAt ? ` · verificato ${dateIt(p.compat.checkedAt)}` : ""}</span>
                  </>
                ) : (
                  <span className="flex items-start gap-1.5 text-ink-2">
                    <CircleAlert className="mt-0.5 size-4 shrink-0 text-warn" aria-hidden />
                    Solo il veicolo di provenienza: compatibilità non verificata
                  </span>
                )}
              </Row>
            </Section>

            <Section title="Provenienza">
              {v ? (
                <>
                  <Row k="Veicolo"><span className="code text-[20px] font-bold">{v.id}</span></Row>
                  <Row k="Targa"><Plate plate={v.plate} size="sm" /></Row>
                  <Row k="Modello">{v.make} {v.model} <span className="text-ink-2">{v.version}</span></Row>
                  <Row k="Anno · alim.">{v.year || "—"} · {v.fuel}</Row>
                  <Row k="Km veicolo"><span className="code">{v.km?.toLocaleString("it-IT") ?? "—"}</span></Row>
                  {v.color && <Row k="Colore">{v.color}</Row>}
                  <Row k="Telaio (VIN)"><span className="code font-semibold tracking-wide">{v.vin || "non acquisito"}</span></Row>
                  <Row k="Piattaforma">{platform ? `${platform.label} · ${platform.years}` : <span className="text-warn">non determinata</span>}</Row>
                  <Row k="Pratica">
                    <span className="code font-semibold">{v.dossier.number || "da registrare"}</span>
                    <span className="text-ink-3"> · {v.dossier.kind} · {v.dossier.status}</span>
                  </Row>
                  <Row k="Ingresso">{dateIt(v.intakeAt)}</Row>
                  <Row k="Identificazione"><span className={`font-semibold ${v.verification === "verificato" ? "text-ok" : "text-warn"}`}>{v.verification}</span></Row>
                </>
              ) : (
                p.pastDossier ? (
                  <>
                    <Row k="Pratica">
                      <span className="code font-semibold">{p.pastDossier.number}</span> <span className="text-ink-3">· archivio precedente</span>
                    </Row>
                    {p.pastDossier.plate && <Row k="Targa"><span className="code">{p.pastDossier.plate}</span></Row>}
                    {p.pastDossier.vin && <Row k="Telaio (VIN)"><span className="code">{p.pastDossier.vin}</span></Row>}
                    {p.pastDossier.model && <Row k="Modello">{p.pastDossier.model}</Row>}
                  </>
                ) : (
                  <Row k="Origine"><span className="text-warn">Non documentata · magazzino preesistente</span></Row>
                )
              )}
            </Section>

            <Section title="Magazzino e tracciamento">
              <Row k="Posizione">{p.location ? locLong(p.location) : <span className="text-warn">da assegnare</span>}</Row>
              <Row k="Negozio online"><ListingChip listing={p.listing} /></Row>
              <Row k="Etichette">{p.labelPrints === 0 ? "non stampata" : p.labelPrints === 1 ? "stampata 1 volta" : `stampata ${p.labelPrints} volte`}</Row>
              <Row k="Catalogato">{dateIt(p.createdAt, true)} · {p.createdBy}</Row>
              {p.aiSuggested && (
                <Row k="Riconoscimento foto">
                  {typeById(p.aiSuggested.typeId).name} ({Math.round(p.aiSuggested.confidence * 100)}%) · {p.aiSuggested.accepted ? "accettato" : "corretto dall'operatore"}
                </Row>
              )}
              {order && <Row k="Ordine"><span className="code font-semibold">{order.id}</span> · {order.channel} · {order.status}</Row>}
            </Section>

            {history.length > 0 && (
              <Section title="Storico" plain>
                <ul className="-my-1 divide-y divide-hair-soft">
                  {history.slice(0, 8).map((e) => (
                    <li key={e.id} className="py-2">
                      <span className="font-semibold">{e.action}</span>
                      {e.detail && <span className="text-ink-2"> · {e.detail}</span>}
                      <span className="block text-sm text-ink-3">{dateIt(e.at, true)} · {e.user}</span>
                    </li>
                  ))}
                </ul>
              </Section>
            )}
          </div>

          <footer className="flex flex-wrap items-center gap-2 border-t border-hair bg-label px-4 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
            {onAdd &&
              (inCart ? (
                <span className="code mr-auto text-[15px] font-semibold uppercase tracking-wide text-ok">Già nel conto</span>
              ) : p.status === "disponibile" ? (
                <Button className="mr-auto" onClick={() => { onAdd(p.id); onClose(); }}>
                  <Plus className="size-5" aria-hidden /> Aggiungi al conto
                </Button>
              ) : (
                <span className="mr-auto text-[15px] font-semibold text-danger">Non vendibile ({p.status})</span>
              ))}
            <Link href={`/ricambi/${p.id}`} target="_blank" className="inline-flex min-h-12 items-center gap-2 rounded-md px-3 font-semibold text-band hover:bg-band-tint">
              <span className="sm:hidden">Scheda</span>
              <span className="hidden sm:inline">Scheda completa</span>
              <ExternalLink className="size-4" aria-hidden />
            </Link>
          </footer>
        </div>
      )}
    </dialog>
  );
}

function Section({ title, children, plain }: { title: string; children: React.ReactNode; plain?: boolean }) {
  return (
    <section className="rounded-md border border-hair bg-label">
      <h3 className="code border-b border-hair-soft px-4 py-2.5 text-[15px] font-bold uppercase tracking-wide text-ink-2">{title}</h3>
      {plain ? <div className="p-4 text-[15px]">{children}</div> : <dl className="grid grid-cols-[120px_minmax(0,1fr)] gap-x-4 gap-y-2.5 p-4 text-[15px]">{children}</dl>}
    </section>
  );
}

function Row({ k, children }: { k: string; children: React.ReactNode }) {
  return (
    <>
      <dt className="text-ink-3">{k}</dt>
      <dd className="min-w-0">{children}</dd>
    </>
  );
}
