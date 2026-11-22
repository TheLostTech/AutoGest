import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Condizioni del servizio · Gestionale", robots: { index: false } };

// Segnaposto: il testo delle condizioni arriverà più avanti.
export default function CondizioniPage() {
  return (
    <main className="grid min-h-dvh place-items-center bg-ground px-4 py-10">
      <div className="label-sheet w-full max-w-md space-y-4 p-5">
        <h1 className="code text-[18px] font-bold uppercase tracking-wide text-ink">Condizioni del servizio</h1>
        <p className="text-[16px] text-ink-2">Condizioni del servizio: in preparazione.</p>
        <Link href="/registrati" className="inline-flex min-h-11 items-center text-[14px] font-semibold text-band underline">
          Torna alla registrazione
        </Link>
      </div>
    </main>
  );
}
