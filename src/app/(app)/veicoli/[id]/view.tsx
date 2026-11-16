"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { BadgeCheck, Leaf, Wrench } from "lucide-react";
import { useStore } from "@/lib/store";
import { Button, ButtonLink, Empty, Notice, Panel, Plate } from "@/components/ui";
import { RecoveryList } from "@/components/RecoveryList";
import { PraticaPanel } from "@/components/PraticaPanel";
import { PartRow } from "@/components/PartRow";
import { dateIt } from "@/lib/logic";
import { platformById } from "@/lib/catalog";
import { fmtKg, itemKg } from "@/lib/ambiente";

export default function SchedaVeicolo() {
  const { id } = useParams<{ id: string }>();
  const v = useStore((s) => s.vehicles.find((x) => x.id === id));
  const parts = useStore((s) => s.parts).filter((p) => p.vehicleId === id);
  const { updateVehicle, setActiveVehicle, audit } = useStore();

  if (!v) return <Empty title={`Veicolo ${id} non trovato`} />;
  const platform = platformById(v.platform);
  const history = audit.filter((e) => e.entityId === v.id).reverse();

  return (
    <div className="mx-auto max-w-6xl">
      {/* Testata a fascia: l'ID interno è il titolo */}
      <header className="-mx-4 -mt-5 mb-6 bg-band px-4 pb-5 pt-5 text-white md:mx-0 md:mt-0 md:rounded-md md:px-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="code text-[56px] font-bold leading-[0.9] md:text-[76px]" aria-label={`Veicolo ${v.id}`}>{v.id}</h1>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <Plate plate={v.plate} size="lg" />
              <span className="text-[19px] font-semibold">{v.make} {v.model}</span>
              <span className="text-white/80">{v.version}</span>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <ButtonLink href={`/campo/${v.id}`} onClick={() => setActiveVehicle(v.id)} variant="secondary" size="lg" className="border-white bg-white text-band">
              <Wrench className="size-5" aria-hidden />
              {v.work === "accettato" ? "Avvia smontaggio" : "Apri smontaggio"}
            </ButtonLink>
          </div>
        </div>
      </header>

      {v.verification === "da verificare" && (
        <div className="mb-6">
          <Notice tone="warn">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span>Identificazione da verificare{v.notes ? `: ${v.notes}` : ""}. I ricambi di questo veicolo non potranno essere pubblicati finché non viene confermata.</span>
              <Button size="sm" variant="secondary" onClick={() => updateVehicle(v.id, { verification: "verificato" }, "Identificazione verificata", "Controllo su libretto/telaio")}>
                <BadgeCheck className="size-4" aria-hidden />
                Confermo dati e telaio
              </Button>
            </div>
          </Notice>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_1.25fr]">
        <div className="space-y-6">
          <Panel title="Identificazione">
            <dl className="grid grid-cols-[130px_1fr] gap-x-4 gap-y-2.5 p-4 text-[15px]">
              <dt className="text-ink-3">Telaio (VIN)</dt>
              <dd className="code text-[18px] font-semibold tracking-wide">{v.vin || "non acquisito"}</dd>
              <dt className="text-ink-3">Anno · alim.</dt>
              <dd>{v.year || "—"} · {v.fuel}</dd>
              <dt className="text-ink-3">Chilometri</dt>
              <dd className="code text-[18px]">{v.km?.toLocaleString("it-IT") ?? "—"}</dd>
              <dt className="text-ink-3">Peso ingresso</dt>
              <dd className="code text-[18px]">{v.weightKg ? fmtKg(v.weightKg) : "—"}</dd>
              <dt className="text-ink-3">Colore</dt>
              <dd>{v.color || "—"}</dd>
              <dt className="text-ink-3">Piattaforma</dt>
              <dd>{platform ? `${platform.label} · ${platform.years}` : <span className="text-warn">non determinata</span>}</dd>
              <dt className="text-ink-3">Ingresso</dt>
              <dd>{dateIt(v.intakeAt)} · {v.createdBy}</dd>
              <dt className="text-ink-3">Verifica</dt>
              <dd className={v.verification === "verificato" ? "font-semibold text-ok" : "font-semibold text-warn"}>{v.verification}</dd>
            </dl>
          </Panel>

          <Panel title="Bonifica" action={v.bonifica && <Link href={`/veicoli/${v.id}/bonifica`} className="text-sm font-semibold text-band">Dettaglio</Link>}>
            {v.bonifica ? (
              <dl className="grid grid-cols-[130px_1fr] gap-x-4 gap-y-2.5 p-4 text-[15px]">
                <dt className="text-ink-3">Eseguita</dt>
                <dd>{dateIt(v.bonifica.at, true)} · {v.bonifica.by}</dd>
                <dt className="text-ink-3">Rimossi</dt>
                <dd className="code text-[18px]">{fmtKg(v.bonifica.items.reduce((a, i) => a + itemKg(i), 0))}</dd>
                <dt className="text-ink-3">Carcassa</dt>
                <dd className="code text-[18px]">{fmtKg(v.bonifica.residualKg)} <span className="font-sans text-sm text-ink-3">· EER 16 01 06</span></dd>
              </dl>
            ) : (
              <div className="flex flex-wrap items-center justify-between gap-3 p-4">
                <p className="text-[15px] text-ink-2">Da fare prima dello smontaggio: liquidi, batteria, airbag, catalizzatore, pneumatici.</p>
                <ButtonLink href={`/veicoli/${v.id}/bonifica`} size="sm"><Leaf className="size-4" aria-hidden /> Registra bonifica</ButtonLink>
              </div>
            )}
          </Panel>

          <div id="pratica">
            <PraticaPanel v={v} />
          </div>

          <Panel title="Storico veicolo">
            <ul className="divide-y divide-hair-soft text-[15px]">
              {history.slice(0, 8).map((e) => (
                <li key={e.id} className="px-4 py-2.5">
                  <span className="font-semibold">{e.action}</span>
                  {e.detail && <span className="text-ink-2"> · {e.detail}</span>}
                  <span className="block text-sm text-ink-3">{dateIt(e.at, true)} · {e.user}</span>
                </li>
              ))}
            </ul>
          </Panel>
        </div>

        <div className="space-y-6">
          <Panel title={`Ricambi originati · ${parts.length}`}>
            {parts.length === 0 ? (
              <Empty title="Nessun ricambio ancora catalogato">Avvia lo smontaggio per catalogare i pezzi dal telefono.</Empty>
            ) : (
              <ul className="divide-y divide-hair-soft">
                {parts.map((p) => (
                  <li key={p.id}>
                    <PartRow part={p} />
                  </li>
                ))}
              </ul>
            )}
          </Panel>
          <Panel title="Analisi recupero vs scorte">
            <RecoveryList vehicle={v} addHref={(t) => `/campo/${v.id}/nuovo?tipo=${t}`} />
          </Panel>
        </div>
      </div>
    </div>
  );
}
