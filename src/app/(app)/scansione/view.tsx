"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowDownToLine, ArrowLeftRight, ArrowUpFromLine, Euro, ScanLine, Trash2, Undo2, VideoOff, X } from "lucide-react";
import { useStore } from "@/lib/store";
import { openOrderFor } from "@/lib/logic";
import { locToString, onLabel, parseShelf, shelfCode } from "@/lib/warehouse";
import { Button, ButtonLink, Notice, PageTitle } from "@/components/ui";
import type { Location, Order, Part } from "@/lib/types";

type Detector = { detect: (src: HTMLVideoElement) => Promise<{ rawValue: string }[]> };
type DetectorClass = { new (o: { formats: string[] }): Detector; getSupportedFormats?: () => Promise<string[]> };
const FORMATS = ["qr_code", "code_128"];

// Lettore dei codici: quello del browser se c'è (Chrome su Android), altrimenti il nostro
// (ZXing in WebAssembly, servito dal gestionale stesso: funziona su iPhone e senza internet).
let ponyfillReady = false;
async function getDetector(): Promise<{ det: Detector; native: boolean }> {
  const Native = (window as unknown as { BarcodeDetector?: DetectorClass }).BarcodeDetector;
  if (Native) {
    try {
      const f = (await Native.getSupportedFormats?.()) ?? FORMATS;
      if (FORMATS.every((x) => f.includes(x))) return { det: new Native({ formats: FORMATS }), native: true };
    } catch {}
  }
  const mod = await import("barcode-detector/ponyfill");
  if (!ponyfillReady) {
    mod.prepareZXingModule({ overrides: { locateFile: (path: string, prefix: string) => (path.endsWith(".wasm") ? "/zxing/zxing_reader.wasm" : prefix + path) } });
    ponyfillReady = true;
  }
  return { det: new mod.BarcodeDetector({ formats: FORMATS as never }), native: false };
}

// Dal QR arriva l'URL o l'ID completo; a mano si scrive spesso abbreviato ("r-2389", "2389", "R2389")
function extractId(raw: string) {
  const s = raw.toUpperCase().trim();
  const full = s.match(/R-\d{6}/);
  if (full) return full[0];
  const short = s.match(/^R?-?\s*(\d{1,6})$/);
  return short ? `R-${short[1].padStart(6, "0")}` : undefined;
}

// Pezzo letto per primo: si sceglie cosa farne (spostarlo, venderlo, scartarlo); scaffale letto per primo: si preleva
type PartMode = "choose" | "move" | "scrap";
type Pending = { kind: "part"; part: Part; mode: PartMode } | { kind: "shelf"; loc: Location };
const SCRAP_REASONS = ["Rotto o danneggiato", "Invendibile", "Fermo da troppo tempo", "Non conforme"];
type Outcome = { tone: "ok" | "warn"; verb?: "carico" | "scarico" | "scarto"; title: string; detail?: string; undo?: () => void; sell?: string; load?: { label: string; run: () => void }; rottami?: boolean };

// Lo scaffale scansionato resta attivo per prendere più pezzi di fila, ma non per sempre:
// chi torna dopo con un pezzo in mano da mettere via non deve trovarsi in modalità prelievo.
const SHELF_IDLE_MS = 2 * 60 * 1000;

