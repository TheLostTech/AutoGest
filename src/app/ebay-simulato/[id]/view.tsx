"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useStore } from "@/lib/store";
import { euro } from "@/lib/logic";
import { onlinePrice } from "@/lib/pricing";
import { nextToShip, partsOf, quantityOf } from "@/lib/annunci";
import { PartImage } from "@/components/ui";

export default function EbaySimulato() {
  const { id } = useParams<{ id: string }>();
  const parts = useStore((s) => s.parts);
  const annunci = useStore((s) => s.annunci);
  const a = annunci.find((x) => x.id === id);

  // Foto dal prossimo a partire o, a zero pezzi, dall'ultimo pezzo entrato
  const qtyOra = a ? quantityOf(a, parts) : 0;
  const p = a
    ? qtyOra > 0
      ? nextToShip(a, parts)[0]
      : [...partsOf(a, parts)].sort((x, y) => y.createdAt.localeCompare(x.createdAt))[0]
    : undefined;
  // Come eBay: quantità, prezzo e stato dell'ultimo invio riuscito. Prima del primo invio, i valori del gestionale (segnalati)
  const inviato = a?.ebay?.quantitaInviata !== undefined && a.ebay.prezzoInviato !== undefined;
  const qty = inviato ? a!.ebay!.quantitaInviata! : qtyOra;
  const prezzo = inviato ? a!.ebay!.prezzoInviato! : a ? (onlinePrice(a.price) ?? a.price) : 0;
  const stato = a?.ebay?.stato;
  const chiuso = stato === "ritirato" || stato === "chiuso da eBay";

  return (
    <div className="min-h-screen bg-white text-ink">
      <div className="bg-label px-4 py-3 text-center text-[15px] font-semibold" role="status">
        Annuncio eBay simulato: questa pagina non è su eBay, serve solo per provare il gestionale.
      </div>
      <main className="mx-auto max-w-4xl p-4 md:p-8">
        {!a ? (
          <div className="rounded-md border border-hair p-8 text-center">
            <p className="font-semibold">Annuncio non trovato</p>
            <Link href="/" className="mt-2 inline-block font-semibold text-band">Torna al gestionale</Link>
          </div>
        ) : (
          <div className="grid gap-8 md:grid-cols-2">
            <PartImage src={p?.photos[0]} typeId={a.typeId} className="aspect-square w-full rounded-md border border-hair bg-white p-6" alt={a.titolo} />
            <div>
              <h1 className="text-[28px] font-bold leading-tight">{a.titolo}</h1>
              {!inviato && (
                <p className="mt-2 rounded bg-label px-2 py-1 text-sm font-semibold">Non ancora mandato a eBay: prezzo e quantità sono quelli del gestionale.</p>
              )}
              <p className="mt-3 text-[30px] font-bold">{euro(prezzo)}</p>
              {stato && <p className="mt-1 text-[15px] text-ink-2">Stato su eBay: {stato}</p>}
              {chiuso ? (
                <p className="mt-2 text-[17px] font-semibold">Annuncio non più in vendita</p>
              ) : qty > 0 ? (
                <p className="mt-2 text-[17px]">Quantità disponibile: {qty}</p>
              ) : (
                <p className="mt-2 text-[17px] font-semibold">Esaurito: nascosto dalle ricerche di eBay</p>
              )}
              {a.descrizione && <p className="mt-4 whitespace-pre-line text-[15px] text-ink-2">{a.descrizione}</p>}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
