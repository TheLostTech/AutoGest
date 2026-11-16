"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowRight, Boxes, CarFront, CircleCheck, FileText, PackageCheck, TrendingDown, type LucideIcon } from "lucide-react";
import { ROLE_USER, useStore } from "@/lib/store";
import { ButtonLink, Panel, PageTitle, Plate } from "@/components/ui";
import { buildAgenda, urgencyOf, type AgendaItem, type Urgency } from "@/lib/agenda";
import { dateIt, euro } from "@/lib/logic";
import type { Role } from "@/lib/types";

const GROUPS: { u: Urgency; label: string; tone: string }[] = [
  { u: "scaduto", label: "In ritardo", tone: "text-danger" },
  { u: "oggi", label: "Entro oggi", tone: "text-band" },
  { u: "settimana", label: "Questa settimana", tone: "text-ink-2" },
  { u: "quando-puoi", label: "Più avanti", tone: "text-ink-3" },
];

const KIND_ICON: Record<AgendaItem["kind"], LucideIcon> = {
  veicolo: CarFront,
  pratica: FileText,
  ricambi: Boxes,
  ordine: PackageCheck,
  scorte: TrendingDown,
};

const PRIMARY: Record<Role, { href: string; label: string }> = {
  accettazione: { href: "/veicoli/nuovo", label: "Nuovo ingresso veicolo" },
  smontatore: { href: "/campo", label: "Vai allo smontaggio" },
  magazziniere: { href: "/scansione", label: "Scansiona un'etichetta" },
  responsabile: { href: "/veicoli/nuovo", label: "Nuovo ingresso veicolo" },
  vendite: { href: "/vendite", label: "Nuova vendita al banco" },
};

const DAY = 864e5;

