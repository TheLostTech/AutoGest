"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowUpFromLine, BadgeCheck, CircleCheck, CircleX, MapPin, Printer, ShoppingCart, Upload } from "lucide-react";
import { useStore } from "@/lib/store";
import { CONDITIONS, typeById } from "@/lib/catalog";
import { dateIt, euro, openOrderFor, publishChecks } from "@/lib/logic";
import { firstFreeSlot, locLong, locToString, normLoc, warehouseFor } from "@/lib/warehouse";
import { LocationPicker, locComplete, startLocation } from "@/components/LocationPicker";
import { CatalogPanel } from "@/components/CatalogPanel";
import { catalogFor } from "@/lib/partsdb";
import { listPrice, suggestUsedPrice } from "@/lib/pricing";
import type { Location } from "@/lib/types";
import { PartLabel } from "@/components/PartLabel";
import { Lifecycle } from "@/components/Lifecycle";
import { Button, Empty, ListingChip, Notice, Panel, PartImage, Plate, StatusChip } from "@/components/ui";

export default function SchedaRicambio() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const s = useStore();
  const p = s.parts.find((x) => x.id === id);
  const v = p ? s.vehicles.find((x) => x.id === p.vehicleId) : undefined;
  const [loc, setLoc] = useState<Location | undefined>(p?.location);
  const [editLoc, setEditLoc] = useState(false);
  const [price, setPrice] = useState(p?.price ? String(p.price) : "");
  const [msg, setMsg] = useState<{ tone: "ok" | "danger"; text: string } | null>(null);

  if (!p) return <Empty title={`Ricambio ${id} non trovato`}>Controlla il codice sull&apos;etichetta o cerca nel magazzino.</Empty>;
  const t = typeById(p.typeId);
  const suggestedWh = warehouseFor(t.category, t.shippable, s.warehouses);
  const pickLoc = loc ?? firstFreeSlot(suggestedWh, s.parts) ?? startLocation(suggestedWh.id, s.warehouses, s.parts);
  const checks = publishChecks(p, v);
  const blocking = checks.filter((c) => c.blocking && !c.ok);
  const history = s.audit.filter((e) => e.entityId === p.id || e.detail?.includes(p.id)).reverse();
  const order = s.orders.find((o) => o.partIds.includes(p.id) && o.status !== "annullato");
  const cat = v ? catalogFor(p.typeId, v.platform, p.side) : null;
  const rule = s.rules.find((r) => r.typeId === p.typeId);
  const inStock = s.parts.filter((x) => x.typeId === p.typeId && x.status === "disponibile" && x.id !== p.id).length;
  const suggested = cat ? suggestUsedPrice(cat.newPrice, p.condition, inStock, rule?.max ?? 99) : undefined;

  const flash = (tone: "ok" | "danger", text: string) => {
    setMsg({ tone, text });
    setTimeout(() => setMsg(null), 3500);
  };

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-4 flex flex-wrap items-center gap-3 text-[15px]">
        <StatusChip status={p.status} />
        <ListingChip listing={p.listing} />
        <span className="text-ink-3">catalogato {dateIt(p.createdAt, true)} da {p.createdBy}</span>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
        <div className="space-y-6">
          <PartLabel part={p} vehicle={v} />
          <p className="-mt-3 text-[15px] font-semibold text-ink-2">{locLong(p.location)}</p>
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={() => {
                s.printLabel(p.id);
                window.open(`/etichetta/${p.id}`, "_blank");
              }}
            >
              <Printer className="size-5" aria-hidden />
              {p.labelPrints > 0 ? `Ristampa etichetta (${p.labelPrints})` : "Stampa etichetta"}
            </Button>
            {p.status !== "venduto" && p.status !== "scartato" && (
              <Button variant="secondary" onClick={() => setEditLoc(true)}>
                <MapPin className="size-5" aria-hidden />
                {p.location ? "Sposta" : "Assegna posizione"}
              </Button>
            )}
            {p.location && (
              // Scarico manuale: lo stesso della scansione scaffale → pezzo
              <Button
                variant="secondary"
                onClick={() => {
                  const from = locToString(p.location);
                  const order = openOrderFor(p.id, s.orders);
                  s.pickPart(p.id, order ? `per ${order.id}` : "manuale");
                  setLoc(undefined);
                  flash("ok", `${p.id} prelevato da ${from}${order ? ` per l'ordine ${order.id}` : ""}`);
                }}
              >
                <ArrowUpFromLine className="size-5" aria-hidden />
                Preleva dallo scaffale
              </Button>
            )}
            {p.status === "disponibile" && (
              <Button variant="secondary" onClick={() => router.push(`/vendite?pezzo=${p.id}`)}>
                <ShoppingCart className="size-5" aria-hidden />
                Vendi al banco
              </Button>
            )}
          </div>

          <Panel title="Percorso del pezzo">
            <div className="p-4">
              <Lifecycle part={p} />
            </div>
          </Panel>

          {editLoc && (
            <Panel title="Posizione di magazzino">
              <div className="space-y-4 p-4">
                <LocationPicker value={pickLoc} onChange={setLoc} typeId={p.typeId} />
                <div className="flex gap-2">
                  <Button disabled={!locComplete(pickLoc)} onClick={() => { const l = normLoc(pickLoc.mag, pickLoc.corsia, pickLoc.scaffale, pickLoc.ripiano, pickLoc.contenitore); s.setLocation(p.id, l); setLoc(l); setEditLoc(false); flash("ok", `Posizione ${locToString(l)} registrata`); }}>Conferma posizione</Button>
                  <Button variant="quiet" onClick={() => setEditLoc(false)}>Annulla</Button>
                </div>
              </div>
            </Panel>
          )}

          <Panel title="Provenienza">
            {v ? (
              <Link href={`/veicoli/${v.id}`} className="block p-4 hover:bg-carton">
                <div className="code text-[34px] font-bold leading-none">{v.id}</div>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <Plate plate={v.plate} size="sm" />
                  <span className="font-semibold">{v.make} {v.model}</span>
                  <span className="text-ink-2">{v.version} · {v.year}</span>
                </div>
                <dl className="mt-3 grid grid-cols-[110px_1fr] gap-y-1.5 text-[15px]">
                  <dt className="text-ink-3">Telaio</dt>
                  <dd className="code font-semibold">{v.vin || "—"}</dd>
                  <dt className="text-ink-3">Pratica</dt>
                  <dd className="code font-semibold">{v.dossier.number || "da registrare"} <span className="font-sans font-normal text-ink-3">· {v.dossier.status}</span></dd>
                  <dt className="text-ink-3">Km veicolo</dt>
                  <dd className="code">{v.km?.toLocaleString("it-IT") ?? "—"}</dd>
                  <dt className="text-ink-3">Verifica</dt>
                  <dd className={v.verification === "verificato" ? "font-semibold text-ok" : "font-semibold text-warn"}>{v.verification}</dd>
                </dl>
              </Link>
            ) : (
              <PastOrigin p={p} />
            )}
          </Panel>
        </div>

        <div className="space-y-6">
          {msg && <Notice tone={msg.tone}>{msg.text}</Notice>}

          <Panel title="Foto">
            <div className="grid grid-cols-2 gap-2 p-3">
              {p.photos.length ? (
                p.photos.map((src, i) => <PartImage key={i} src={src} typeId={p.typeId} className="aspect-square w-full rounded border border-hair-soft bg-white" />)
              ) : (
                <PartImage typeId={p.typeId} className="col-span-2 aspect-[2/1] w-full rounded" />
              )}
            </div>
          </Panel>

          <Panel title="Dati commerciali">
            <dl className="grid grid-cols-[130px_1fr] gap-x-4 gap-y-2.5 p-4 text-[15px]">
              <dt className="text-ink-3">Tipologia</dt>
              <dd>{t.name} · {t.category}</dd>
              <dt className="text-ink-3">Condizioni</dt>
              <dd><b className="code text-[18px]">{p.condition}</b> {CONDITIONS[p.condition].label}{p.defects ? ` · ${p.defects}` : ""}</dd>
              <dt className="text-ink-3">Spedizione</dt>
              <dd>{t.shippable ? "Spedibile" : "Solo ritiro in sede"}</dd>
              <dt className="text-ink-3">Prezzo</dt>
              <dd className="flex items-center gap-2">
                <input className="field code h-11 min-h-0 w-28 text-[18px] font-bold" inputMode="numeric" value={price} onChange={(e) => setPrice(e.target.value.replace(/[^0-9]/g, ""))} aria-label="Prezzo in euro" />
                <span className="text-ink-3">€</span>
                {price !== String(p.price ?? "") && (
                  <Button size="sm" onClick={() => { s.updatePart(p.id, { price: price ? Number(price) : undefined }, "Prezzo modificato", `${euro(p.price)} → ${euro(Number(price))}`); flash("ok", "Prezzo aggiornato"); }}>Salva</Button>
                )}
              </dd>
              {cat && (
                <>
                  <dt className="text-ink-3">Nuovo originale</dt>
                  <dd>
                    <span className="code text-[18px]">{euro(cat.newPrice)}</span>
                    {suggested !== undefined && (
                      <span className="text-sm text-ink-2">
                        {" "}· suggerito <b className="code">{euro(suggested)}</b>
                        {String(suggested) !== price && (
                          <button className="ml-2 font-semibold text-band underline" onClick={() => setPrice(String(suggested))}>usa</button>
                        )}
                      </span>
                    )}
                  </dd>
                </>
              )}
              {p.price !== undefined && (
                <>
                  <dt className="text-ink-3">Listini</dt>
                  <dd className="flex flex-wrap gap-x-4 gap-y-1">
                    {s.listini.map((l) => (
                      <span key={l.id} className="text-sm">
                        <span className="text-ink-2">{l.name}</span> <b className="code text-[16px]">{euro(listPrice(p.price, l))}</b>
                      </span>
                    ))}
                  </dd>
                </>
              )}
              {order && (
                <>
                  <dt className="text-ink-3">Ordine</dt>
                  <dd><Link href="/vendite" className="code font-semibold text-band underline">{order.id}</Link> · {order.channel} · {order.status}</dd>
                </>
              )}
            </dl>
          </Panel>

          <CatalogPanel part={p} vehicle={v} />

          <Panel title="Controlli per la pubblicazione">
            <ul className="space-y-2 p-4">
              {checks.map((c) => (
                <li key={c.label} className="flex items-start gap-2.5 text-[15px]">
                  {c.ok ? <CircleCheck className="mt-0.5 size-5 shrink-0 text-ok" aria-hidden /> : <CircleX className={`mt-0.5 size-5 shrink-0 ${c.blocking ? "text-danger" : "text-ink-3"}`} aria-hidden />}
                  <span className={c.ok ? "" : c.blocking ? "font-semibold" : "text-ink-2"}>
                    {c.label}
                    {!c.ok && c.hint && <span className="block text-sm font-normal text-ink-3">{c.hint}</span>}
                  </span>
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-2 border-t border-hair-soft p-4">
              {p.status === "bozza" && (
                <Button variant="secondary" onClick={() => { s.setPartStatus(p.id, "disponibile", "Scheda approvata dal responsabile"); flash("ok", "Scheda approvata: ora è disponibile"); }}>
                  <BadgeCheck className="size-5" aria-hidden />
                  Approva scheda
                </Button>
              )}
              {p.listing !== "pubblicato" ? (
                <Button
                  disabled={blocking.length > 0}
                  onClick={() => {
                    const r = s.publish(p.id);
                    flash(r.ok ? "ok" : "danger", r.ok ? "Pubblicato sul negozio online" : `Non pubblicabile: ${r.conflicts?.join(", ")}`);
                  }}
                >
                  <Upload className="size-5" aria-hidden />
                  {blocking.length ? `Pubblica (${blocking.length} da sistemare)` : "Pubblica sul negozio"}
                </Button>
              ) : (
                <Button variant="secondary" onClick={() => { s.unpublish(p.id); flash("ok", "Ritirato dal negozio"); }}>Ritira dal negozio</Button>
              )}
            </div>
          </Panel>

          <Panel title="Altre azioni">
            <div className="flex flex-wrap gap-2 p-4">
              {p.status !== "invendibile" && p.status !== "venduto" && p.status !== "scartato" && p.status !== "riservato" && (
                <Button variant="danger" size="sm" onClick={() => { const r = prompt("Motivo (es. danneggiato in magazzino):"); if (r) s.setPartStatus(p.id, "invendibile", r); }}>Segna invendibile</Button>
              )}
              {p.status === "invendibile" && (
                <>
                  <Button variant="secondary" size="sm" onClick={() => s.setPartStatus(p.id, "bozza", "Rimesso in lavorazione per verifica")}>Rimetti in verifica</Button>
                  <Button variant="danger" size="sm" onClick={() => { const r = prompt("Motivo dello scarto:"); if (r) s.setPartStatus(p.id, "scartato", r); }}>Scarta</Button>
                </>
              )}
              <Button variant="quiet" size="sm" onClick={() => { s.printLabel(p.id); s.log({ entity: "ricambio", entityId: p.id, action: "Etichetta danneggiata segnalata", detail: "Sostituita con ristampa, stesso ID" }); flash("ok", "Ristampa registrata: l'ID non cambia"); window.open(`/etichetta/${p.id}`, "_blank"); }}>
                Etichetta danneggiata
              </Button>
            </div>
          </Panel>

          <Panel title="Storico del pezzo">
            <ol className="divide-y divide-hair-soft text-[15px]">
              {history.map((e) => (
                <li key={e.id} className="px-4 py-2.5">
                  <span className="font-semibold">{e.action}</span>
                  {e.detail && <span className="text-ink-2"> · {e.detail}</span>}
                  <span className="block text-sm text-ink-3">{dateIt(e.at, true)} · {e.user} · {e.device}</span>
                </li>
              ))}
            </ol>
          </Panel>
        </div>
      </div>
    </div>
  );
}

// Pezzo dal magazzino preesistente: pratica passata (vecchio archivio) o provenienza non documentata
function PastOrigin({ p }: { p: import("@/lib/types").Part }) {
  if (!p.pastDossier)
    return <p className="p-4 text-[15px] text-warn">Provenienza non documentata: pezzo trovato nel magazzino preesistente{p.legacyCode ? ` (vecchio codice ${p.legacyCode})` : ""}.</p>;
  const d = p.pastDossier;
  return (
    <dl className="grid grid-cols-[110px_1fr] gap-y-1.5 p-4 text-[15px]">
      <dt className="text-ink-3">Pratica</dt>
      <dd className="code font-semibold">{d.number} <span className="font-sans font-normal text-ink-3">· archivio precedente</span></dd>
      <dt className="text-ink-3">Targa</dt>
      <dd className="code">{d.plate || "—"}</dd>
      <dt className="text-ink-3">Telaio</dt>
      <dd className="code">{d.vin || "—"}</dd>
      <dt className="text-ink-3">Modello</dt>
      <dd>{d.model || "—"}</dd>
    </dl>
  );
}
