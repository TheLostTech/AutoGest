import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ARTICOLI, articolo, dataLunga } from "@/lib/news";
import { BRAND, PRODUTTORE } from "@/lib/config";
import { DEMO, Piede, SITO, Testata } from "@/components/sito/Sito";
import "../../scopri/scopri.css";

// Gli articoli sono tutti prerenderizzati (generateStaticParams): il parametro serve solo a scegliere quale.
export const instant = false;

export function generateStaticParams() {
  return ARTICOLI.map((a) => ({ slug: a.slug }));
}

export async function generateMetadata({ params }: PageProps<"/news/[slug]">): Promise<Metadata> {
  const a = articolo((await params).slug);
  if (!a) return {};
  const url = `/news/${a.slug}`;
  return {
    metadataBase: new URL(SITO),
    title: `${a.titoloSeo ?? a.titolo} · ${BRAND.azienda}`,
    description: a.descrizione,
    keywords: a.parole,
    alternates: { canonical: url },
    openGraph: {
      type: "article",
      locale: "it_IT",
      url,
      title: a.titolo,
      description: a.descrizione,
      siteName: BRAND.azienda,
      publishedTime: a.data,
      modifiedTime: a.aggiornato ?? a.data,
      tags: a.parole,
    },
  };
}

export default async function ArticoloPage({ params }: PageProps<"/news/[slug]">) {
  const a = articolo((await params).slug);
  if (!a) notFound();
  const altri = ARTICOLI.filter((x) => x.slug !== a.slug).slice(0, 3);
  const ld = [
    {
      "@context": "https://schema.org",
      "@type": "Article",
      headline: a.titolo,
      description: a.descrizione,
      keywords: a.parole.join(", "),
      datePublished: a.data,
      dateModified: a.aggiornato ?? a.data,
      inLanguage: "it-IT",
      mainEntityOfPage: `${SITO}/news/${a.slug}`,
      author: { "@type": "Organization", name: PRODUTTORE.nome, url: PRODUTTORE.sito },
      publisher: { "@type": "Organization", name: PRODUTTORE.nome, url: PRODUTTORE.sito },
      citation: a.fonti.map((f) => f.url),
      about: a.norma,
    },
    {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      itemListElement: [
        { "@type": "ListItem", position: 1, name: BRAND.azienda, item: `${SITO}/scopri` },
        { "@type": "ListItem", position: 2, name: "Normative", item: `${SITO}/news` },
        { "@type": "ListItem", position: 3, name: a.titolo, item: `${SITO}/news/${a.slug}` },
      ],
    },
  ];

  return (
    <div className="min-h-dvh bg-ground text-ink">
      <Testata attiva="news" />
      <main id="contenuto">
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(ld).replace(/</g, "\\u003c") }} />
        <article>
          <header className="border-b border-hair">
            <div className="mx-auto max-w-[1240px] px-4 pb-12 pt-10 md:px-8 md:pb-16 md:pt-14">
              <nav aria-label="Percorso" className="text-[15px] text-ink-3">
                <Link href="/news" className="font-semibold text-band hover:underline">
                  Normative
                </Link>
                <span aria-hidden> / </span>
                <span className="code text-[16px]">{a.norma}</span>
              </nav>
              <h1 className="mt-6 max-w-[22ch] text-balance text-[clamp(36px,5vw,64px)] font-bold leading-[1.03] tracking-[-0.03em]">{a.titolo}</h1>
              <p className="mt-6 max-w-[62ch] text-[19px] leading-[1.55] text-ink-2 md:text-[21px]">{a.descrizione}</p>
              <p className="mt-6 text-[15px] text-ink-3">
                Pubblicato il <time dateTime={a.data}>{dataLunga(a.data)}</time>
                {a.aggiornato && a.aggiornato !== a.data && (
                  <>
                    , aggiornato il <time dateTime={a.aggiornato}>{dataLunga(a.aggiornato)}</time>
                  </>
                )}
              </p>
            </div>
          </header>

          <div className="mx-auto grid max-w-[1240px] gap-12 px-4 py-12 md:px-8 md:py-16 lg:grid-cols-[minmax(0,1fr)_340px] lg:gap-16">
            <div className="min-w-0 max-w-[68ch]">
              <h2 className="text-[26px] font-bold tracking-[-0.02em]">Cosa dice la norma</h2>
              <ul className="mt-5 space-y-3">
                {a.sintesi.map((s) => (
                  <li key={s} className="relative pl-6 text-[18px] leading-[1.6] text-ink-2">
                    <span className="absolute left-0 top-[0.62em] size-2.5 rounded-full bg-band" aria-hidden />
                    {s}
                  </li>
                ))}
              </ul>

              {a.date.length > 0 && (
                <>
                  <h2 className="mt-12 text-[26px] font-bold tracking-[-0.02em]">Le date</h2>
                  <ol className="mt-5 border-l-4 border-hair-soft">
                    {a.date.map((d) => (
                      <li key={d.quando + d.cosa} className="relative py-2.5 pl-6">
                        <span className="absolute -left-[13px] top-[17px] size-[22px] rounded-full border-4 border-band bg-label" aria-hidden />
                        <div className="code text-[20px] font-bold leading-tight">{d.quando}</div>
                        <div className="text-[17px] leading-[1.5] text-ink-2">{d.cosa}</div>
                      </li>
                    ))}
                  </ol>
                </>
              )}

              <section className="mt-12 rounded-md bg-band p-6 text-white md:p-8" aria-labelledby="commento">
                <h2 id="commento" className="text-[26px] font-bold tracking-[-0.02em]">
                  Il nostro commento
                </h2>
                <div className="mt-4 space-y-4 text-[18px] leading-[1.65] text-white/90">
                  {a.commento.map((c) => (
                    <p key={c}>{c}</p>
                  ))}
                </div>
              </section>

              {a.nelGestionale && (
                <>
                  <h2 className="mt-12 text-[26px] font-bold tracking-[-0.02em]">Nel gestionale</h2>
                  <p className="mt-4 text-[18px] leading-[1.65] text-ink-2">{a.nelGestionale}</p>
                  <a href={DEMO} className="mt-6 inline-flex h-12 items-center rounded-md bg-band px-5 text-[16px] font-semibold text-white hover:bg-band-deep">
                    Apri la demo
                  </a>
                </>
              )}

              <p className="mt-12 border-t border-hair pt-6 text-[15px] leading-[1.6] text-ink-3">
                Questa scheda è informativa e riassume la norma alla data indicata. Per il tuo impianto fa fede il testo ufficiale: verifica con il consulente ambientale o legale.
              </p>
            </div>

            <aside className="space-y-8 lg:sticky lg:top-6 lg:self-start">
              <div className="label-sheet overflow-hidden">
                <div className="bg-band px-5 py-2.5 text-[15px] font-semibold text-white">Riferimenti</div>
                <ul className="space-y-3 px-5 py-4">
                  {a.riferimenti.map((r) => (
                    <li key={r} className="code text-[17px] font-semibold leading-snug">
                      {r}
                    </li>
                  ))}
                </ul>
                <div className="border-t border-hair-soft px-5 py-4">
                  <h3 className="text-[15px] font-semibold text-ink-3">Fonti ufficiali</h3>
                  <ul className="mt-2 space-y-2 text-[15px]">
                    {a.fonti.map((f) => (
                      <li key={f.url}>
                        <a href={f.url} target="_blank" rel="noopener" className="font-semibold text-band underline-offset-2 hover:underline">
                          {f.nome}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div>
                <h3 className="text-[15px] font-semibold text-ink-3">Parole chiave</h3>
                <ul className="mt-2 flex flex-wrap gap-1.5">
                  {a.parole.map((p) => (
                    <li key={p} className="rounded-[4px] bg-band-tint px-2 py-1 text-[13px] font-semibold text-band">
                      {p}
                    </li>
                  ))}
                </ul>
              </div>
            </aside>
          </div>
        </article>

        {altri.length > 0 && (
          <section className="border-t border-hair bg-carton">
            <div className="mx-auto max-w-[1240px] px-4 py-12 md:px-8 md:py-16">
              <h2 className="text-[26px] font-bold tracking-[-0.02em]">Altre norme</h2>
              <ul className="mt-6 grid gap-px overflow-hidden rounded-md border border-hair bg-hair md:grid-cols-3">
                {altri.map((x) => (
                  <li key={x.slug} className="bg-label">
                    <Link href={`/news/${x.slug}`} className="block h-full p-5 hover:bg-carton">
                      <span className="code text-[16px] font-semibold text-band">{x.norma}</span>
                      <span className="mt-2 block text-[19px] font-bold leading-snug">{x.titolo}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        )}
      </main>
      <Piede />
    </div>
  );
}
