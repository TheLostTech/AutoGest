import Link from "next/link";
import { BRAND, PRODUTTORE } from "@/lib/config";
import { Logo } from "@/components/Logo";
import { LostarCredit } from "@/components/Lostar";

// Testata e piede delle pagine pubbliche (presentazione e normative): la fascia blu della scatola.

// Demo pubblica: entra senza credenziali dove DEMO_PUBBLICA=1, altrimenti porta all'accesso normale.
export const DEMO = "/demo";
// Dove si parte per comprare: la registrazione dell'azienda. Finché la pagina di registrazione non c'è, porta alla demo.
export const REGISTRAZIONE = DEMO;

// Indirizzo pubblico del sito, per canonical, sitemap e condivisioni. Da impostare in produzione.
export const SITO = (process.env.SITO_PUBBLICO ?? "http://localhost:3000").replace(/\/$/, "");

export function Testata({ attiva }: { attiva?: "news" }) {
  const voce = "hidden rounded-md px-3 py-2 text-[15px] font-semibold text-white/90 hover:bg-white/12 md:block";
  return (
    <>
      <a href="#contenuto" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-label focus:px-4 focus:py-3 focus:text-ink">
        Vai al contenuto
      </a>
      <header className="relative z-20 bg-band text-white">
        <div className="mx-auto flex h-16 max-w-[1240px] items-center justify-between gap-4 px-4 md:h-[72px] md:px-8">
          <Link href="/scopri" aria-label={`${BRAND.azienda}, presentazione`}>
            <Logo className="text-[30px] md:text-[34px]" />
          </Link>
          <nav className="flex items-center gap-1 md:gap-2" aria-label="Sito">
            <Link href="/scopri#in-regola" className={voce}>
              In regola
            </Link>
            <Link href="/scopri#percorso" className={voce}>
              Come funziona
            </Link>
            <Link href="/news" className={`${voce} ${attiva === "news" ? "bg-white/12" : ""}`} aria-current={attiva === "news" ? "page" : undefined}>
              Normative
            </Link>
            <Link href="/scopri#costo" className={voce}>
              Quanto costa
            </Link>
            <a href={DEMO} className="ml-1 inline-flex h-11 items-center rounded-md bg-label px-4 text-[15px] font-semibold text-band hover:bg-band-tint">
              Apri la demo
            </a>
          </nav>
        </div>
      </header>
    </>
  );
}

export function Piede() {
  return (
    <footer className="bg-band-deep text-white/80">
      <div className="mx-auto flex max-w-[1240px] flex-wrap items-center justify-between gap-x-8 gap-y-4 px-4 py-8 md:px-8">
        <p className="text-[15px]">
          {BRAND.azienda} è un prodotto {PRODUTTORE.nome}.
        </p>
        <nav className="flex flex-wrap gap-x-5 gap-y-2 text-[15px]" aria-label="Piede">
          <Link href="/scopri" className="hover:text-white">
            Il gestionale
          </Link>
          <Link href="/news" className="hover:text-white">
            Normative commentate
          </Link>
        </nav>
        <LostarCredit className="text-white/80 hover:text-white" />
      </div>
    </footer>
  );
}
