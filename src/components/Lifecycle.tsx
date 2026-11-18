"use client";

import { useListing, useStore } from "@/lib/store";
import type { Part } from "@/lib/types";

// Il ciclo di vita del pezzo come linea a fermate: ogni passaggio resta visibile.
const STOPS = [
  { key: "catalogato", label: "Catalogato" },
  { key: "etichettato", label: "Etichettato" },
  { key: "posizione", label: "In magazzino" },
  { key: "online", label: "Online" },
  { key: "riservato", label: "Riservato" },
  { key: "venduto", label: "Venduto" },
] as const;

export function Lifecycle({ part }: { part: Part }) {
  const listing = useListing(part);
  // Prima ogni reso segnava il pezzo «ritirato»: il reso si legge anche dagli ordini, per i pezzi mai stati online
  const returned = useStore((s) => s.orders.some((o) => o.status === "reso" && o.partIds.includes(part.id)));
  const reached: Record<string, boolean> = {
    catalogato: true,
    etichettato: part.labelPrints > 0,
    posizione: !!part.location,
    online: listing === "pubblicato",
    riservato: part.status === "riservato" || part.status === "venduto",
    venduto: part.status === "venduto",
  };
  const lastIdx = STOPS.reduce((acc, s, i) => (reached[s.key] ? i : acc), 0);
  const off = part.status === "invendibile" || part.status === "scartato";
  return (
    <div>
      <div className="relative">
      <div className="absolute left-[8.33%] right-[8.33%] top-[11px] h-[4px] rounded bg-hair-soft" aria-hidden />
      <div
        className="absolute left-[8.33%] top-[11px] h-[4px] rounded bg-band transition-[width] duration-700 ease-out-expo"
        style={{ width: `${(lastIdx / (STOPS.length - 1)) * 83.33}%` }}
        aria-hidden
      />
      <ol className="relative grid grid-cols-6" aria-label="Ciclo di vita del ricambio">
        {STOPS.map((s, i) => {
          const on = reached[s.key];
          const current = i === lastIdx;
          return (
            <li key={s.key} className="relative flex flex-col items-center text-center">
              <span
                className={`relative z-10 grid size-[26px] place-items-center rounded-full border-[4px] ${
                  current ? "border-band bg-white" : on ? "border-band bg-band" : "border-hair bg-white"
                }`}
              >
                {current && <span className="size-2 rounded-full bg-band" />}
              </span>
              <span className={`mt-1.5 text-[12px] font-semibold leading-tight md:text-[13px] ${on ? "text-ink" : "text-ink-3"}`}>{s.label}</span>
            </li>
          );
        })}
      </ol>
      </div>
      {off && (
        <p className="mt-3 rounded bg-danger-bg px-3 py-2 text-sm font-semibold text-danger">
          Fuori linea: {part.status}. Il pezzo resta tracciato ma non è vendibile.
        </p>
      )}
      {part.status === "bozza" && (listing === "ritirato" || returned) && (
        <p className="mt-3 rounded bg-warn-bg px-3 py-2 text-sm font-semibold text-warn">Rientrato da reso: da ricontrollare prima di rimetterlo in vendita.</p>
      )}
    </div>
  );
}
