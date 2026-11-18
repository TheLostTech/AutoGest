import type { Metadata } from "next";
import Link from "next/link";
import { ARTICOLI, dataLunga } from "@/lib/news";
import { BRAND } from "@/lib/config";
import { Piede, SITO, Testata } from "@/components/sito/Sito";
import "../scopri/scopri.css";

const TITOLO = "Normative per autodemolizioni, spiegate e commentate";
const DESCRIZIONE =
  "RENTRI, formulario digitale, bonifica dei veicoli fuori uso, nuovo regolamento europeo, GPSR sui ricambi usati, garanzia: cosa dicono le norme e cosa cambia in piazzale.";

export const metadata: Metadata = {
  metadataBase: new URL(SITO),
  title: `${TITOLO} · ${BRAND.azienda}`,
  description: DESCRIZIONE,
  keywords: [...new Set(ARTICOLI.flatMap((a) => a.parole.slice(0, 2)))],
  alternates: { canonical: "/news" },
  openGraph: { type: "website", locale: "it_IT", title: TITOLO, description: DESCRIZIONE, url: "/news", siteName: BRAND.azienda },
};

export default function NewsPage() {
  const ordinati = [...ARTICOLI].sort((a, b) => b.data.localeCompare(a.data));
  const ld = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: TITOLO,
    description: DESCRIZIONE,
    url: `${SITO}/news`,
    inLanguage: "it-IT",
    hasPart: ordinati.map((a) => ({ "@type": "Article", headline: a.titolo, url: `${SITO}/news/${a.slug}`, datePublished: a.data })),
  };
  return (
    <div className="min-h-dvh bg-ground text-ink">
      <Testata attiva="news" />
      <main id="contenuto">
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(ld).replace(/</g, "\\u003c") }} />
        <section className="border-b border-hair">
          <div className="mx-auto max-w-[1240px] px-4 pb-14 pt-16 md:px-8 md:pb-20 md:pt-24">
            <h1 className="scopri-titolo max-w-[16ch] text-balance">Le norme che toccano il piazzale.</h1>
            <p className="mt-6 max-w-[60ch] text-[18px] leading-[1.6] text-ink-2 md:text-[20px]">
              Ogni scheda riassume una norma con il riferimento ufficiale, poi ti diciamo cosa ne pensiamo e cosa cambia nel lavoro di tutti i giorni. Non sostituisce il consulente
              ambientale o il commercialista: serve ad arrivarci preparati.
            </p>
          </div>
        </section>

        <section className="mx-auto max-w-[1240px] px-4 py-12 md:px-8 md:py-16">
          <ol className="grid gap-px overflow-hidden rounded-md border border-hair bg-hair md:grid-cols-2">
            {ordinati.map((a) => (
              <li key={a.slug} className="bg-label">
                <Link href={`/news/${a.slug}`} className="group flex h-full flex-col p-6 hover:bg-carton md:p-8">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                    <span className="code text-[17px] font-semibold text-band">{a.norma}</span>
                    <time dateTime={a.data} className="text-[14px] text-ink-3">
                      {dataLunga(a.data)}
                    </time>
                  </div>
                  <h2 className="mt-3 text-[24px] font-bold leading-[1.18] tracking-[-0.02em] text-ink group-hover:underline md:text-[27px]">{a.titolo}</h2>
                  <p className="mt-3 text-[16px] leading-[1.6] text-ink-2">{a.descrizione}</p>
                  <ul className="mt-auto flex flex-wrap gap-1.5 pt-5" aria-label="Parole chiave">
                    {a.parole.slice(0, 3).map((p) => (
                      <li key={p} className="rounded-[4px] bg-band-tint px-2 py-1 text-[13px] font-semibold text-band">
                        {p}
                      </li>
                    ))}
                  </ul>
                </Link>
              </li>
            ))}
          </ol>
        </section>
      </main>
      <Piede />
    </div>
  );
}
