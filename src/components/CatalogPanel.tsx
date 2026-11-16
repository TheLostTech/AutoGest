"use client";

import { useState } from "react";
import { BookOpen, CircleAlert, Loader2 } from "lucide-react";
import { useStore } from "@/lib/store";
import { lookupCatalog, platformLabel, type CatalogInfo } from "@/lib/partsdb";
import type { Part, Vehicle } from "@/lib/types";
import { Button, Field, Panel } from "./ui";

// Dati dal catalogo ricambi: costruttore, codice OE, intercambiabilità.
// La compatibilità diventa "verificata" solo quando l'operatore conferma che il codice sul pezzo coincide.
export function CatalogPanel({ part, vehicle }: { part: Part; vehicle?: Vehicle }) {
  const s = useStore();
  const [info, setInfo] = useState<CatalogInfo | null>(null);
  const [state, setState] = useState<"idle" | "loading" | "found" | "none">("idle");
  const [code, setCode] = useState(part.oem ?? "");

  async function search() {
    if (!vehicle) return;
    setState("loading");
    const r = await lookupCatalog(part.typeId, vehicle.platform, part.side);
    setInfo(r);
    setState(r ? "found" : "none");
  }

  const norm = (x: string) => x.replace(/[\s-]/g, "").toUpperCase();
  const matches = info && code && norm(code) === norm(info.oem);

  return (
    <Panel title="Catalogo ricambi e compatibilità">
      <div className="space-y-4 p-4">
        <dl className="grid grid-cols-[130px_1fr] gap-x-4 gap-y-2 text-[15px]">
          <dt className="text-ink-3">Costruttore</dt>
          <dd className="font-semibold">{part.manufacturer ?? "—"}</dd>
          <dt className="text-ink-3">Codice OE</dt>
          <dd className="code text-[18px] font-semibold">
            {part.oem ?? "—"}{" "}
            {part.oem && <span className={`font-sans text-sm font-semibold ${part.oemVerified ? "text-ok" : "text-warn"}`}>{part.oemVerified ? "letto sul pezzo e verificato" : "non verificato"}</span>}
          </dd>
          {part.legacyCode && (
            <>
              <dt className="text-ink-3">Codice precedente</dt>
              <dd className="code text-[17px]">{part.legacyCode} <span className="font-sans text-sm text-ink-3">dal magazzino migrato</span></dd>
            </>
          )}
        </dl>

        {part.compat?.verified ? (
          <div>
            <p className="text-sm font-semibold text-ok">Montabile su {part.compat.platforms.length} {part.compat.platforms.length === 1 ? "modello" : "modelli"} · {part.compat.source}</p>
            <ul className="mt-2 flex flex-wrap gap-1.5">
              {part.compat.platforms.map((pl) => (
                <li key={pl} className="rounded border border-hair bg-carton px-2 py-1 text-sm font-medium">{platformLabel(pl)}</li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="flex items-start gap-2 text-sm text-ink-2">
            <CircleAlert className="mt-0.5 size-4 shrink-0 text-warn" aria-hidden />
            Compatibilità non dichiarata: vale solo il veicolo di provenienza finché il codice non è verificato col catalogo.
          </p>
        )}

        {state === "idle" && (
          <Button variant="secondary" onClick={search} disabled={!vehicle}>
            <BookOpen className="size-5" aria-hidden /> {part.compat?.verified ? "Riapri scheda catalogo" : "Cerca nel catalogo ricambi"}
          </Button>
        )}
        {state === "loading" && <p className="flex items-center gap-2 font-semibold text-band"><Loader2 className="size-5 animate-spin" aria-hidden /> Ricerca nel catalogo…</p>}
        {state === "none" && <p className="text-sm font-semibold text-warn">Nessun risultato: piattaforma del veicolo non determinata.</p>}
        {state === "found" && info && (
          <div className="rounded-md border border-band/40 bg-band-tint/50 p-4">
            <p className="code text-[12px] font-semibold uppercase tracking-[0.14em] text-band-deep">{info.source}</p>
            <dl className="mt-2 grid grid-cols-[120px_1fr] gap-x-3 gap-y-1.5 text-[15px]">
              <dt className="text-ink-3">Codice OE atteso</dt>
              <dd className="code text-[20px] font-bold">{info.oem}</dd>
              <dt className="text-ink-3">Costruttore</dt>
              <dd className="font-semibold">{info.manufacturer}</dd>
              <dt className="text-ink-3">Produzione</dt>
              <dd className="code">{info.production}</dd>
              <dt className="text-ink-3">Nota</dt>
              <dd>{info.note}</dd>
            </dl>
            <p className="mt-3 text-sm font-semibold">Montabile su:</p>
            <ul className="mt-1 flex flex-wrap gap-1.5">
              {info.platforms.map((pl) => (
                <li key={pl} className="rounded border border-hair bg-label px-2 py-1 text-sm font-medium">{platformLabel(pl)}</li>
              ))}
            </ul>
            <div className="mt-4">
              <Field label="Codice letto sul pezzo" hint="Confronta con l'etichetta o la punzonatura del componente" error={code && !matches ? "Non coincide con il codice atteso: la compatibilità non verrà dichiarata" : undefined}>
                <input className="field code text-[18px] font-bold uppercase" value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder={info.oem} />
              </Field>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button
                disabled={!matches}
                onClick={() => {
                  s.updatePart(
                    part.id,
                    { oem: info.oem, oemVerified: true, manufacturer: info.manufacturer, compat: { platforms: info.platforms, source: info.source, verified: true, checkedAt: new Date().toISOString() } },
                    "Compatibilità verificata",
                    `${info.oem} · ${info.platforms.length} modelli`,
                  );
                  setState("idle");
                }}
              >
                Codice coincide: conferma
              </Button>
              <Button
                variant="secondary"
                onClick={() => {
                  s.updatePart(part.id, { oem: code || undefined, oemVerified: false, manufacturer: info.manufacturer, compat: undefined }, "Dati catalogo salvati senza verifica", code ? `codice letto ${code} ≠ ${info.oem}` : "codice illeggibile");
                  setState("idle");
                }}
              >
                Salva senza verificare
              </Button>
            </div>
          </div>
        )}
      </div>
    </Panel>
  );
}
