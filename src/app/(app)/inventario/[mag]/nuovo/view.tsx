"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useRef, useState } from "react";
import { ArrowLeft, Camera, Check, Loader2, Printer, X } from "lucide-react";
import { useStore } from "@/lib/store";
import { CONDITIONS, PART_TYPES, sidesFor, typeById } from "@/lib/catalog";
import { savePhoto, identifyFromPhoto } from "@/lib/services";
import { locLong, locToString, normLoc } from "@/lib/warehouse";
import { Button, Empty, Field, Notice } from "@/components/ui";
import type { Condition } from "@/lib/types";
import { ShippingChoice } from "@/components/ShippingChoice";
import { asksShipping } from "@/lib/spedizione";
import { TypeOptions } from "@/components/TypeOptions";

// Ciò che resta uguale tra un pezzo e il successivo (stesso scaffale, spesso stessa auto)
interface Sticky {
  corsia: string;
  scaffale: string;
  ripiano: string;
  contenitore: string;
  model: string;
  pratica: string;
  targa: string;
  telaio: string;
}
const EMPTY: Sticky = { corsia: "", scaffale: "", ripiano: "", contenitore: "", model: "", pratica: "", targa: "", telaio: "" };

export default function AggiungiRicambio() {
  const { mag } = useParams<{ mag: string }>();
  const id = decodeURIComponent(mag);
  const { warehouses, parts, vehicles, addPart, printLabel } = useStore();
  const w = warehouses.find((x) => x.id === id);
  const fileRef = useRef<HTMLInputElement>(null);
  const storeKey = `inv-sticky-${id}`;

  const [sticky, setSticky] = useState<Sticky>(() => {
    try {
      return { ...EMPTY, ...JSON.parse(sessionStorage.getItem(storeKey) ?? "{}") };
    } catch {
      return EMPTY;
    }
  });
  const [photos, setPhotos] = useState<string[]>([]);
  const [guess, setGuess] = useState<{ typeId: string; confidence: number }[] | null>(null);
  const [guessing, setGuessing] = useState(false);
  const [typeId, setTypeId] = useState("");
  const [side, setSide] = useState("");
  const [misura, setMisura] = useState("");
  const [spedibile, setSpedibile] = useState(false);
  const [dicitura, setDicitura] = useState<string | null>(null); // null = composta in automatico
  const [legacy, setLegacy] = useState("");
  const [condition, setCondition] = useState<Condition | undefined>();
  const [vehicleId, setVehicleId] = useState("");
  const [oem, setOem] = useState("");
  const [price, setPrice] = useState("");
  const [tried, setTried] = useState(false);
  const [added, setAdded] = useState<string[]>([]);

  if (!w) return <Empty title={`Magazzino ${id} non trovato`} />;
  const t = typeId ? typeById(typeId) : undefined;
  const v = vehicles.find((x) => x.id === vehicleId);
  const model = v ? `${v.make} ${v.model}` : sticky.model.trim();
  const auto = t ? `${t.name}${misura ? ` ${misura}` : ""}${model ? ` ${model}` : ""}${side ? ` ${side.toLowerCase()}` : ""}` : "";
  const description = (dicitura ?? auto).trim();
  const loc = normLoc(w.id, sticky.corsia, sticky.scaffale, sticky.ripiano, sticky.contenitore);
  const locOk = !!loc.corsia && !!loc.scaffale && !!loc.ripiano;
  const dupLegacy = legacy.trim() && parts.find((p) => p.legacyCode?.toUpperCase() === legacy.trim().toUpperCase());
  const ok = !!t && description.length >= 4 && locOk && !!condition && (!t.sided || !!side) && (!t.misure || !!misura) && !dupLegacy;
  const knownPast = [...new Map(parts.filter((p) => p.pastDossier).map((p) => [p.pastDossier!.number, p.pastDossier!])).values()];
  const set = (k: keyof Sticky) => (e: React.ChangeEvent<HTMLInputElement>) => setSticky({ ...sticky, [k]: e.target.value });

  async function addPhotos(files: FileList | null) {
    if (!files?.length) return;
    const imgs = await Promise.all(Array.from(files).map((f) => savePhoto(f)));
    setPhotos((p) => [...p, ...imgs]);
    if (!guess && !typeId) {
      setGuessing(true);
      const r = await identifyFromPhoto(w!.categories.length ? PART_TYPES.filter((x) => w!.categories.includes(x.category)).map((x) => x.id) : PART_TYPES.map((x) => x.id));
      setGuessing(false);
      setGuess(r);
      setTypeId(r[0].typeId);
    }
  }

  function pickPratica(number: string) {
    const k = knownPast.find((x) => x.number.toUpperCase() === number.trim().toUpperCase());
    setSticky(k ? { ...sticky, pratica: k.number, targa: k.plate ?? sticky.targa, telaio: k.vin ?? sticky.telaio, model: k.model ?? sticky.model } : { ...sticky, pratica: number });
  }

  function save() {
    setTried(true);
    if (!ok || !t || !condition) return;
    sessionStorage.setItem(storeKey, JSON.stringify(sticky));
    const pid = addPart({
      vehicleId: v?.id ?? "",
      origin: "inventario",
      pastDossier:
        !v && sticky.pratica.trim()
          ? { number: sticky.pratica.trim().toUpperCase(), plate: sticky.targa.trim().toUpperCase() || undefined, vin: sticky.telaio.trim().toUpperCase() || undefined, model: sticky.model.trim() || undefined }
          : undefined,
      typeId: t.id,
      misura: t.misure ? misura : undefined,
      description,
      condition,
      status: "bozza",
      side: side || undefined,
      oem: oem.trim().toUpperCase() || undefined,
      oemVerified: false,
      spedibile: asksShipping(t.shippable) ? spedibile : undefined,
      legacyCode: legacy.trim().toUpperCase() || undefined,
      price: price ? Number(price) : undefined,
      location: loc,
      photos,
      aiSuggested: guess ? { typeId: guess[0].typeId, confidence: guess[0].confidence, accepted: guess[0].typeId === t.id } : undefined,
    });
    setAdded((xs) => [pid, ...xs]);
    // Pronto per il pezzo successivo: si azzera solo ciò che cambia da pezzo a pezzo
    setPhotos([]);
    setGuess(null);
    setTypeId("");
    setSide("");
    setSpedibile(false);
    setDicitura(null);
    setLegacy("");
    setCondition(undefined);
    setOem("");
    setPrice("");
    setTried(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const last = added[0] ? parts.find((p) => p.id === added[0]) : undefined;

  return (
    <div className="mx-auto max-w-2xl">
      <Link href={`/inventario/${encodeURIComponent(w.id)}`} className="mb-3 inline-flex items-center gap-1.5 text-[15px] font-semibold text-band">
        <ArrowLeft className="size-4" aria-hidden /> Mag. {w.id}
      </Link>
      <h1 className="mb-1 text-[28px] font-bold leading-tight md:text-[34px]">Aggiungi ricambio</h1>
      <p className="mb-5 text-ink-2">Un pezzo già presente in {w.name}: lo registri con la sua ubicazione e gli dai un codice nuovo con etichetta.</p>

      {last && (
        <div className="mb-5">
          <Notice tone="ok">
            <span className="flex flex-wrap items-center justify-between gap-3">
              <span>
                <b className="code">{last.id}</b> registrato in <b className="code">{locToString(last.location)}</b>
                {added.length > 1 && ` · ${added.length} in questa sessione`}
              </span>
              <button
                onClick={() => {
                  printLabel(last.id);
                  window.open(`/etichetta/${last.id}`, "_blank");
                }}
                className="inline-flex h-10 items-center gap-1.5 rounded-md bg-ok px-3 text-[15px] font-semibold text-white"
              >
                <Printer className="size-4" aria-hidden /> Stampa etichetta
              </button>
            </span>
          </Notice>
        </div>
      )}

      <div className="space-y-5">
        {/* Foto: aiuta a capire che pezzo è */}
        <section className="space-y-3">
          <input ref={fileRef} type="file" accept="image/*" capture="environment" multiple className="hidden" onChange={(e) => void addPhotos(e.target.files)} />
          {photos.length === 0 ? (
            <Button variant="secondary" className="w-full" size="lg" onClick={() => fileRef.current?.click()}>
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
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-sm font-semibold">Sembra:</span>
              {guess.map((g) => (
                <button
                  key={g.typeId}
                  onClick={() => setTypeId(g.typeId)}
                  aria-pressed={typeId === g.typeId}
                  className={`h-10 rounded-full border px-3.5 text-[15px] font-semibold ${typeId === g.typeId ? "border-band bg-band text-white" : "border-hair bg-label"}`}
                >
                  {typeById(g.typeId).name} <span className={typeId === g.typeId ? "text-white/80" : "text-ink-3"}>{Math.round(g.confidence * 100)}%</span>
                </button>
              ))}
            </div>
          )}
        </section>

        {/* Il pezzo */}
        <section className="space-y-4 rounded-md border border-hair bg-label p-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Tipo di pezzo" error={tried && !t ? "Scegli il tipo" : undefined}>
              <select className="field" value={typeId} onChange={(e) => { setTypeId(e.target.value); setMisura(""); }}>
                <option value="">Scegli…</option>
                <TypeOptions />
              </select>
            </Field>
            {t?.misure && (
              <Field label="Misura" error={tried && !misura ? "Scegli la misura" : undefined}>
                <select className="field" value={misura} onChange={(e) => setMisura(e.target.value)}>
                  <option value="">Scegli…</option>
                  {t.misure.map((m) => <option key={m}>{m}</option>)}
                </select>
              </Field>
            )}
            {t?.sided ? (
              <Field label="Lato" error={tried && !side ? "Indica il lato" : undefined}>
                <select className="field" value={side} onChange={(e) => setSide(e.target.value)}>
                  <option value="">Scegli…</option>
                  {sidesFor(t!.id).map((x) => <option key={x}>{x}</option>)}
                </select>
              </Field>
            ) : (
              <span className="hidden sm:block" />
            )}
            <Field label="Marca e modello del veicolo" hint="Resta per i pezzi successivi">
              <input className="field" value={v ? `${v.make} ${v.model}` : sticky.model} disabled={!!v} onChange={set("model")} placeholder="Es. Fiat Punto 1.2" />
            </Field>
            <Field label="Codice vecchio" error={dupLegacy ? `Già usato da ${dupLegacy.id}` : undefined}>
              <input className="field code uppercase" value={legacy} onChange={(e) => setLegacy(e.target.value)} placeholder="K000…" />
            </Field>
          </div>
          <Field label="Dicitura" hint={dicitura === null ? "Composta in automatico: puoi correggerla" : undefined} error={tried && description.length < 4 ? "Scrivi una descrizione" : undefined}>
            <input className="field" value={dicitura ?? auto} onChange={(e) => setDicitura(e.target.value)} placeholder="Es. Alternatore Fiat Punto 1.2" />
          </Field>
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
          {t && asksShipping(t.shippable) && <ShippingChoice value={spedibile} onChange={setSpedibile} />}
        </section>

        {/* Ubicazione nel magazzino */}
        <section className="rounded-md border border-hair bg-label p-4">
          <h2 className="mb-3 font-semibold">Ubicazione in Mag. {w.id} <span className="text-sm font-normal text-ink-3">· resta per i pezzi successivi</span></h2>
          <div className="grid grid-cols-4 gap-2">
            {(
              [
                ["corsia", "Corsia", "3 o T03"],
                ["scaffale", "Scaffale", "4 o 104"],
                ["ripiano", "Ripiano", "B"],
                ["contenitore", "Contenitore", "facolt."],
              ] as const
            ).map(([k, label, ph]) => (
              <Field key={k} label={label}>
                <input className="field code px-2 text-center text-[20px] font-bold uppercase" value={sticky[k]} onChange={set(k)} placeholder={ph} />
              </Field>
            ))}
          </div>
          <p className={`mt-2 text-[15px] ${locOk ? "font-semibold" : tried ? "font-semibold text-danger" : "text-ink-3"}`}>
            {locOk ? locLong(loc) : "Servono almeno corsia, scaffale e ripiano"}
          </p>
        </section>

        {/* Provenienza */}
        <section className="space-y-3 rounded-md border border-hair bg-label p-4">
          <h2 className="font-semibold">Provenienza <span className="text-sm font-normal text-ink-3">· dal vecchio archivio, se c&apos;è</span></h2>
          <div className="grid gap-3 sm:grid-cols-3">
            <Field label="Numero pratica">
              <input className="field code uppercase" list="pratiche-passate" value={sticky.pratica} disabled={!!v} onChange={(e) => pickPratica(e.target.value)} placeholder="CR-2019-…" />
              <datalist id="pratiche-passate">
                {knownPast.map((k) => <option key={k.number} value={k.number}>{[k.plate, k.model].filter(Boolean).join(" · ")}</option>)}
              </datalist>
            </Field>
            <Field label="Targa">
              <input className="field code uppercase" value={sticky.targa} disabled={!!v} onChange={set("targa")} />
            </Field>
            <Field label="Telaio">
              <input className="field code uppercase" maxLength={17} value={sticky.telaio} disabled={!!v} onChange={set("telaio")} />
            </Field>
          </div>
          <details>
            <summary className="flex min-h-10 cursor-pointer list-none items-center text-[15px] font-semibold text-band">È un veicolo già nel gestionale?</summary>
            <select className="field mt-2" value={vehicleId} onChange={(e) => setVehicleId(e.target.value)}>
              <option value="">No</option>
              {vehicles.map((x) => <option key={x.id} value={x.id}>{x.id} · {x.plate} · {x.make} {x.model}</option>)}
            </select>
          </details>
          {!v && !sticky.pratica.trim() && <p className="text-sm text-warn">Senza pratica né veicolo il pezzo risulterà con provenienza non documentata.</p>}
        </section>

        {/* Facoltativi */}
        <details className="rounded-md border border-hair bg-label p-4">
          <summary className="flex cursor-pointer list-none items-center font-semibold">Codice OE e prezzo (facoltativi)</summary>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <Field label="Codice OE">
              <input className="field code uppercase" value={oem} onChange={(e) => setOem(e.target.value)} />
            </Field>
            <Field label="Prezzo (€)">
              <input className="field code" inputMode="numeric" value={price} onChange={(e) => setPrice(e.target.value.replace(/[^0-9]/g, ""))} />
            </Field>
          </div>
        </details>
      </div>

      <div className="sticky bottom-[calc(72px+env(safe-area-inset-bottom))] z-20 mt-5 rounded-md border border-hair bg-label p-3 shadow-[0_8px_24px_-12px_rgb(17_20_24/0.35)] md:bottom-4">
        <Button className="w-full" size="lg" onClick={save}>
          <Check className="size-6" aria-hidden /> Registra {locOk ? `in ${locToString(loc)}` : "ricambio"}
        </Button>
      </div>
      <p className="mt-3 text-[13px] text-ink-3">Il pezzo entra in bozza con un codice nuovo; il codice vecchio resta cercabile. Il riconoscimento da foto è simulato nel prototipo.</p>
    </div>
  );
}
