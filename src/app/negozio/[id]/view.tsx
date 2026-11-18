"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { ChevronLeft, ShieldCheck, Truck, Store as StoreIcon } from "lucide-react";
import { useStore } from "@/lib/store";
import { useCart } from "@/lib/cart";
import { CONDITIONS, typeById } from "@/lib/catalog";
import { euro } from "@/lib/logic";
import { onlinePrice } from "@/lib/pricing";
import { platformLabel } from "@/lib/partsdb";
import { Button, PartImage } from "@/components/ui";
import { isShippable } from "@/lib/spedizione";

export default function Prodotto() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const p = useStore((s) => s.parts.find((x) => x.id === id));
  const v = useStore((s) => s.vehicles.find((x) => x.id === p?.vehicleId));
  const add = useCart((s) => s.add);
  const inCart = useCart((s) => s.ids.includes(id));
  const [img, setImg] = useState(0);

  const sellable = p && p.listing === "pubblicato" && p.status === "disponibile";
  if (!p || p.listing !== "pubblicato") {
    return (
      <div className="rounded-md border border-hair bg-label p-8 text-center">
        <p className="font-semibold">Ricambio non disponibile online.</p>
        <Link href="/negozio" className="mt-2 inline-block font-semibold text-band">Torna al catalogo</Link>
      </div>
    );
  }
  const t = typeById(p.typeId);

  return (
    <div>
      <Link href="/negozio" className="-ml-1 mb-4 inline-flex min-h-11 items-center gap-1 font-semibold text-band">
        <ChevronLeft className="size-5" aria-hidden /> Catalogo
      </Link>
      <div className="grid gap-8 md:grid-cols-2">
        <div>
          <PartImage src={p.photos[img]} typeId={p.typeId} className="aspect-square w-full rounded-md border border-hair bg-white p-6" alt={p.description} />
          {p.photos.length > 1 && (
            <div className="mt-2 flex gap-2">
              {p.photos.map((src, i) => (
                <button key={i} onClick={() => setImg(i)} className={`size-16 overflow-hidden rounded border ${i === img ? "border-band ring-2 ring-band" : "border-hair"}`} aria-label={`Foto ${i + 1}`}>
                  <PartImage src={src} typeId={p.typeId} className="size-full bg-white" />
                </button>
              ))}
            </div>
          )}
        </div>
        <div>
          <h1 className="text-[30px] font-bold leading-tight">{p.description}</h1>
          <p className="mt-1 text-[15px] text-ink-2">{t.category} · codice <span className="code font-semibold text-ink">{p.id}</span></p>
          <div className="code mt-3 text-[44px] font-bold leading-none">{euro(onlinePrice(p.price))}</div>
          <p className="mt-1 text-sm text-ink-3">IVA e documenti fiscali da definire (prototipo)</p>

          <dl className="mt-6 grid grid-cols-[140px_1fr] gap-y-2.5 border-y border-hair py-4 text-[15px]">
            <dt className="text-ink-3">Condizioni</dt>
            <dd><b className="code text-[18px]">{p.condition}</b> {CONDITIONS[p.condition].label} · <span className="text-ink-2">{CONDITIONS[p.condition].hint}</span></dd>
            {p.defects && (<><dt className="text-ink-3">Note</dt><dd>{p.defects}</dd></>)}
            {p.side && (<><dt className="text-ink-3">Lato</dt><dd>{p.side}</dd></>)}
            <dt className="text-ink-3">Proviene da</dt>
            <dd>{v ? `${v.make} ${v.model} ${v.version}, ${v.year}` : p.pastDossier?.model ?? "Dal nostro magazzino"}</dd>
            <dt className="text-ink-3">Km del veicolo</dt>
            <dd className="code">{p.km?.toLocaleString("it-IT") ?? "—"}</dd>
            <dt className="text-ink-3">Compatibilità</dt>
            <dd>
              {p.compat?.verified ? (
                <span>
                  <span className="font-semibold text-ok">Codice OE verificato: <span className="code">{p.oem}</span></span>
                  {p.manufacturer && <span className="block text-ink-2">Costruttore: {p.manufacturer}</span>}
                  <span className="mt-2 flex flex-wrap gap-1.5">
                    {p.compat.platforms.map((pl) => (
                      <span key={pl} className="rounded border border-hair bg-carton px-2 py-0.5 text-sm font-medium">{platformLabel(pl)}</span>
                    ))}
                  </span>
                </span>
              ) : (
                <span className="text-ink-2">Non dichiarata. Scrivici targa o telaio della tua auto e la verifichiamo prima della spedizione.</span>
              )}
            </dd>
          </dl>

          <ul className="mt-4 space-y-2 text-[15px]">
            <li className="flex items-center gap-2">{isShippable(p, t.shippable) ? <Truck className="size-5 text-band" aria-hidden /> : <StoreIcon className="size-5 text-band" aria-hidden />}{isShippable(p, t.shippable) ? "Spedizione con corriere (tariffe da definire)" : "Solo ritiro in sede: pezzo voluminoso"}</li>
            <li className="flex items-center gap-2"><ShieldCheck className="size-5 text-band" aria-hidden />Pezzo unico tracciato: quello che vedi è quello che ricevi</li>
          </ul>

          <div className="mt-6">
            {sellable ? (
              inCart ? (
                <Button size="lg" variant="secondary" className="w-full" onClick={() => router.push("/negozio/carrello")}>Nel carrello · vai al carrello</Button>
              ) : (
                <Button size="lg" className="w-full" onClick={() => add(p.id)}>Aggiungi al carrello</Button>
              )
            ) : (
              <p className="rounded-md bg-warn-bg px-4 py-3 font-semibold text-warn">Questo pezzo è appena stato riservato da un altro acquirente.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
