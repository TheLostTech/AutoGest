"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ArrowDownToLine, ArrowUpFromLine, ScanLine, Undo2, VideoOff, X } from "lucide-react";
import { useStore } from "@/lib/store";
import { openOrderFor } from "@/lib/logic";
import { locToString, onLabel, parseShelf, shelfCode } from "@/lib/warehouse";
import { Button, ButtonLink, Notice, PageTitle } from "@/components/ui";
import type { Location, Part } from "@/lib/types";

type Detector = { detect: (src: HTMLVideoElement) => Promise<{ rawValue: string }[]> };

// Dal QR arriva l'URL o l'ID completo; a mano si scrive spesso abbreviato ("r-2389", "2389", "R2389")
function extractId(raw: string) {
  const s = raw.toUpperCase().trim();
  const full = s.match(/R-\d{6}/);
  if (full) return full[0];
  const short = s.match(/^R?-?\s*(\d{1,6})$/);
  return short ? `R-${short[1].padStart(6, "0")}` : undefined;
}

type Pending = { kind: "part"; part: Part } | { kind: "shelf"; loc: Location };
type Outcome = { tone: "ok" | "warn"; verb?: "carico" | "scarico"; title: string; detail?: string; undo?: () => void; sell?: string; load?: { label: string; run: () => void } };

// Lo scaffale scansionato resta attivo per prendere più pezzi di fila, ma non per sempre:
// chi torna dopo con un pezzo in mano da mettere via non deve trovarsi in modalità prelievo.
const SHELF_IDLE_MS = 2 * 60 * 1000;

