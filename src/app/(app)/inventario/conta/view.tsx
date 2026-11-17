"use client";

import Link from "next/link";
import { Suspense, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, Camera, Check, Loader2, Printer, X } from "lucide-react";
import { useStore } from "@/lib/store";
import { CONDITIONS, PART_TYPES, sidesFor, typeById } from "@/lib/catalog";
import { savePhoto, identifyFromPhoto } from "@/lib/services";
import { locLong, locToString, sameRipiano } from "@/lib/warehouse";
import { Button, Empty, Field, Notice, PartImage } from "@/components/ui";
import type { Condition, Location, Part } from "@/lib/types";

export default function Page() {
  return (
    <Suspense>
      <Conta />
    </Suspense>
  );
}

function Conta() {
  const sp = useSearchParams();
  const { warehouses, parts, closeCount } = useStore();
  const w = warehouses.find((x) => x.id === sp.get("mag"));
  const loc = { mag: w?.id ?? "", corsia: sp.get("c") ?? "", scaffale: sp.get("s") ?? "", ripiano: sp.get("r") ?? "" };
  const [mark, setMark] = useState<Record<string, boolean>>({});
  const [added, setAdded] = useState<string[]>([]);
  const [closed, setClosed] = useState<string | null>(null);

  if (!w || !loc.corsia || !loc.scaffale || !loc.ripiano) return <Empty title="Ripiano non trovato">Torna all&apos;inventario e scegli uno scaffale.</Empty>;
  const existing = parts.filter((p) => sameRipiano(p.location, loc.mag, loc.corsia, loc.scaffale, loc.ripiano) && p.status !== "venduto" && p.status !== "scartato" && !added.includes(p.id));
  const unchecked = existing.filter((p) => mark[p.id] === undefined).length;
  const found = existing.filter((p) => mark[p.id] === true).map((p) => p.id);
  const missing = existing.filter((p) => mark[p.id] === false).map((p) => p.id);
  const code = `${loc.mag}/${loc.corsia}-${loc.scaffale}-${loc.ripiano}`;
  const back = `/inventario/${encodeURIComponent(w.id)}`;

  if (closed)
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <Notice tone="ok">
          Ripiano <b className="code">{code}</b> contato ({closed}): {found.length + added.length} pezzi presenti, {added.length} nuovi catalogati
          {missing.length ? `, ${missing.length} non trovati e segnalati` : ""}.
        </Notice>
        <div className="flex flex-wrap gap-2">
          <Link href={back} className="inline-flex min-h-12 items-center rounded-md bg-band px-5 font-semibold text-white">Prossimo ripiano</Link>
          <Link href="/ricambi" className="inline-flex min-h-12 items-center rounded-md border border-hair bg-label px-5 font-semibold">Vedi i ricambi</Link>
        </div>
      </div>
    );

  return (
    <div className="mx-auto max-w-2xl">
      <Link href={back} className="mb-3 inline-flex items-center gap-1.5 text-[15px] font-semibold text-band">
        <ArrowLeft className="size-4" aria-hidden /> Mag. {w.id}
      </Link>
      <h1 className="code text-[44px] font-bold leading-none">{code}</h1>
      <p className="mt-1 mb-5 text-ink-2">{locLong(loc)}</p>

      {/* 1 · Appello dei pezzi già registrati su questo ripiano */}
      <section className="mb-6" aria-labelledby="registrati">
        <h2 id="registrati" className="code mb-2 text-[15px] font-bold uppercase tracking-wide text-ink-2">
          Già registrati qui · {existing.length}
        </h2>
        {existing.length === 0 ? (
          <p className="rounded-md border border-dashed border-hair bg-label px-4 py-4 text-ink-2">Nessun pezzo risulta su questo ripiano: cataloga quello che trovi.</p>
        ) : (
          <ul className="divide-y divide-hair-soft rounded-md border border-hair bg-label">
            {existing.map((p) => (
              <li key={p.id} className="flex items-center gap-3 px-3 py-2.5">
                <PartImage src={p.photos[0]} typeId={p.typeId} className="size-12 shrink-0 rounded bg-white [&>span]:hidden" />
                <span className="min-w-0 flex-1">
                  <span className="code block text-[17px] font-bold leading-none">{p.id}</span>
                  <span className="block truncate text-sm">{p.description}</span>
                  <span className="block text-[13px] text-ink-3">
                    {p.location?.contenitore ? `contenitore ${p.location.contenitore}` : "ripiano libero"}
                    {p.legacyCode ? ` · ${p.legacyCode}` : ""}
                  </span>
                </span>
                <span className="flex shrink-0 gap-1" role="group" aria-label={`${p.id} presente?`}>
                  <button
                    onClick={() => setMark((m) => ({ ...m, [p.id]: true }))}
                    aria-pressed={mark[p.id] === true}
                    className={`h-11 rounded-md px-3 text-[15px] font-semibold ${mark[p.id] === true ? "bg-ok text-white" : "border border-hair text-ink-2"}`}
                  >
                    C&apos;è
                  </button>
                  <button
                    onClick={() => setMark((m) => ({ ...m, [p.id]: false }))}
                    aria-pressed={mark[p.id] === false}
                    className={`h-11 rounded-md px-3 text-[15px] font-semibold ${mark[p.id] === false ? "bg-danger text-white" : "border border-hair text-ink-2"}`}
                  >
                    Non c&apos;è
                  </button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* 2 · Pezzi trovati qui e non ancora nel gestionale */}
      <section className="mb-6" aria-labelledby="nuovi">
        <h2 id="nuovi" className="code mb-2 text-[15px] font-bold uppercase tracking-wide text-ink-2">
          Trovati qui, da catalogare{added.length ? ` · ${added.length} fatti` : ""}
        </h2>
        {added.length > 0 && (
          <ul className="mb-3 divide-y divide-hair-soft rounded-md border border-ok/40 bg-ok-bg/40">
            {added.map((id) => {
              const p = parts.find((x) => x.id === id);
              return p ? <AddedRow key={id} p={p} /> : null;
            })}
          </ul>
        )}
        <AddFound key={added.length} loc={loc} contenitori={w.contenitori} categories={w.categories} onAdded={(id) => setAdded((xs) => [...xs, id])} />
      </section>

      {/* Chiusura del ripiano */}
      <div className="sticky bottom-[calc(72px+env(safe-area-inset-bottom))] z-20 flex items-center justify-between gap-3 rounded-md border border-hair bg-label p-3 shadow-[0_8px_24px_-12px_rgb(17_20_24/0.35)] md:bottom-4">
        <span className="text-sm text-ink-2">
          <b className="code text-[18px] text-ink">{found.length + added.length}</b> presenti · <b className="code text-[18px] text-ink">{missing.length}</b> mancanti
          {unchecked > 0 && <span className="block font-semibold text-warn">{unchecked} da spuntare</span>}
        </span>
        <Button disabled={unchecked > 0} onClick={() => setClosed(closeCount({ ...loc, found, missing, added }))}>
          Chiudi il ripiano
        </Button>
      </div>
    </div>
  );
}

function AddedRow({ p }: { p: Part }) {
  const printLabel = useStore((s) => s.printLabel);
  return (
    <li className="flex items-center gap-3 px-3 py-2.5">
      <Check className="size-5 shrink-0 text-ok" aria-hidden />
      <span className="min-w-0 flex-1">
        <span className="code block text-[17px] font-bold leading-none">{p.id}</span>
        <span className="block truncate text-sm">{p.description} · {locToString(p.location)}</span>
      </span>
      <button
        onClick={() => {
          printLabel(p.id);
          window.open(`/etichetta/${p.id}`, "_blank");
        }}
        className="inline-flex h-11 shrink-0 items-center gap-1.5 rounded-md border border-hair px-3 text-[15px] font-semibold"
      >
        <Printer className="size-4" aria-hidden /> {p.labelPrints ? "Ristampa" : "Etichetta"}
      </button>
    </li>
  );
}

type Origin = "pratica" | "veicolo" | "nessuna";

function AddFound({
  loc,
  contenitori,
  categories,
  onAdded,
}: {
  loc: Omit<Location, "contenitore">;
  contenitori: number;
  categories: string[];
  onAdded: (id: string) => void;
}) {
  const { vehicles, parts, addPart } = useStore();
  const fileRef = useRef<HTMLInputElement>(null);
  const [photos, setPhotos] = useState<string[]>([]);
  const [guess, setGuess] = useState<{ typeId: string; confidence: number }[] | null>(null);
  const [guessing, setGuessing] = useState(false);
  const [typeId, setTypeId] = useState("");
  const [side, setSide] = useState("");
  const [condition, setCondition] = useState<Condition | undefined>();
  const [box, setBox] = useState(contenitori ? "1" : "");
  // La provenienza resta tra un pezzo e l'altro: spesso sullo stesso ripiano ci sono pezzi della stessa auto
  const [origin, setOrigin] = useState<Origin>(() => (typeof window !== "undefined" && (sessionStorage.getItem("inv-origin") as Origin)) || "pratica");
  const [past, setPast] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem("inv-past") ?? "") as { number: string; plate: string; vin: string; model: string };
    } catch {
      return { number: "", plate: "", vin: "", model: "" };
    }
  });
  const [vehicleId, setVehicleId] = useState("");
  const [legacy, setLegacy] = useState("");
  const [oem, setOem] = useState("");
  const [price, setPrice] = useState("");
  const [tried, setTried] = useState(false);

  const candidates = PART_TYPES.filter((t) => !categories.length || categories.includes(t.category)).map((t) => t.id);
  const t = typeId ? typeById(typeId) : undefined;
  const knownPast = [...new Map(parts.filter((p) => p.pastDossier).map((p) => [p.pastDossier!.number, p.pastDossier!])).values()];
  const v = vehicles.find((x) => x.id === vehicleId);
  const originOk = origin === "nessuna" || (origin === "veicolo" ? !!v : past.number.trim().length >= 3);
  const dupLegacy = legacy.trim() && parts.find((p) => p.legacyCode?.toUpperCase() === legacy.trim().toUpperCase());
  const ok = !!t && !!condition && (!t.sided || !!side) && originOk && !dupLegacy;
  const model = origin === "veicolo" && v ? `${v.make} ${v.model}` : origin === "pratica" ? past.model.trim() : "";

  async function addPhotos(files: FileList | null) {
    if (!files?.length) return;
    const imgs = await Promise.all(Array.from(files).map((f) => savePhoto(f)));
    setPhotos((p) => [...p, ...imgs]);
    if (!guess && !typeId) {
      setGuessing(true);
      const r = await identifyFromPhoto(candidates.length ? candidates : PART_TYPES.map((x) => x.id));
      setGuessing(false);
      setGuess(r);
      setTypeId(r[0].typeId);
    }
  }

  function pickPast(number: string) {
    const k = knownPast.find((x) => x.number.toUpperCase() === number.trim().toUpperCase());
    setPast(k ? { number: k.number, plate: k.plate ?? "", vin: k.vin ?? "", model: k.model ?? "" } : { ...past, number });
  }

  function save() {
    setTried(true);
    if (!ok || !t || !condition) return;
    sessionStorage.setItem("inv-origin", origin);
    sessionStorage.setItem("inv-past", JSON.stringify(past));
    const id = addPart({
      vehicleId: origin === "veicolo" && v ? v.id : "",
      origin: "inventario",
      pastDossier:
        origin === "pratica"
          ? { number: past.number.trim().toUpperCase(), plate: past.plate.trim().toUpperCase() || undefined, vin: past.vin.trim().toUpperCase() || undefined, model: past.model.trim() || undefined }
          : undefined,
      typeId: t.id,
      description: `${t.name}${model ? ` ${model}` : ""}${side ? ` ${side.toLowerCase()}` : ""}`,
      condition,
      status: "bozza",
      side: side || undefined,
      oem: oem.trim().toUpperCase() || undefined,
      oemVerified: false,
      legacyCode: legacy.trim().toUpperCase() || undefined,
      price: price ? Number(price) : undefined,
      location: { ...loc, contenitore: contenitori ? box : undefined },
      photos,
      aiSuggested: guess ? { typeId: guess[0].typeId, confidence: guess[0].confidence, accepted: guess[0].typeId === t.id } : undefined,
    });
    onAdded(id);
  }

  return (
    <div className="space-y-4 rounded-md border border-hair bg-label p-4">
      {/* Foto e riconoscimento */}
      <input ref={fileRef} type="file" accept="image/*" capture="environment" multiple className="hidden" onChange={(e) => void addPhotos(e.target.files)} />
      {photos.length === 0 ? (
        <Button className="w-full" size="lg" onClick={() => fileRef.current?.click()}>
          <Camera className="size-6" aria-hidden /> Fotografa il pezzo
        </Button>
      ) : (
        <div className="flex gap-2 overflow-x-auto">
          {photos.map((src, i) => (
            <span key={i} className="relative shrink-0">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={src} alt={`Foto ${i + 1}`} className="size-24 rounded border border-hair-soft object-cover" />
              <button onClick={() => setPhotos((xs) => xs.filter((_, j) => j !== i))} className="absolute right-1 top-1 grid size-7 place-items-center rounded-full bg-ink/70 text-white" aria-label={`Togli foto ${i + 1}`}>
                <X className="size-4" aria-hidden />
              </button>
            </span>
          ))}
          <button onClick={() => fileRef.current?.click()} className="grid size-24 shrink-0 place-items-center rounded border border-dashed border-hair text-ink-3" aria-label="Aggiungi foto">
            <Camera className="size-6" aria-hidden />
          </button>
        </div>
      )}

      {guessing && <p className="flex items-center gap-2 font-semibold text-band"><Loader2 className="size-5 animate-spin" aria-hidden /> Riconosco il pezzo…</p>}
      {guess && (
        <div>
          <span className="mb-1.5 block text-sm font-semibold">Sembra…</span>
          <div className="flex flex-wrap gap-1.5">
            {guess.map((g) => (
              <button
                key={g.typeId}
                onClick={() => setTypeId(g.typeId)}
                aria-pressed={typeId === g.typeId}
                className={`h-11 rounded-full border px-4 text-[15px] font-semibold ${typeId === g.typeId ? "border-band bg-band text-white" : "border-hair bg-label text-ink"}`}
              >
                {typeById(g.typeId).name} <span className={typeId === g.typeId ? "text-white/80" : "text-ink-3"}>{Math.round(g.confidence * 100)}%</span>
              </button>
            ))}
          </div>
        </div>
      )}
      <Field label={guess ? "Oppure scegli la tipologia" : "Tipologia"} error={tried && !t ? "Scegli il tipo di pezzo" : undefined}>
        <select className="field" value={typeId} onChange={(e) => setTypeId(e.target.value)}>
          <option value="">Scegli…</option>
          {PART_TYPES.map((x) => <option key={x.id} value={x.id}>{x.name} · {x.category}</option>)}
        </select>
      </Field>

      <div className="grid gap-4 sm:grid-cols-2">
        {t?.sided && (
          <Field label="Lato" error={tried && !side ? "Indica il lato" : undefined}>
            <select className="field" value={side} onChange={(e) => setSide(e.target.value)}>
              <option value="">Scegli…</option>
              {sidesFor(t!.id).map((x) => <option key={x}>{x}</option>)}
            </select>
          </Field>
        )}
        {contenitori > 0 && (
          <Field label="Contenitore">
            <select className="field" value={box} onChange={(e) => setBox(e.target.value)}>
              {Array.from({ length: contenitori }, (_, i) => <option key={i} value={String(i + 1)}>{i + 1}</option>)}
            </select>
          </Field>
        )}
      </div>

      <div>
        <span className="mb-1.5 block text-sm font-semibold">Condizioni</span>
        <div className="grid grid-cols-4 gap-1.5">
          {(Object.keys(CONDITIONS) as Condition[]).map((c) => (
            <button
              key={c}
              onClick={() => setCondition(c)}
              aria-pressed={condition === c}
              className={`min-h-12 rounded-md border text-center ${condition === c ? "border-band bg-band text-white" : "border-hair bg-label"}`}
            >
              <span className="code block text-[20px] font-bold leading-none">{c}</span>
              <span className={`block text-[12px] ${condition === c ? "text-white/85" : "text-ink-3"}`}>{CONDITIONS[c].label}</span>
            </button>
          ))}
        </div>
        {tried && !condition && <span className="mt-1 block text-sm font-medium text-danger">Indica le condizioni</span>}
      </div>

      {/* Provenienza: tracciabilità anche per il magazzino preesistente */}
      <div>
        <span className="mb-1.5 block text-sm font-semibold">Provenienza</span>
        <div className="grid grid-cols-3 gap-1 rounded-md border border-hair bg-carton p-1" role="radiogroup" aria-label="Provenienza">
          {(
            [
              ["pratica", "Pratica passata"],
              ["veicolo", "Veicolo nel gestionale"],
              ["nessuna", "Non documentata"],
            ] as const
          ).map(([k, label]) => (
            <button key={k} role="radio" aria-checked={origin === k} onClick={() => setOrigin(k)} className={`min-h-11 rounded px-2 text-[14px] font-semibold leading-tight ${origin === k ? "bg-label text-ink shadow-sm" : "text-ink-2"}`}>
              {label}
            </button>
          ))}
        </div>
        {origin === "pratica" && (
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <Field label="Numero pratica o certificato" hint="Come nel vecchio archivio (Excel)" error={tried && past.number.trim().length < 3 ? "Inserisci il numero della pratica" : undefined}>
              <input className="field code uppercase" list="pratiche-passate" value={past.number} onChange={(e) => pickPast(e.target.value)} placeholder="Es. CR-2019-001234" />
              <datalist id="pratiche-passate">
                {knownPast.map((k) => <option key={k.number} value={k.number}>{[k.plate, k.model].filter(Boolean).join(" · ")}</option>)}
              </datalist>
            </Field>
            <Field label="Targa (se nota)">
              <input className="field code uppercase" value={past.plate} onChange={(e) => setPast({ ...past, plate: e.target.value })} />
            </Field>
            <Field label="Telaio (se noto)">
              <input className="field code uppercase" maxLength={17} value={past.vin} onChange={(e) => setPast({ ...past, vin: e.target.value })} />
            </Field>
            <Field label="Marca e modello">
              <input className="field" value={past.model} onChange={(e) => setPast({ ...past, model: e.target.value })} placeholder="Es. Fiat Punto" />
            </Field>
          </div>
        )}
        {origin === "veicolo" && (
          <div className="mt-3">
            <Field label="Veicolo d'origine" error={tried && !v ? "Scegli il veicolo" : undefined}>
              <select className="field" value={vehicleId} onChange={(e) => setVehicleId(e.target.value)}>
                <option value="">Scegli…</option>
                {vehicles.map((x) => <option key={x.id} value={x.id}>{x.id} · {x.plate} · {x.make} {x.model}</option>)}
              </select>
            </Field>
          </div>
        )}
        {origin === "nessuna" && <p className="mt-2 text-sm text-warn">Il pezzo resta tracciato dal suo codice, ma senza veicolo né pratica d&apos;origine: segnalato in scheda.</p>}
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="Vecchio codice" error={dupLegacy ? `Già usato da ${dupLegacy.id}` : undefined}>
          <input className="field code uppercase" value={legacy} onChange={(e) => setLegacy(e.target.value)} placeholder="K000…" />
        </Field>
        <Field label="Codice OE (se leggibile)">
          <input className="field code uppercase" value={oem} onChange={(e) => setOem(e.target.value)} />
        </Field>
        <Field label="Prezzo (€)">
          <input className="field code" inputMode="numeric" value={price} onChange={(e) => setPrice(e.target.value.replace(/[^0-9]/g, ""))} />
        </Field>
      </div>

      <Button className="w-full" size="lg" onClick={save}>
        Registra pezzo su {locToString({ ...loc, contenitore: contenitori ? box : undefined })}
      </Button>
      <p className="text-[13px] text-ink-3">Il pezzo entra in bozza: il responsabile lo approva come gli altri. Il riconoscimento da foto è simulato nel prototipo.</p>
    </div>
  );
}
