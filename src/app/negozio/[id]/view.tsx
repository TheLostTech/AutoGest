"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ChevronLeft, Phone, ShieldCheck, Truck, Store as StoreIcon } from "lucide-react";
import { useStore } from "@/lib/store";
import { useCart } from "@/lib/cart";
import { CONDITIONS, typeById } from "@/lib/catalog";
import { euro } from "@/lib/logic";
import { onlinePrice } from "@/lib/pricing";
import { platformLabel } from "@/lib/partsdb";
import { BRAND } from "@/lib/config";
import { Button, Field, PartImage } from "@/components/ui";
import { isShippable } from "@/lib/spedizione";
import { nextToShip, partsOf, quantityOf } from "@/lib/annunci";

function NonDisponibile() {
  return (
    <div className="rounded-md border border-hair bg-label p-8 text-center">
      <p className="font-semibold">Non disponibile</p>
      <Link href="/negozio" className="mt-2 inline-block font-semibold text-band">Torna al catalogo</Link>
    </div>
  );
}

export default function Prodotto() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const parts = useStore((s) => s.parts);
  const vehicles = useStore((s) => s.vehicles);
  const annunci = useStore((s) => s.annunci);
  const add = useCart((s) => s.add);
  const inCart = useCart((s) => s.ids.includes(id));
  const [img, setImg] = useState(0);
  const [email, setEmail] = useState("");
  const [avvisato, setAvvisato] = useState(false);

  // Vecchio indirizzo di un pezzo (R-…): porta al suo annuncio, se è ancora sul negozio
  const oldPart = id.startsWith("R-") ? parts.find((x) => x.id === id) : undefined;
  const oldAnnuncio = oldPart?.annuncioId ? annunci.find((x) => x.id === oldPart.annuncioId) : undefined;
  const redirectTo = oldAnnuncio?.negozio && oldAnnuncio.negozio.stato !== "ritirato" ? oldAnnuncio.id : undefined;
  useEffect(() => {
    if (redirectTo) router.replace(`/negozio/${redirectTo}`);
  }, [redirectTo, router]);

  const a = annunci.find((x) => x.id === id);
  if (redirectTo) return null;
  if (!a || !a.negozio || a.negozio.stato === "ritirato") return <NonDisponibile />;

  // Foto e dati dal prossimo a partire o, se esaurito, dall'ultimo pezzo entrato
  const qty = quantityOf(a, parts);
  const p = qty > 0 ? nextToShip(a, parts)[0] : [...partsOf(a, parts)].sort((x, y) => y.createdAt.localeCompare(x.createdAt))[0];
  if (!p) return <NonDisponibile />;
  const v = vehicles.find((x) => x.id === p.vehicleId);
  const t = typeById(a.typeId);
  const sellable = qty > 0 && a.negozio.stato === "online";

  return (
    <div>
      <Link href="/negozio" className="-ml-1 mb-4 inline-flex min-h-11 items-center gap-1 font-semibold text-band">
        <ChevronLeft className="size-5" aria-hidden /> Catalogo
      </Link>
      <div className="grid gap-8 md:grid-cols-2">
        <div>
          <PartImage src={p.photos[img]} typeId={a.typeId} className="aspect-square w-full rounded-md border border-hair bg-white p-6" alt={a.titolo} />
          {p.photos.length > 1 && (
            <div className="mt-2 flex gap-2">
              {p.photos.map((src, i) => (
                <button key={i} onClick={() => setImg(i)} className={`size-16 overflow-hidden rounded border ${i === img ? "border-band ring-2 ring-band" : "border-hair"}`} aria-label={`Foto ${i + 1}`}>
                  <PartImage src={src} typeId={a.typeId} className="size-full bg-white" />
                </button>
              ))}
            </div>
          )}
        </div>
        <div>
          <h1 className="text-[30px] font-bold leading-tight">{a.titolo}</h1>
          <p className="mt-1 text-[15px] text-ink-2">{t.category} · codice <span className="code font-semibold text-ink">{a.id}</span></p>
          {a.descrizione && <p className="mt-3 whitespace-pre-line text-[15px] text-ink-2">{a.descrizione}</p>}
          <div className="code mt-3 text-[44px] font-bold leading-none">{euro(onlinePrice(a.price))}</div>
          <p className="mt-1 text-sm text-ink-3">IVA e documenti fiscali da definire (prototipo)</p>
          <p className="mt-2 font-semibold text-band">{qty === 0 ? "Esaurito" : qty === 1 ? "1 disponibile" : `${qty} disponibili`}</p>

          <dl className="mt-6 grid grid-cols-[140px_1fr] gap-y-2.5 border-y border-hair py-4 text-[15px]">
            <dt className="text-ink-3">Condizioni</dt>
            <dd><b className="code text-[18px]">{a.condition}</b> {CONDITIONS[a.condition].label} · <span className="text-ink-2">{CONDITIONS[a.condition].hint}</span></dd>
            {p.defects && (<><dt className="text-ink-3">Note</dt><dd>{p.defects}</dd></>)}
            {a.side && (<><dt className="text-ink-3">Lato</dt><dd>{a.side}</dd></>)}
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
            <li className="flex items-center gap-2">{isShippable(a, t.shippable) ? <Truck className="size-5 text-band" aria-hidden /> : <StoreIcon className="size-5 text-band" aria-hidden />}{isShippable(a, t.shippable) ? "Spedizione con corriere (tariffe da definire)" : "Solo ritiro in sede: pezzo voluminoso"}</li>
            <li className="flex items-center gap-2"><ShieldCheck className="size-5 text-band" aria-hidden />Ogni pezzo è tracciato: ricevi quello con il suo codice univoco</li>
          </ul>

          <div className="mt-6">
            {sellable ? (
              inCart ? (
                <Button size="lg" variant="secondary" className="w-full" onClick={() => router.push("/negozio/carrello")}>Nel carrello · vai al carrello</Button>
              ) : (
                <Button size="lg" className="w-full" onClick={() => add(a.id)}>Aggiungi al carrello</Button>
              )
            ) : (
              <div className="space-y-4 rounded-md bg-warn-bg px-4 py-4">
                <p className="font-semibold text-warn">Esaurito: chiamaci per questo pezzo o per altri dello stesso veicolo.</p>
                <a href={`tel:${BRAND.telefono.replace(/\s/g, "")}`} className="code inline-flex min-h-11 items-center gap-2 text-[22px] font-bold text-band">
                  <Phone className="size-5" aria-hidden /> {BRAND.telefono}
                </a>
                {avvisato ? (
                  <p className="font-semibold text-ok">Ti avviseremo quando torna disponibile</p>
                ) : (
                  <form onSubmit={(e) => { e.preventDefault(); setAvvisato(true); }} className="space-y-2">
                    <Field label="La tua email">
                      <input className="field" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
                    </Field>
                    <Button type="submit" variant="secondary">Avvisami quando torna</Button>
                  </form>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