// Pezzo → scaffale = lo metto lì (carico). Scaffale → pezzo = lo prendo (scarico).
// La stessa logica vale con la fotocamera, con la pistola laser o scrivendo i codici a mano.
export default function Scansione() {
  const s = useStore();
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const lastRef = useRef<{ raw: string; at: number }>({ raw: "", at: 0 });
  const [camera, setCamera] = useState<"off" | "on" | "unsupported" | "denied">("off");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState<Pending | null>(null);
  const pendingAt = useRef(0);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [conflict, setConflict] = useState<{ part: Part; loc: Location } | null>(null);

  const findPart = (raw: string) => {
    const id = extractId(raw);
    const legacy = raw.trim().toUpperCase();
    return s.parts.find((x) => x.id === id) ?? s.parts.find((x) => x.legacyCode && x.legacyCode === legacy);
  };

  function carico(p: Part, loc: Location) {
    setPending(null);
    if (p.status === "venduto" || p.status === "scartato") {
      setOutcome({ tone: "warn", title: `${p.id} è ${p.status}: non va a scaffale` });
      return;
    }
    const prev = p.location;
    if (prev && locToString(prev) === locToString(loc)) {
      setOutcome({ tone: "ok", verb: "carico", title: `${p.id} è già in ${shelfCode(loc)}` });
      return;
    }
    s.setLocation(p.id, loc);
    setOutcome({
      tone: "ok",
      verb: "carico",
      title: `${p.id} messo in ${shelfCode(loc)}`,
      detail: prev ? `Spostato da ${locToString(prev)} · ${p.description}` : p.description,
      undo: () => (prev ? s.setLocation(p.id, prev) : s.pickPart(p.id, "scansione annullata")),
    });
  }

  function scarico(p: Part, loc: Location, force = false) {
    setConflict(null);
    if (!p.location) {
      // Pezzo in mano e scaffale davanti: con ogni probabilità lo si vuole mettere qui
      setOutcome({
        tone: "warn",
        title: `${p.id} non risulta su nessuno scaffale`,
        detail: "Se lo stai mettendo a posto, registralo qui.",
        load: p.status === "venduto" || p.status === "scartato" ? undefined : { label: `Mettilo in ${shelfCode(loc)}`, run: () => carico(p, loc) },
      });
      return;
    }
    if (!force && !onLabel(p.location, loc)) {
      setConflict({ part: p, loc });
      return;
    }
    const prev = p.location;
    const order = openOrderFor(p.id, s.orders);
    s.pickPart(p.id, order ? `per ${order.id}` : undefined);
    const toDeliver = order && (order.channel === "banco" || order.delivery === "ritiro") ? "da consegnare" : "da spedire";
    setOutcome({
      tone: "ok",
      verb: "scarico",
      title: `${p.id} prelevato da ${locToString(prev)}`,
      detail: order
        ? `Ordine ${order.id} · ${order.customer} · ${order.status === "pagato" ? toDeliver : "in attesa di pagamento"}`
        : p.status === "disponibile"
          ? "Non è ancora venduto: vendilo al banco, oppure rimettilo a scaffale."
          : p.description,
      undo: () => s.setLocation(p.id, prev),
      sell: !order && p.status === "disponibile" ? p.id : undefined,
    });
  }

  function handle(raw: string) {
    setError("");
    const active = pending && (pending.kind === "part" || Date.now() - pendingAt.current < SHELF_IDLE_MS) ? pending : null;
    pendingAt.current = Date.now();
    const loc = parseShelf(raw, s.warehouses);
    if (loc) {
      if (active?.kind === "part") carico(active.part, loc);
      else {
        setPending({ kind: "shelf", loc });
        setOutcome(null);
        setConflict(null);
      }
      return true;
    }
    const p = findPart(raw);
    if (p) {
      if (active?.kind === "shelf") scarico(p, active.loc); // lo scaffale resta: si possono prendere altri pezzi
      else {
        setPending({ kind: "part", part: p });
        setOutcome(null);
        setConflict(null);
      }
      return true;
    }
    setError(`Codice «${raw.trim()}» non riconosciuto: né un ricambio né uno scaffale.`);
    return false;
  }

  // Il ciclo della fotocamera chiama sempre la versione aggiornata (lo stato cambia a ogni scansione)
  const handleRef = useRef(handle);
  useEffect(() => {
    handleRef.current = handle;
  });

  async function start() {
    setError("");
    const BD = (window as unknown as { BarcodeDetector?: new (o: { formats: string[] }) => Detector }).BarcodeDetector;
    if (!BD || !navigator.mediaDevices) {
      setCamera("unsupported");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      streamRef.current = stream;
      setCamera("on");
      const video = videoRef.current!;
      video.srcObject = stream;
      await video.play();
      const det = new BD({ formats: ["qr_code", "code_128"] });
      const loop = async () => {
        if (!streamRef.current?.active) return;
        try {
          const r = await det.detect(video);
          const raw = r[0]?.rawValue;
          // Lo stesso codice inquadrato di continuo conta una volta sola
          if (raw && (raw !== lastRef.current.raw || Date.now() - lastRef.current.at > 2500)) {
            lastRef.current = { raw, at: Date.now() };
            if (handleRef.current(raw)) navigator.vibrate?.(60);
          }
        } catch {}
        requestAnimationFrame(loop);
      };
      loop();
    } catch {
      setCamera("denied");
    }
  }

  useEffect(() => () => streamRef.current?.getTracks().forEach((t) => t.stop()), []);

  // Lo scaffale attivo sparisce dallo schermo quando scade (ogni prelievo riparte il conto)
  useEffect(() => {
    if (pending?.kind !== "shelf") return;
    const t = setTimeout(() => setPending((x) => (x?.kind === "shelf" ? null : x)), SHELF_IDLE_MS);
    return () => clearTimeout(t);
  }, [pending, outcome]);

  const shelfParts = pending?.kind === "shelf" ? s.parts.filter((p) => onLabel(p.location, pending.loc) && p.status !== "scartato") : [];
  const samplesParts = s.parts.filter((p) => p.status === "disponibile" && p.location).slice(0, 3);
  const samplesShelves = [...new Set(samplesParts.map((p) => shelfCode({ ...p.location!, contenitore: undefined })))];

  return (
    <div className="mx-auto max-w-xl">
      <PageTitle title="Scansiona" sub="Pezzo e poi scaffale: lo metti a posto. Scaffale e poi pezzo: lo prendi. Funziona anche scrivendo i codici a mano." />

      <div className="relative aspect-[4/3] overflow-hidden rounded-md bg-ink">
        <video ref={videoRef} className={`size-full object-cover ${camera === "on" ? "" : "hidden"}`} playsInline muted />
        {camera === "on" && <div className="pointer-events-none absolute inset-[18%] rounded-lg border-4 border-white/90" aria-hidden />}
        {camera !== "on" && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 p-6 text-center text-white">
            {camera === "off" && (
              <Button size="lg" onClick={start} className="bg-white text-band hover:bg-band-tint">
                <ScanLine className="size-6" aria-hidden /> Attiva fotocamera
              </Button>
            )}
            {(camera === "unsupported" || camera === "denied") && (
              <>
                <VideoOff className="size-10" aria-hidden />
                <p className="max-w-xs">{camera === "unsupported" ? "Questo browser non legge i codici dalla fotocamera. Su smartphone Android con Chrome funziona; qui puoi scrivere i codici." : "Accesso alla fotocamera negato. Scrivi il codice stampato sotto il QR."}</p>
              </>
            )}
          </div>
        )}
      </div>

      {/* Primo codice letto: cosa aspettiamo adesso */}
      {pending && (
        <section className="mt-4 rounded-md border-2 border-band bg-label" aria-live="polite">
          <div className="flex items-start justify-between gap-3 px-4 pt-3">
            {pending.kind === "part" ? (
              <div className="min-w-0">
                <p className="code text-[26px] font-bold leading-none">{pending.part.id}</p>
                <p className="truncate">{pending.part.description}</p>
                <p className="mt-0.5 text-sm text-ink-2">{pending.part.location ? `Ora in ${locToString(pending.part.location)}` : "Senza posizione"}</p>
              </div>
            ) : (
              <div className="min-w-0">
                <p className="code text-[26px] font-bold leading-none">{shelfCode(pending.loc)}</p>
                <p className="text-sm text-ink-2">{shelfParts.length === 0 ? "Nessun pezzo registrato qui" : `${shelfParts.length} ${shelfParts.length === 1 ? "pezzo registrato" : "pezzi registrati"} qui`}</p>
              </div>
            )}
            <button onClick={() => setPending(null)} className="grid size-10 shrink-0 place-items-center rounded text-ink-3 hover:bg-carton hover:text-ink" aria-label="Lascia perdere">
              <X className="size-5" aria-hidden />
            </button>
          </div>
          <p className="mx-4 mt-3 flex items-center gap-2 rounded bg-band-tint px-3 py-2.5 text-[17px] font-semibold text-band-deep">
            {pending.kind === "part" ? <ArrowDownToLine className="size-5 shrink-0" aria-hidden /> : <ArrowUpFromLine className="size-5 shrink-0" aria-hidden />}
            {pending.kind === "part" ? "Ora scansiona lo scaffale dove lo lasci" : "Ora scansiona il pezzo che prendi"}
          </p>
          {pending.kind === "shelf" && shelfParts.length > 0 && (
            <ul className="mx-4 mt-2 flex flex-wrap gap-1.5">
              {shelfParts.map((p) => (
                <li key={p.id}>
                  <button onClick={() => handle(p.id)} className="code rounded border border-hair px-2 py-1 text-[15px] font-bold text-band hover:border-band" title={p.description}>
                    {p.id}
                    {p.location?.contenitore && <span className="ml-1 font-semibold text-ink-3">c.{p.location.contenitore}</span>}
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div className="flex flex-wrap gap-2 p-4 pt-3">
            {pending.kind === "part" ? (
              <ButtonLink href={`/ricambi/${pending.part.id}`} variant="quiet" size="sm">Apri la scheda</ButtonLink>
            ) : (
              <ButtonLink href={`/magazzino?${new URLSearchParams({ mag: pending.loc.mag, c: pending.loc.corsia, s: pending.loc.scaffale, r: pending.loc.ripiano })}`} variant="quiet" size="sm">
                Vedi sulla mappa
              </ButtonLink>
            )}
          </div>
        </section>
      )}

      {/* Scaffale diverso da quello registrato: si decide, non si indovina */}
      {conflict && (
        <section className="mt-4 rounded-md border-2 border-warn bg-warn-bg px-4 py-3" aria-live="assertive">
          <p className="text-[17px] font-semibold text-ink">
            <span className="code">{conflict.part.id}</span> risulta in <span className="code">{locToString(conflict.part.location)}</span>, non in <span className="code">{shelfCode(conflict.loc)}</span>.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button onClick={() => scarico(conflict.part, conflict.loc, true)}>Prelevalo comunque</Button>
            <Button variant="quiet" onClick={() => setConflict(null)}>Annulla</Button>
          </div>
        </section>
      )}

      {/* Esito: grande, con Annulla finché non si scansiona altro */}
      {outcome && (
        <section className={`mt-4 rounded-md border-2 px-4 py-3 ${outcome.tone === "ok" ? "border-ok bg-ok-bg" : "border-warn bg-warn-bg"}`} aria-live="polite">
          {outcome.verb && <p className={`code text-[13px] font-bold uppercase tracking-wide ${outcome.tone === "ok" ? "text-ok" : "text-warn"}`}>{outcome.verb === "carico" ? "Messo a scaffale" : "Preso dallo scaffale"}</p>}
          <p className="code text-[24px] font-bold leading-tight">{outcome.title}</p>
          {outcome.detail && <p className="mt-0.5 text-ink-2">{outcome.detail}</p>}
          {(outcome.undo || outcome.sell || outcome.load) && (
            <div className="mt-3 flex flex-wrap gap-2">
              {outcome.load && <Button onClick={outcome.load.run}>{outcome.load.label}</Button>}
              {outcome.sell && <ButtonLink href={`/vendite?pezzo=${outcome.sell}`}>Vendi al banco</ButtonLink>}
              {outcome.undo && (
                <Button
                  variant="quiet"
                  onClick={() => {
                    outcome.undo!();
                    setOutcome({ tone: "warn", title: "Annullato", detail: "La posizione è tornata com'era." });
                  }}
                >
                  <Undo2 className="size-4" aria-hidden /> Annulla
                </Button>
              )}
            </div>
          )}
        </section>
      )}

      <form
        className="mt-5 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (code.trim() && handle(code)) setCode("");
        }}
      >
        <input
          className="field code text-[22px] font-bold uppercase"
          placeholder={pending?.kind === "part" ? "Scaffale: 1/T01-103-B" : pending?.kind === "shelf" ? "Pezzo: R-002301" : "R-002301 o 1/T01-103-B"}
          value={code}
          onChange={(e) => setCode(e.target.value)}
          aria-label="Codice ricambio o scaffale"
          autoCapitalize="characters"
          autoComplete="off"
        />
        <Button type="submit">Invia</Button>
      </form>
      {error && <div className="mt-3"><Notice tone="danger">{error}</Notice></div>}

      <div className="mt-4 space-y-1 text-sm text-ink-3">
        <p>
          Ricambi di prova:{" "}
          {samplesParts.map((p) => (
            <button key={p.id} onClick={() => handle(p.id)} className="code mx-1 font-semibold text-band underline">{p.id}</button>
          ))}
        </p>
        <p>
          Scaffali di prova:{" "}
          {samplesShelves.map((c) => (
            <button key={c} onClick={() => handle(c)} className="code mx-1 font-semibold text-band underline">{c}</button>
          ))}
        </p>
        <p>
          Etichette per gli scaffali: <Link href="/etichette-scaffale" className="font-semibold text-band underline">stampale dalla mappa</Link>.
        </p>
      </div>

    </div>
  );
}
