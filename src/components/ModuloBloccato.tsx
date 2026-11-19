"use client";

import Link from "next/link";
import { Check, Lock, MessageCircle } from "lucide-react";
import { BRAND } from "@/lib/config";
import { linkAttivazione, MODULI, type Modulo } from "@/lib/moduli";
import { useModuli } from "@/lib/use-moduli";
import { useStore } from "@/lib/store";

// Al posto di una pagina di un modulo non acquistato: cosa fa il modulo e come chiederne l'attivazione
export function ModuloBloccato({ modulo }: { modulo: Modulo }) {
  const log = useStore((s) => s.log);
  const m = MODULI[modulo];
  return (
    <div className="mx-auto max-w-3xl">
      <div className="overflow-hidden rounded-md border border-hair bg-label">
        {modulo !== "magazzino" && (
          <div className="relative h-44 overflow-hidden border-b border-hair bg-carton md:h-56" aria-hidden>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={`/moduli/${modulo}.jpg`} alt="" className="size-full scale-105 object-cover object-top opacity-70 blur-[3px]" />
            <span className="absolute inset-0 grid place-items-center">
              <span className="grid size-14 place-items-center rounded-full bg-band text-white shadow-lg">
                <Lock className="size-6" />
              </span>
            </span>
          </div>
        )}
        <div className="p-5 md:p-7">
          <p className="code text-[13px] font-semibold uppercase tracking-[0.14em] text-ink-3">Modulo non attivo</p>
          <h1 className="mt-1 text-[28px] font-bold leading-tight md:text-[34px]">{m.nome}</h1>
          <p className="mt-2 text-[17px] text-ink-2">{m.frase}</p>
          <ul className="mt-5 space-y-2.5 text-[16px]">
            {m.punti.map((p) => (
              <li key={p} className="flex gap-2.5">
                <Check className="mt-0.5 size-5 shrink-0 text-ok" aria-hidden />
                {p}
              </li>
            ))}
          </ul>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <a
              href={linkAttivazione(BRAND.azienda, modulo)}
              target="_blank"
              rel="noopener"
              onClick={() => log({ entity: "sistema", entityId: `modulo-${modulo}`, action: "Richiesta attivazione modulo", detail: m.nome })}
              className="press inline-flex min-h-12 items-center justify-center gap-2 rounded-md bg-band px-5 font-semibold text-white transition-colors duration-150 hover:bg-band-deep"
            >
              <MessageCircle className="size-5" aria-hidden />
              Chiedi l&apos;attivazione
            </a>
            <span className="text-[14px] text-ink-3">Si apre WhatsApp con il messaggio già scritto.</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// Dove un modulo non attivo si aggancerebbe a una pagina aperta: una riga sobria al posto della funzione
export function Bloccato({ modulo, funzione, children }: { modulo: Modulo; funzione: string; children: React.ReactNode }) {
  const moduli = useModuli();
  if (moduli.has(modulo)) return <>{children}</>;
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-dashed border-hair bg-label px-4 py-3 text-[15px] text-ink-3">
      <span className="flex items-center gap-2">
        <Lock className="size-4 shrink-0" aria-hidden />
        {funzione}
      </span>
      <Link href={`/moduli/${modulo}`} className="font-semibold text-band underline">
        Scopri il modulo {MODULI[modulo].nome}
      </Link>
    </div>
  );
}
