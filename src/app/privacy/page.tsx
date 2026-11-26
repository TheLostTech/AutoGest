import type { Metadata } from "next";
import { BRAND, PRODUTTORE } from "@/lib/config";
import { INFORMATIVA_PRIVACY } from "@/lib/legale/privacy";
import { DocumentoLegale } from "@/components/sito/DocumentoLegale";
import { SITO } from "@/components/sito/Sito";

// Informativa privacy pubblica: si apre senza accesso (percorsi.ts) e si indicizza (robots.ts, sitemap.ts).
export const metadata: Metadata = {
  metadataBase: new URL(SITO),
  title: `${INFORMATIVA_PRIVACY.titolo} · ${BRAND.azienda}`,
  description: `Come ${PRODUTTORE.ragioneSociale} tratta i dati personali di chi usa ${BRAND.azienda}, il gestionale per autodemolizioni: dati, finalità, tempi, fornitori, diritti e cookie.`,
  alternates: { canonical: "/privacy" },
};

export default function PrivacyPage() {
  return <DocumentoLegale documento={INFORMATIVA_PRIVACY} />;
}
