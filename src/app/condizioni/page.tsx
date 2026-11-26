import type { Metadata } from "next";
import { BRAND, PRODUTTORE } from "@/lib/config";
import { CONDIZIONI } from "@/lib/legale/condizioni";
import { DocumentoLegale } from "@/components/sito/DocumentoLegale";
import { SITO } from "@/components/sito/Sito";

// Condizioni del servizio pubbliche, con l'accordo sul trattamento dei dati in fondo (ancora #accordo, l'id della
// sezione): si aprono senza accesso (percorsi.ts) e si indicizzano (robots.ts, sitemap.ts).
export const metadata: Metadata = {
  metadataBase: new URL(SITO),
  title: `${CONDIZIONI.titolo} · ${BRAND.azienda}`,
  description: `Le condizioni con cui ${PRODUTTORE.ragioneSociale} fornisce ${BRAND.azienda}, il gestionale per autodemolizioni: prova gratuita, abbonamento a moduli, commissione sulle vendite online, disdetta e accordo sul trattamento dei dati.`,
  alternates: { canonical: "/condizioni" },
};

export default function CondizioniPage() {
  return <DocumentoLegale documento={CONDIZIONI} />;
}
