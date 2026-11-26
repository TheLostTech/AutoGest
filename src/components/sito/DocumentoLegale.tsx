import Link from "next/link";
import { dataVersione, pezziTesto, type Blocco, type Documento, type Sezione } from "@/lib/legale/comune";
import { Piede, Testata } from "./Sito";

// Pagina di un documento legale pubblico (/privacy, /condizioni): titolo, versione, indice con ancore, sezioni.
// La versione è quella di consensi.ts, la stessa salvata con il consenso. Server component.

function Testo({ s }: { s: string }) {
  return pezziTesto(s).map((p, i) => {
    if (typeof p === "string") return p;
    const stile = "font-semibold text-band underline underline-offset-2 hover:text-band-deep";
    if (p.href.startsWith("/"))
      return (
        <Link key={i} href={p.href} className={stile}>
          {p.testo}
        </Link>
      );
    const esterno = p.href.startsWith("https://");
    return (
      <a key={i} href={p.href} className={stile} {...(esterno ? { target: "_blank", rel: "noopener noreferrer" } : {})}>
        {p.testo}
      </a>
    );
  });
}

function Parte({ sezione, numero }: { sezione: Sezione; numero: number }) {
  return (
    <section id={sezione.id} aria-labelledby={`${sezione.id}-titolo`} className="scroll-mt-6 border-t border-hair pt-8">
      <h2 id={`${sezione.id}-titolo`} className="text-[24px] font-bold leading-tight tracking-[-0.02em] md:text-[26px]">
        <span className="code mr-2 text-band">{numero}.</span>
        {sezione.titolo}
      </h2>
      <div className="mt-4 space-y-4 text-[17px] leading-[1.65] text-ink-2 md:text-[18px]">
        {[sezione, ...(sezione.dopo ?? [])].map((b, i) => (
          <ParteBlocco key={i} blocco={b} />
        ))}
      </div>
    </section>
  );
}

function ParteBlocco({ blocco }: { blocco: Blocco }) {
  return (
    <>
      {blocco.paragrafi.map((p) => (
        <p key={p}>
          <Testo s={p} />
        </p>
      ))}
      {blocco.elenco && (
        <ul className="space-y-3">
          {blocco.elenco.map((v) => (
            <li key={v} className="relative pl-6">
              <span className="absolute left-0 top-[0.62em] size-2.5 rounded-full bg-band" aria-hidden />
              <Testo s={v} />
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

export function DocumentoLegale({ documento }: { documento: Documento }) {
  return (
    <div className="min-h-dvh bg-ground text-ink">
      <Testata />
      <main id="contenuto" className="[overflow-wrap:anywhere]">
        <header className="border-b border-hair">
          <div className="mx-auto max-w-[1240px] px-4 pb-10 pt-12 md:px-8 md:pb-14 md:pt-16">
            <h1 className="max-w-[22ch] text-balance text-[clamp(36px,5vw,60px)] font-bold leading-[1.03] tracking-[-0.03em]">{documento.titolo}</h1>
            <p className="mt-5 text-[16px] text-ink-3">
              Versione del <time dateTime={documento.versione}>{dataVersione(documento.versione)}</time>
            </p>
          </div>
        </header>

        <div className="mx-auto grid max-w-[1240px] gap-10 px-4 py-10 md:px-8 md:py-14 lg:grid-cols-[280px_minmax(0,1fr)] lg:gap-16">
          <nav aria-label="Indice" className="lg:sticky lg:top-6 lg:self-start">
            <h2 className="text-[15px] font-semibold text-ink-3">Indice</h2>
            <ol className="mt-3 space-y-1 text-[16px]">
              {documento.sezioni.map((s, i) => (
                <li key={s.id}>
                  <a href={`#${s.id}`} className="flex min-h-11 items-center gap-2 font-semibold text-band hover:underline">
                    <span className="code w-6 shrink-0 text-ink-3">{i + 1}.</span>
                    {s.titolo}
                  </a>
                </li>
              ))}
            </ol>
          </nav>

          <div className="min-w-0 max-w-[68ch] space-y-10">
            {documento.sezioni.map((s, i) => (
              <Parte key={s.id} sezione={s} numero={i + 1} />
            ))}
          </div>
        </div>
      </main>
      <Piede />
    </div>
  );
}