export default function Oggi() {
  const s = useStore();
  const { vehicles, parts, orders, audit, role } = s;
  const agenda = buildAgenda(s, role);
  const late = agenda.filter((i) => urgencyOf(i.due) === "scaduto").length;
  const today = new Date().toLocaleDateString("it-IT", { weekday: "long", day: "numeric", month: "long" });

  const [now] = useState(() => Date.now());
  const avail = parts.filter((p) => p.status === "disponibile");
  const inYard = vehicles.filter((v) => v.work !== "smontato");
  const sold30 = orders.filter((o) => ["pagato", "spedito", "consegnato"].includes(o.status) && now - new Date(o.createdAt).getTime() < 30 * DAY);
  const stats: Record<Role, { label: string; value: string }[]> = {
    accettazione: [
      { label: "Veicoli in piazzale", value: String(inYard.length) },
      { label: "Ingressi ultimi 7 giorni", value: String(vehicles.filter((v) => now - new Date(v.intakeAt).getTime() < 7 * DAY).length) },
      { label: "Pratiche aperte", value: String(vehicles.filter((v) => v.dossier.status !== "completata").length) },
    ],
    smontatore: [
      { label: "Veicoli da smontare", value: String(inYard.length) },
      { label: "Pezzi catalogati oggi", value: String(parts.filter((p) => new Date(p.createdAt).toDateString() === new Date().toDateString()).length) },
    ],
    magazziniere: [
      { label: "Ricambi a magazzino", value: String(avail.length) },
      { label: "Senza posizione", value: String(avail.filter((p) => !p.location).length) },
      { label: "Da preparare", value: String(orders.filter((o) => o.status === "pagato").length) },
    ],
    responsabile: [
      { label: "Ricambi disponibili", value: String(avail.length) },
      { label: "Valore disponibile", value: euro(avail.reduce((a, p) => a + (p.price ?? 0), 0)) },
      { label: "Venduto ultimi 30 giorni", value: euro(sold30.reduce((a, o) => a + o.amount, 0)) },
      { label: "Veicoli in piazzale", value: String(inYard.length) },
    ],
    vendite: [
      { label: "Ricambi disponibili", value: String(avail.length) },
      { label: "Online sul negozio", value: String(avail.filter((p) => p.listing === "pubblicato").length) },
      { label: "Venduto ultimi 30 giorni", value: euro(sold30.reduce((a, o) => a + o.amount, 0)) },
    ],
  };
  const showVehicles = role !== "vendite" && role !== "magazziniere";

  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle
        title="Da fare"
        sub={
          <>
            <span className="first-letter:uppercase">{today}</span> · {ROLE_USER[role].label} ·{" "}
            {agenda.length === 0 ? "niente in sospeso" : `${agenda.length} attività`}
            {late > 0 && <span className="font-semibold text-danger"> · {late} in ritardo</span>}
          </>
        }
        actions={<ButtonLink href={PRIMARY[role].href}>{PRIMARY[role].label}</ButtonLink>}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        {/* Coda di lavoro */}
        <div className="space-y-6">
          {agenda.length === 0 && (
            <div className="label-sheet flex items-center gap-3 p-5">
              <CircleCheck className="size-6 text-ok" aria-hidden />
              <p className="font-semibold">Tutto in ordine: niente da fare per {ROLE_USER[role].label.toLowerCase()}.</p>
            </div>
          )}
          {GROUPS.map((g) => {
            const list = agenda.filter((i) => urgencyOf(i.due) === g.u);
            if (!list.length) return null;
            return (
              <section key={g.u} aria-labelledby={`g-${g.u}`}>
                <h2 id={`g-${g.u}`} className={`code mb-2 flex items-baseline gap-2 text-[15px] font-bold uppercase tracking-wide ${g.tone}`}>
                  {g.label} <span className="text-ink-3">{list.length}</span>
                </h2>
                <ul className="divide-y divide-hair-soft rounded-md border border-hair bg-label">
                  {list.map((i) => (
                    <li key={i.id}>
                      <AgendaRow item={i} urgency={g.u} />
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}
        </div>

        {/* Colonna laterale: numeri del ruolo e veicoli in lavorazione */}
        <div className="space-y-6">
          <Panel title="In numeri">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-4 p-4">
              {stats[role].map((x) => (
                <div key={x.label} className="min-w-0">
                  <dt className="text-sm text-ink-2">{x.label}</dt>
                  <dd className="code text-[30px] font-bold leading-tight">{x.value}</dd>
                </div>
              ))}
            </dl>
          </Panel>

          {showVehicles && (
            <Panel title="Veicoli in lavorazione" action={<Link href="/veicoli" className="text-sm font-semibold text-band">Tutti</Link>}>
              <ul className="divide-y divide-hair-soft">
                {inYard.slice(0, 6).map((v) => (
                  <li key={v.id}>
                    <Link href={role === "smontatore" ? `/campo/${v.id}` : `/veicoli/${v.id}`} className="flex items-center gap-3 px-4 py-2.5 hover:bg-carton">
                      <span className="code text-[20px] font-bold leading-none">{v.id}</span>
                      <Plate plate={v.plate} size="sm" />
                      <span className="min-w-0 flex-1 truncate text-sm text-ink-2">{v.make} {v.model} · {v.work}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </Panel>
          )}

          {role === "responsabile" && (
            <Panel title="Ultime operazioni" action={<Link href="/registro" className="text-sm font-semibold text-band">Registro</Link>}>
              <ul className="divide-y divide-hair-soft">
                {[...audit].reverse().slice(0, 5).map((e) => (
                  <li key={e.id} className="px-4 py-2.5 text-[15px]">
                    <span className="font-semibold">{e.action}</span>
                    {e.detail && <span className="text-ink-2"> · {e.detail}</span>}
                    <span className="block text-sm text-ink-3">{dateIt(e.at, true)} · {e.user}</span>
                  </li>
                ))}
              </ul>
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}

function AgendaRow({ item, urgency }: { item: AgendaItem; urgency: Urgency }) {
  const Icon = KIND_ICON[item.kind];
  return (
    <Link href={item.href} className="grid grid-cols-[64px_minmax(0,1fr)_auto] items-center gap-3 px-3 py-3 hover:bg-carton sm:gap-4 sm:px-4">
      <DueStamp due={item.due} urgency={urgency} icon={Icon} />
      <span className="min-w-0">
        <span className="block font-semibold leading-snug">
          {/* Gli ID (V-000117, R-002301, O-000012) non vanno spezzati sul trattino */}
          {item.title.split(/([VRO]-\d{6})/).map((part, i) => (i % 2 ? <span key={i} className="whitespace-nowrap">{part}</span> : part))}
        </span>
        <span className="block truncate text-sm text-ink-2">{item.detail}</span>
      </span>
      <span className="flex items-center gap-1.5 text-[15px] font-semibold text-band">
        <span className="hidden sm:inline">{item.action}</span>
        <ArrowRight className="size-5" aria-hidden />
      </span>
    </Link>
  );
}

// Timbro di scadenza: come la data stampata sulla scatola
function DueStamp({ due, urgency, icon: Icon }: { due?: string; urgency: Urgency; icon: LucideIcon }) {
  if (!due) {
    return (
      <span className="grid h-14 place-items-center rounded border border-hair-soft bg-carton text-ink-3">
        <Icon className="size-5" aria-hidden />
      </span>
    );
  }
  const d = new Date(due);
  const days = Math.ceil((new Date().setHours(0, 0, 0, 0) - new Date(due).setHours(0, 0, 0, 0)) / DAY);
  const cls =
    urgency === "scaduto"
      ? "border-danger bg-danger-bg text-danger"
      : urgency === "oggi"
        ? "border-band bg-band text-white"
        : urgency === "settimana"
          ? "border-hair bg-label text-ink"
          : "border-hair-soft bg-carton text-ink-2";
  return (
    <span className={`code grid h-14 place-content-center rounded border text-center leading-none ${cls}`}>
      {urgency === "scaduto" ? (
        <>
          <span className="text-[22px] font-bold">{days}</span>
          <span className="mt-0.5 text-[11px] font-semibold uppercase tracking-wide">{days === 1 ? "giorno" : "giorni"}</span>
        </>
      ) : urgency === "oggi" ? (
        <span className="text-[17px] font-bold uppercase tracking-wide">Oggi</span>
      ) : (
        <>
          <span className="text-[22px] font-bold">{d.getDate()}</span>
          <span className="mt-0.5 text-[11px] font-semibold uppercase tracking-wide">{d.toLocaleDateString("it-IT", { month: "short" }).replace(".", "")}</span>
        </>
      )}
    </span>
  );
}
