"use client";

import { useParams } from "next/navigation";
import { useEffect } from "react";
import { Printer } from "lucide-react";
import { useStore } from "@/lib/store";
import { PartLabel } from "@/components/PartLabel";
import { QrAddressNote, usePublicBase } from "@/components/codes";

export default function StampaEtichetta() {
  const { id } = useParams<{ id: string }>();
  const p = useStore((s) => s.parts.find((x) => x.id === id));
  const v = useStore((s) => s.vehicles.find((x) => x.id === p?.vehicleId));
  // Si stampa da sola, ma solo quando si sa quale indirizzo scrivere nel QR
  const { ready } = usePublicBase();
  useEffect(() => {
    if (!ready) return;
    const t = setTimeout(() => window.print(), 600);
    return () => clearTimeout(t);
  }, [ready]);
  if (!p) return <p className="p-8">Ricambio {id} non trovato.</p>;
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-6 bg-ground p-6 print:block print:bg-white print:p-0">
      <style>{`@page { size: 100mm 50mm; margin: 0; }`}</style>
      <PartLabel part={p} vehicle={v} size="print" />
      <div className="no-print max-w-sm text-center text-ink-2">
        <p>Formato 100 × 50 mm. Stampante etichette da definire (Bluetooth, Wi-Fi o USB).</p>
        <QrAddressNote className="mt-2" />
        <button onClick={() => window.print()} className="mt-4 inline-flex min-h-12 items-center gap-2 rounded-md bg-band px-5 font-semibold text-white">
          <Printer className="size-5" aria-hidden /> Stampa di nuovo
        </button>
      </div>
    </div>
  );
}
