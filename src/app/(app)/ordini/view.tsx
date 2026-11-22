"use client";

import { PageTitle } from "@/components/ui";
import { OrdiniPanel } from "@/components/OrdiniPanel";

// Ordini online nel Magazzino (la base): si chiudono qui anche senza il modulo Vendite
export default function OrdiniOnline() {
  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle title="Ordini online" sub="eBay e negozio online: prepara, spedisci, emetti il documento e registra i resi." />
      <OrdiniPanel canali="online" />
    </div>
  );
}
