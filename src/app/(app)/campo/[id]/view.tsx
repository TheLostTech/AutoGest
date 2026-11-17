"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect } from "react";
import { Camera, ChevronLeft } from "lucide-react";
import { useStore } from "@/lib/store";
import { ButtonLink, Button, Empty, Panel, Plate } from "@/components/ui";
import { RecoveryList } from "@/components/RecoveryList";
import { PartRow } from "@/components/PartRow";

export default function SmontaggioVeicolo() {
  const { id } = useParams<{ id: string }>();
  const v = useStore((s) => s.vehicles.find((x) => x.id === id));
  const allParts = useStore((s) => s.parts);
  const { updateVehicle, setActiveVehicle } = useStore();
  const parts = allParts.filter((p) => p.vehicleId === id);

  // Aprire la pagina rende il veicolo quello "attivo" su questo dispositivo, ma non cambia il suo stato:
  // lo smontaggio si avvia con il pulsante (o con il primo pezzo catalogato)
  useEffect(() => {
    if (!v) return;
    setActiveVehicle(v.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [v?.id]);

  if (!v) return <Empty title={`Veicolo ${id} non trovato`} />;

  return (
    <div className="mx-auto max-w-2xl">
      <header className="-mx-4 -mt-5 mb-5 bg-band px-4 pb-5 pt-3 text-white md:mx-0 md:mt-0 md:rounded-md md:px-5">
        <Link href="/campo" className="-ml-1 inline-flex min-h-10 items-center gap-1 text-[15px] font-semibold text-white/85">
          <ChevronLeft className="size-5" aria-hidden />
          Cambia veicolo
        </Link>
        <div className="code text-[64px] font-bold leading-[0.88]">{v.id}</div>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Plate plate={v.plate} />
          <span className="text-[18px] font-semibold">{v.make} {v.model}</span>
        </div>
        <div className="mt-1 text-[15px] text-white/80">
          {v.version} · {v.year} · pratica <span className="code font-semibold text-white">{v.dossier.number || "da registrare"}</span>
        </div>
      </header>

      {!v.bonifica && (
        <Link href={`/veicoli/${v.id}/bonifica`} className="mb-5 flex items-center justify-between gap-3 rounded-md bg-warn-bg px-4 py-3 font-semibold text-warn">
          <span>Bonifica non ancora registrata: falla prima di smontare</span>
          <span className="shrink-0 underline">Bonifica</span>
        </Link>
      )}

      {/* Stato dello smontaggio, con il passo successivo esplicito */}
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-md border border-hair bg-label px-4 py-3">
        <span className="text-[15px]">
          Smontaggio: <b>{v.work === "accettato" ? "non avviato" : v.work === "in smontaggio" ? "in corso" : "finito"}</b>
        </span>
        {v.work === "accettato" && (
          <Button size="sm" disabled={!v.bonifica} onClick={() => updateVehicle(v.id, { work: "in smontaggio" }, "Smontaggio avviato")}>
            Avvia smontaggio
          </Button>
        )}
        {v.work === "in smontaggio" && (
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              if (confirm(`Chiudere lo smontaggio di ${v.id}? La carcassa resta nel registro rifiuti fino al formulario di uscita.`)) updateVehicle(v.id, { work: "smontato" }, "Smontaggio finito", `${parts.length} pezzi catalogati`);
            }}
          >
            Smontaggio finito
          </Button>
        )}
        {v.work === "smontato" && (
          <Button size="sm" variant="quiet" onClick={() => updateVehicle(v.id, { work: "in smontaggio" }, "Smontaggio riaperto")}>
            Riapri smontaggio
          </Button>
        )}
      </div>

      <Panel title="Cosa recuperare">
        <RecoveryList vehicle={v} addHref={v.work === "smontato" ? undefined : (t) => `/campo/${v.id}/nuovo?tipo=${t}`} />
      </Panel>

      <Panel title={`Catalogati da questo veicolo · ${parts.length}`} className="mt-5">
        {parts.length === 0 ? (
          <Empty title="Ancora nessun pezzo">Premi «Aggiungi pezzo» e inizia dalla foto.</Empty>
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

      {v.work !== "smontato" && (
        <div className="mt-5 text-center">
          <Button variant="quiet" onClick={() => confirm(`Chiudere lo smontaggio di ${v.id}?`) && updateVehicle(v.id, { work: "smontato" }, "Smontaggio concluso", `${parts.length} ricambi catalogati`)}>
            Chiudi smontaggio del veicolo
          </Button>
        </div>
      )}

      {v.work !== "smontato" && (
        <>
          <div className="h-20 md:hidden" aria-hidden />
          {/* Azione primaria sempre a portata di pollice */}
          <div className="fixed inset-x-0 bottom-[calc(64px+env(safe-area-inset-bottom))] z-20 px-4 pb-3 md:static md:mt-6 md:px-0">
            <ButtonLink href={`/campo/${v.id}/nuovo`} size="lg" className="w-full shadow-[0_8px_24px_-8px_rgb(18_64_168/0.6)] md:shadow-none">
              <Camera className="size-6" aria-hidden />
              Aggiungi pezzo
            </ButtonLink>
          </div>
        </>
      )}
    </div>
  );
}