// Pezzo → scaffale = lo metto lì (carico). Scaffale → pezzo = lo prendo (scarico).
// La stessa logica vale con la fotocamera, con la pistola laser o scrivendo i codici a mano.
export default function Scansione() {
  const s = useStore();
  const router = useRouter();
  const [reason, setReason] = useState("");
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const lastRef = useRef<{ raw: string; at: number }>({ raw: "", at: 0 });
  const [camera, setCamera] = useState<"off" | "starting" | "on" | "insecure" | "unsupported" | "denied">("off");
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
    // Già su questo ripiano (anche dentro un suo contenitore): resta dov'è, il contenitore non si perde
    if (prev && onLabel(prev, loc)) {
      setOutcome({
        tone: "ok",
        title: `${p.id} è già qui`,
        detail: prev.contenitore && !loc.contenitore ? `In ${locToString(prev)}: contenitore ${prev.contenitore} di questo ripiano. Non cambia niente.` : `In ${locToString(prev)}. Non cambia niente.`,
      });
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

  // Vendi: se il pezzo è in un ordine si preleva per quell'ordine, altrimenti si preleva e si apre il banco
  function vendi(p: Part) {
    setPending(null);
    const order = openOrderFor(p.id, s.orders);
    if (order) {
      if (p.location) scarico(p, p.location, true);
      else setOutcome({ tone: "ok", title: `${p.id} è già fuori dallo scaffale`, detail: `Ordine ${order.id} · ${order.customer}` });
      return;
    }
    if (p.location) s.pickPart(p.id, "per la vendita al banco");
    router.push(`/vendite?pezzo=${p.id}`);
  }

  function scarta(p: Part, reason: string) {
    const prev = { status: p.status, location: p.location, listing: p.listing };
    const r = s.scrapPart(p.id, reason);
    setPending(null);
    if (!r.ok) {
      setOutcome({ tone: "warn", title: r.error });
      return;
    }
    setOutcome({
      tone: "ok",
      verb: "scarto",
      title: `${p.id} nei rottami`,
      detail: `${prev.location ? `Tolto da ${locToString(prev.location)} · ` : ""}${reason}. Portalo nell'area rottami: si vende a peso con il prossimo ritiro.`,
      undo: () => s.unscrapPart(p.id, prev),
      rottami: true,
    });
  }

  function handle(raw: string) {
    setError("");
    const active = pending && (pending.kind === "part" || Date.now() - pendingAt.current < SHELF_IDLE_MS) ? pending : null;
    pendingAt.current = Date.now();
    const loc = parseShelf(raw, s.warehouses);
    if (loc) {
      if (active?.kind === "part" && active.mode !== "scrap") carico(active.part, loc);
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
        setPending({ kind: "part", part: p, mode: p.status === "venduto" || p.status === "scartato" ? "move" : "choose" });
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
    // La fotocamera nel browser si apre solo da un indirizzo sicuro (https) o dal computer stesso
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setCamera(window.isSecureContext ? "unsupported" : "insecure");
      return;
    }
    setCamera("starting");
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
    } catch {
      setCamera("denied");
      return;
    }
    let reader: Awaited<ReturnType<typeof getDetector>>;
    try {
      reader = await getDetector();
    } catch {
      stream.getTracks().forEach((t) => t.stop());
      setCamera("unsupported");
      return;
    }
    streamRef.current = stream;
    setCamera("on");
    const video = videoRef.current!;
    video.srcObject = stream;
    await video.play().catch(() => undefined);
    const loop = async () => {
      if (!streamRef.current?.active) return;
      try {
        const r = video.readyState >= 2 ? await reader.det.detect(video) : [];
        const raw = r[0]?.rawValue;
        // Lo stesso codice inquadrato di continuo conta una volta sola
        if (raw && (raw !== lastRef.current.raw || Date.now() - lastRef.current.at > 2500)) {
          lastRef.current = { raw, at: Date.now() };
          if (handleRef.current(raw)) navigator.vibrate?.(60);
        }
      } catch {}
      // Il lettore del browser regge ogni fotogramma; il nostro legge circa 6 volte al secondo per non scaldare il telefono
      if (reader.native) requestAnimationFrame(loop);
      else setTimeout(loop, 160);
    };
    loop();
  }

  // Uscendo dalla pagina la fotocamera si spegne; tornando si riaccende col pulsante (non resta un riquadro nero)
  useEffect(
    () => () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      setCamera((c) => (c === "on" || c === "starting" ? "off" : c));
    },
    [],
  );

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
            {camera === "starting" && <p className="text-[17px] font-semibold">Apro la fotocamera…</p>}
            {(camera === "unsupported" || camera === "denied" || camera === "insecure") && (
              <>
                <VideoOff className="size-10" aria-hidden />
                <p className="max-w-xs">
                  {camera === "insecure"
                    ? "Il telefono apre la fotocamera solo se il gestionale è aperto da un indirizzo sicuro (https://…). Intanto scrivi il codice qui sotto o usa la pistola laser."
                    : camera === "denied"
                      ? "Accesso alla fotocamera negato. Consentilo nelle impostazioni del browser, oppure scrivi il codice stampato sotto il QR."
                      : "Questo browser non riesce a leggere i codici dalla fotocamera. Scrivi il codice qui sotto o usa la pistola laser."}
                </p>
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
          {pending.kind === "part" && pending.mode === "choose" && <PartChoices part={pending.part} orders={s.orders} onMove={() => setPending({ ...pending, mode: "move" })} onSell={() => vendi(pending.part)} onScrap={() => { setReason(""); setPending({ ...pending, mode: "scrap" }); }} />}
          {pending.kind === "part" && pending.mode === "scrap" && (
            <div className="mx-4 mt-3">
              <p className="text-[17px] font-semibold">Perché lo scarti?</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {SCRAP_REASONS.map((r) => (
                  <button key={r} onClick={() => setReason(r)} aria-pressed={reason === r} className={`min-h-11 rounded-md border-2 px-3 font-semibold ${reason === r ? "border-danger bg-danger text-white" : "border-hair bg-label text-ink hover:border-danger"}`}>
                    {r}
                  </button>
                ))}
              </div>
              <input className="field mt-2" placeholder="Altro motivo (facoltativo)" value={SCRAP_REASONS.includes(reason) ? "" : reason} onChange={(e) => setReason(e.target.value)} aria-label="Altro motivo dello scarto" />
              <div className="mt-3 flex flex-wrap gap-2">
                <Button variant="danger" disabled={!reason.trim()} onClick={() => scarta(pending.part, reason.trim())}>
                  <Trash2 className="size-5" aria-hidden /> Metti nei rottami
                </Button>
                <Button variant="quiet" onClick={() => setPending({ ...pending, mode: "choose" })}>Indietro</Button>
              </div>
            </div>
          )}
          {(pending.kind === "shelf" || pending.mode === "move") && (
            <p className="mx-4 mt-3 flex items-center gap-2 rounded bg-band-tint px-3 py-2.5 text-[17px] font-semibold text-band-deep">
              {pending.kind === "part" ? <ArrowDownToLine className="size-5 shrink-0" aria-hidden /> : <ArrowUpFromLine className="size-5 shrink-0" aria-hidden />}
              {pending.kind === "part"
                ? pending.part.status === "venduto" || pending.part.status === "scartato"
                  ? `È ${pending.part.status}: non va a scaffale`
                  : pending.part.location
                    ? "Ora scansiona lo scaffale dove lo metti"
                    : "Ora scansiona lo scaffale dove lo lasci"
                : "Ora scansiona il pezzo che prendi"}
            </p>
          )}
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
          {outcome.verb && <p className={`code text-[13px] font-bold uppercase tracking-wide ${outcome.tone === "ok" ? "text-ok" : "text-warn"}`}>{outcome.verb === "carico" ? "Messo a scaffale" : outcome.verb === "scarto" ? "Scartato" : "Preso dallo scaffale"}</p>}
          <p className="code text-[24px] font-bold leading-tight">{outcome.title}</p>
          {outcome.detail && <p className="mt-0.5 text-ink-2">{outcome.detail}</p>}
          {(outcome.undo || outcome.sell || outcome.load || outcome.rottami) && (
            <div className="mt-3 flex flex-wrap gap-2">
              {outcome.rottami && <ButtonLink href="/rottami" variant="secondary">Area rottami</ButtonLink>}
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

// Tre scelte grandi per il pezzo appena scansionato. Spostare resta anche la via rapida: si scansiona subito lo scaffale nuovo.
function PartChoices({ part, orders, onMove, onSell, onScrap }: { part: Part; orders: Order[]; onMove: () => void; onSell: () => void; onScrap: () => void }) {
  const order = openOrderFor(part.id, orders);
  const sellable = !!order || part.status === "disponibile";
  const sellNote = order ? `per ${order.id}` : sellable ? "al banco" : `è ${part.status}`;
  const scrapNote = part.status === "riservato" ? "è in un ordine" : "nei rottami";
  const big = "flex min-h-[88px] flex-col items-center justify-center gap-1 rounded-md border-2 px-2 text-center font-semibold disabled:cursor-not-allowed disabled:opacity-40";
  return (
    <div className="mx-4 mt-3">
      <p className="text-[17px] font-semibold">Cosa fai con questo pezzo?</p>
      <div className="mt-2 grid grid-cols-3 gap-2">
        <button onClick={onMove} className={`${big} border-band bg-band text-white hover:bg-band-deep`}>
          <ArrowLeftRight className="size-6" aria-hidden />
          <span className="text-[17px]">{part.location ? "Sposta" : "Metti a posto"}</span>
          <span className="text-[12px] font-medium opacity-80">{part.location ? "altro scaffale" : "su uno scaffale"}</span>
        </button>
        <button onClick={onSell} disabled={!sellable} className={`${big} border-hair bg-label text-ink hover:border-band`}>
          <Euro className="size-6 text-band" aria-hidden />
          <span className="text-[17px]">Vendi</span>
          <span className="text-[12px] font-medium text-ink-3">{sellNote}</span>
        </button>
        <button onClick={onScrap} disabled={part.status === "riservato"} className={`${big} border-hair bg-label text-ink hover:border-danger`}>
          <Trash2 className="size-6 text-danger" aria-hidden />
          <span className="text-[17px]">Scarta</span>
          <span className="text-[12px] font-medium text-ink-3">{scrapNote}</span>
        </button>
      </div>
      {part.location && <p className="mt-2 text-sm text-ink-2">Per spostarlo puoi anche scansionare subito lo scaffale nuovo.</p>}
    </div>
  );
}
