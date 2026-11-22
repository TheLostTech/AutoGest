"use client";

import { useStore } from "@/lib/store";
import { useModuli } from "@/lib/use-moduli";
import { MODULI, ORDINE_MODULI, type Modulo } from "@/lib/moduli";
import { lavoroAperto } from "@/lib/moduli-lavoro";
import { dateIt } from "@/lib/logic";
import { Notice, PageTitle, Panel } from "@/components/ui";

export default function Moduli() {
  const s = useStore();
  const moduli = useModuli();

  function cambia(m: Modulo, acceso: boolean) {
    if (!acceso) {
      const aperto = lavoroAperto(m, s);
      const testo = `Spegnere il modulo ${MODULI[m].nome}?${aperto.length ? `\n\nC'è ancora lavoro aperto:\n· ${aperto.join("\n· ")}` : ""}\n\nI dati restano salvati e tornano visibili riattivando il modulo.`;
      if (!confirm(testo)) return;
    }
    s.setModulo(m, acceso);
  }

  return (
    <div className="mx-auto max-w-3xl">
      <PageTitle title="Moduli" sub="Il Magazzino è la base. Accettazione, Ambiente e Vendite si aggiungono: quelli non attivi restano visibili, bloccati." />
      <div className="mb-5">
        <Notice>Pagina provvisoria: con il login gli interruttori passeranno all&apos;amministratore della piattaforma.</Notice>
      </div>
      <Panel>
        <ul className="divide-y divide-hair-soft">
          {ORDINE_MODULI.map((m) => {
            const acceso = moduli.has(m);
            const base = m === "magazzino";
            const st = s.moduli.find((x) => x.id === m);
            return (
              <li key={m} className="flex items-start justify-between gap-4 px-4 py-4">
                <div className="min-w-0">
                  <p className="text-[17px] font-semibold">{MODULI[m].nome}</p>
                  <p className="mt-0.5 text-[15px] text-ink-2">{MODULI[m].frase}</p>
                  {base ? (
                    <p className="mt-1 text-sm font-semibold text-ok">Sempre incluso</p>
                  ) : (
                    st?.cambiatoAt && <p className="mt-1 text-sm text-ink-3">{acceso ? "Attivato" : "Spento"} il {dateIt(st.cambiatoAt, true)} · {st.cambiatoDa}</p>
                  )}
                </div>
                <label className="flex shrink-0 cursor-pointer items-center gap-2 pt-1 text-[15px] font-semibold">
                  <input type="checkbox" role="switch" className="size-6 accent-band" checked={acceso} disabled={base} onChange={(e) => cambia(m, e.target.checked)} />
                  {acceso ? "Attivo" : "Spento"}
                </label>
              </li>
            );
          })}
        </ul>
      </Panel>
    </div>
  );
}
