"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useStore } from "@/lib/store";
import { Panel, PageTitle, Plate, ButtonLink } from "@/components/ui";
import { dateIt, euro } from "@/lib/logic";
import type { PartStatus } from "@/lib/types";

const STATE_ORDER: { s: PartStatus; label: string; cls: string }[] = [
  { s: "disponibile", label: "Disponibili", cls: "bg-ok" },
  { s: "bozza", label: "In bozza", cls: "bg-draft" },
  { s: "riservato", label: "Riservati", cls: "bg-[#d99a00]" },
  { s: "venduto", label: "Venduti", cls: "bg-ink" },
  { s: "invendibile", label: "Invendibili", cls: "bg-danger" },
];

export default function Oggi() {
  const { vehicles, parts, orders, audit } = useStore();
  const inWork = vehicles.filter((v) => v.work !== "smontato");
  const total = parts.length;
  const count = (s: PartStatus) => parts.filter((p) => p.status === s).length;
  const todo = [
    { n: vehicles.filter((v) => v.verification === "da verificare").length, label: "veicoli con identificazione da verificare", href: "/veicoli" },
    { n: parts.filter((p) => p.status === "bozza").length, label: "schede ricambio in bozza da completare", href: "/pubblicazione" },
    { n: parts.filter((p) => p.status === "disponibile" && !p.location).length, label: "ricambi senza posizione di magazzino", href: "/ricambi?filtro=senza-posizione" },
    { n: parts.filter((p) => p.status === "disponibile" && p.listing !== "pubblicato").length, label: "ricambi disponibili non ancora online", href: "/pubblicazione" },
    { n: orders.filter((o) => o.status === "in attesa di pagamento").length, label: "ordini in attesa di pagamento", href: "/vendite" },
  ].filter((t) => t.n > 0);
  const stockValue = parts.filter((p) => p.status === "disponibile").reduce((a, p) => a + (p.price ?? 0), 0);

  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle
        title="Oggi in piazzale"
        sub={`${inWork.length} veicoli in lavorazione · ${total} ricambi tracciati singolarmente · valore disponibile ${euro(stockValue)}`}
        actions={<ButtonLink href="/veicoli/nuovo">Nuovo ingresso veicolo</ButtonLink>}
      />

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Panel title="Veicoli in lavorazione" action={<Link href="/veicoli" className="text-sm font-semibold text-band">Tutti i veicoli</Link>}>
          <ul className="divide-y divide-hair-soft">
            {inWork.map((v) => {
              const n = parts.filter((p) => p.vehicleId === v.id).length;
              return (
                <li key={v.id}>
                  <Link href={`/veicoli/${v.id}`} className="grid grid-cols-[auto_1fr_auto] items-center gap-4 px-4 py-3.5 hover:bg-carton">
                    <span className="code text-[30px] font-bold leading-none text-ink">{v.id}</span>
                    <span className="min-w-0">
                      <span className="flex flex-wrap items-center gap-2">
                        <Plate plate={v.plate} size="sm" />
                        <span className="truncate font-semibold">{v.make} {v.model}</span>
                      </span>
                      <span className="mt-0.5 block text-sm text-ink-2">
                        {v.work} · {n} ricambi catalogati
                        {v.verification === "da verificare" && <span className="font-semibold text-warn"> · da verificare</span>}
                      </span>
                    </span>
                    <ArrowRight className="size-5 text-ink-3" aria-hidden />
                  </Link>
                </li>
              );
            })}
          </ul>
        </Panel>

        <Panel title="Da sistemare">
          {todo.length === 0 ? (
            <p className="px-4 py-6 text-ink-2">Niente in sospeso.</p>
          ) : (
            <ul className="divide-y divide-hair-soft">
              {todo.map((t) => (
                <li key={t.label}>
                  <Link href={t.href} className="flex items-center gap-4 px-4 py-3 hover:bg-carton">
                    <span className="code w-12 text-right text-[28px] font-bold leading-none text-band">{t.n}</span>
                    <span className="flex-1 font-medium text-ink">{t.label}</span>
                    <ArrowRight className="size-4 text-ink-3" aria-hidden />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <Panel title="Stato del magazzino" className="mt-6">
        <div className="p-4">
          <div className="flex h-5 overflow-hidden rounded" role="img" aria-label="Distribuzione dei ricambi per stato">
            {STATE_ORDER.map((x) => (
              <div key={x.s} className={x.cls} style={{ width: `${(count(x.s) / Math.max(total, 1)) * 100}%` }} />
            ))}
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-5">
            {STATE_ORDER.map((x) => (
              <div key={x.s}>
                <dt className="flex items-center gap-2 text-sm font-semibold text-ink-2">
                  <span className={`size-3 rounded-sm ${x.cls}`} aria-hidden />
                  {x.label}
                </dt>
                <dd className="code text-[32px] font-bold leading-tight">{count(x.s)}</dd>
              </div>
            ))}
          </dl>
        </div>
      </Panel>

      <Panel title="Ultime operazioni" className="mt-6" action={<Link href="/registro" className="text-sm font-semibold text-band">Registro completo</Link>}>
        <ul className="divide-y divide-hair-soft">
          {[...audit].reverse().slice(0, 8).map((e) => (
            <li key={e.id} className="grid grid-cols-[110px_1fr] gap-3 px-4 py-2.5 text-[15px] sm:grid-cols-[130px_120px_1fr]">
              <span className="text-ink-3">{dateIt(e.at, true)}</span>
              <Link href={e.entity === "ricambio" ? `/ricambi/${e.entityId}` : e.entity === "veicolo" ? `/veicoli/${e.entityId}` : "/vendite"} className="code hidden font-semibold text-band sm:block">
                {e.entityId}
              </Link>
              <span className="min-w-0 truncate">
                <span className="font-semibold">{e.action}</span>
                {e.detail && <span className="text-ink-2"> · {e.detail}</span>}
                <span className="text-ink-3"> · {e.user}</span>
              </span>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
