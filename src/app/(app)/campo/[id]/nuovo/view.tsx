"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useRef, useState } from "react";
import { Camera, Check, ChevronLeft, ChevronRight, Loader2, Printer, Sparkles, X } from "lucide-react";
import { useStore } from "@/lib/store";
import { CONDITIONS, sidesFor, typeById } from "@/lib/catalog";
import { savePhoto, suggestComponent } from "@/lib/services";
import { recoveryList } from "@/lib/logic";
import { catalogFor, platformLabel } from "@/lib/partsdb";
import { suggestUsedPrice } from "@/lib/pricing";
import type { Condition } from "@/lib/types";
import { Button, ButtonLink, Empty, Field, Plate } from "@/components/ui";
import { PartLabel } from "@/components/PartLabel";
import { ShippingChoice } from "@/components/ShippingChoice";
import { asksShipping } from "@/lib/spedizione";
import { TypePicker } from "@/components/TypePicker";

export default function Page() {
  return (
    <Suspense>
      <NuovoPezzo />
    </Suspense>
  );
}

function NuovoPezzo() {
  const { id } = useParams<{ id: string }>();
  const sp = useSearchParams();
  const router = useRouter();
  const preset = sp.get("tipo") ?? undefined;
  const store = useStore();
  const v = store.vehicles.find((x) => x.id === id);
  const fileRef = useRef<HTMLInputElement>(null);

  const [photos, setPhotos] = useState<string[]>([]);
  const [typeId, setTypeId] = useState<string | undefined>(preset);
  const [ai, setAi] = useState<{ typeId: string; confidence: number } | null>(null);
  const [aiState, setAiState] = useState<"idle" | "loading" | "proposed" | "accepted" | "rejected">("idle");
  const [condition, setCondition] = useState<Condition | undefined>();
  const [side, setSide] = useState<string>("");
  const [misura, setMisura] = useState("");
  const [spedibile, setSpedibile] = useState(false);
  const [oem, setOem] = useState("");
  const [defects, setDefects] = useState("");
  const [price, setPrice] = useState("");
  const [oemOk, setOemOk] = useState(false);
  const [savedId, setSavedId] = useState<string>();
  const [tried, setTried] = useState(false);

  if (!v) return <Empty title={`Veicolo ${id} non trovato`} />;
  const t = typeId ? typeById(typeId) : undefined;

  async function addPhotos(files: FileList | null) {
    if (!files?.length) return;
    const imgs = await Promise.all(Array.from(files).map((f) => savePhoto(f)));
    setPhotos((p) => [...p, ...imgs]);
    if (!preset && aiState === "idle") {
      setAiState("loading");
      const missing = recoveryList(v!, store.parts, store.vehicles, store.rules).slice(0, 6).map((r) => r.typeId);
      const r = await suggestComponent(undefined, missing);
      setAi(r);
      setTypeId(r.typeId);
      setAiState("proposed");
    }
  }

  const cat = t ? catalogFor(t.id, v.platform, side || undefined) : null;
  // Prezzo suggerito: quota del nuovo per condizione, più basso se la tipologia è già oltre la scorta massima
  const rule = t && store.rules.find((r) => r.typeId === t.id);
  const inStock = t ? store.parts.filter((p) => p.typeId === t.id && p.status === "disponibile").length : 0;
  const suggested = cat && condition ? suggestUsedPrice(cat.newPrice, condition, inStock, rule?.max ?? 99) : undefined;
  const description = t ? `${t.name}${misura ? ` ${misura}` : ""} ${v.make} ${v.model}${side ? ` ${side.toLowerCase()}` : ""}` : "";
  const valid = !!t && !!condition && (!t.sided || !!side) && (!t.misure || !!misura);

  function save() {
    setTried(true);
    if (!valid || !t || !condition) return;
    const pid = store.addPart({
      vehicleId: v!.id,
      typeId: t.id,
      misura: t.misure ? misura : undefined,
      description,
      condition,
      status: "bozza",
      side: side || undefined,
      oem: oemOk && cat ? cat.oem : oem.trim() || undefined,
      oemVerified: oemOk,
      spedibile: asksShipping(t.shippable) ? spedibile : undefined,
      manufacturer: (oemOk || oem.trim()) && cat ? cat.manufacturer : undefined,
      compat: oemOk && cat ? { platforms: cat.platforms, source: cat.source, verified: true, checkedAt: new Date().toISOString() } : undefined,
      km: v!.km,
      defects: defects.trim() || undefined,
      price: price ? Number(price) : undefined,
      photos,
      aiSuggested: ai ? { typeId: ai.typeId, confidence: ai.confidence, accepted: ai.typeId === t.id } : undefined,
    });
    setSavedId(pid);
    window.scrollTo({ top: 0 });
  }

  const saved = savedId ? store.parts.find((p) => p.id === savedId) : undefined;
  if (saved) {
    return (
      <div className="mx-auto max-w-xl">
        <p className="mb-3 flex items-center gap-2 text-[17px] font-semibold text-ok">
          <Check className="size-5" strokeWidth={3} aria-hidden />
          Pezzo salvato. Applica l&apos;etichetta.
        </p>
        <div className="stamp-in">
          <PartLabel part={saved} vehicle={v} />
        </div>
        <div className="mt-5 grid gap-3">
          <Button
            size="lg"
            onClick={() => {
              store.printLabel(saved.id);
              window.open(`/etichetta/${saved.id}`, "_blank");
            }}
          >
            <Printer className="size-5" aria-hidden />
            {saved.labelPrints > 0 ? "Ristampa etichetta" : "Stampa etichetta"}
          </Button>
          <Button
            size="lg"
            variant="secondary"
            onClick={() => {
              setPhotos([]);
              setTypeId(undefined);
              setAi(null);
              setAiState("idle");
              setCondition(undefined);
              setSide("");
              setSpedibile(false);
              setOem("");
              setDefects("");
              setPrice("");
              setOemOk(false);
              setTried(false);
              setSavedId(undefined);
              router.replace(`/campo/${v.id}/nuovo`);
            }}
          >
            <Camera className="size-5" aria-hidden />
            Cataloga un altro pezzo
          </Button>
          <ButtonLink href={`/campo/${v.id}`} variant="quiet">Torna al veicolo {v.id}</ButtonLink>
        </div>
        <p className="mt-4 text-sm text-ink-2">La scheda resta in bozza finché il responsabile non la approva. La posizione di magazzino la assegna il magazziniere scansionando l&apos;etichetta.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-xl">
      <div className="mb-4 flex items-center justify-between gap-3">
        <Link href={`/campo/${v.id}`} className="-ml-1 inline-flex min-h-11 items-center gap-1 font-semibold text-band">
          <ChevronLeft className="size-5" aria-hidden />
          {v.id}
        </Link>
        <span className="flex items-center gap-2 text-sm text-ink-2">
          <Plate plate={v.plate} size="sm" /> {v.make} {v.model}
        </span>
      </div>
      <h1 className="text-[28px] font-bold leading-tight">Nuovo pezzo</h1>
      <p className="mt-1 text-ink-2">Targa, telaio e pratica vengono ereditati dal veicolo: non serve riscriverli.</p>

      {/* Foto */}
      <section className="mt-5">
        <div className="grid grid-cols-3 gap-2">
          {photos.map((p, i) => (
            <div key={i} className="relative aspect-square overflow-hidden rounded border border-hair bg-white">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={p} alt={`Foto ${i + 1}`} className="size-full object-cover" />
              <button onClick={() => setPhotos(photos.filter((_, j) => j !== i))} className="absolute right-1 top-1 grid size-9 place-items-center rounded-full bg-ink/80 text-white" aria-label={`Rimuovi foto ${i + 1}`}>
                <X className="size-4" />
              </button>
            </div>
          ))}
          <button
            onClick={() => fileRef.current?.click()}
            className={`flex aspect-square flex-col items-center justify-center gap-1 rounded border-2 border-dashed font-semibold ${photos.length ? "border-hair text-band" : "col-span-3 aspect-[2/1] border-band bg-band-tint text-band"}`}
          >
            <Camera className={photos.length ? "size-7" : "size-10"} aria-hidden />
            {photos.length ? "Altra foto" : "Scatta la prima foto"}
          </button>
        </div>
        <input ref={fileRef} type="file" accept="image/*" capture="environment" multiple className="hidden" onChange={(e) => { void addPhotos(e.target.files); e.target.value = ""; }} />
      </section>

      {/* Suggerimento IA: proposta, mai certezza */}
      {aiState === "loading" && (
        <p className="mt-4 flex items-center gap-2 rounded-md bg-band-tint px-4 py-3 font-semibold text-band-deep">
          <Loader2 className="size-5 animate-spin" aria-hidden /> Riconoscimento del componente dalla foto…
        </p>
      )}
      {ai && aiState === "proposed" && (
        <div className="mt-4 rounded-md border border-band bg-band-tint p-4">
          <p className="flex items-center gap-2 text-sm font-semibold text-band-deep">
            <Sparkles className="size-4" aria-hidden /> Suggerimento IA (simulato) · affidabilità {Math.round(ai.confidence * 100)}%
          </p>
          <p className="mt-1 text-[20px] font-bold">Sembra: {typeById(ai.typeId).name}</p>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <Button onClick={() => setAiState("accepted")}>Sì, è questo</Button>
            <Button variant="secondary" onClick={() => { setAiState("rejected"); setTypeId(undefined); }}>No, scelgo io</Button>
          </div>
        </div>
      )}

      <div className="mt-5 space-y-5">
        <Field label="Che pezzo è?" error={tried && !t ? "Scegli la tipologia" : undefined}>
          <TypePicker className="text-[17px] font-semibold" value={typeId ?? ""} vuoto="Seleziona…" onChange={(v) => { setTypeId(v || undefined); setMisura(""); setOemOk(false); if (aiState === "proposed") setAiState("rejected"); }} />
        </Field>

        {t?.misure && (
          <Field label="Misura" error={tried && !misura ? "Scegli la misura" : undefined}>
            <select className="field text-[17px] font-semibold" value={misura} onChange={(e) => setMisura(e.target.value)}>
              <option value="">Seleziona…</option>
              {t.misure.map((m) => <option key={m}>{m}</option>)}
            </select>
          </Field>
        )}

        {t?.sided && (
          <fieldset>
            <legend className="mb-1.5 text-sm font-semibold">Lato / posizione</legend>
            <div className="grid grid-cols-2 gap-2">
              {sidesFor(t.id).map((s) => (
                <button key={s} onClick={() => { setSide(s); setOemOk(false); }} className={`min-h-12 rounded-md border font-semibold ${side === s ? "border-band bg-band text-white" : "border-hair bg-label"}`}>{s}</button>
              ))}
            </div>
            {tried && !side && <p className="mt-1 text-sm font-medium text-danger">Indica il lato</p>}
          </fieldset>
        )}

        <fieldset>
          <legend className="mb-1.5 text-sm font-semibold">Condizioni</legend>
          <div className="grid grid-cols-2 gap-2">
            {(Object.keys(CONDITIONS) as Condition[]).map((c) => (
              <button key={c} onClick={() => setCondition(c)} className={`flex min-h-16 items-center gap-3 rounded-md border px-3 text-left ${condition === c ? "border-band bg-band text-white" : "border-hair bg-label"}`}>
                <span className="code text-[30px] font-bold leading-none">{c}</span>
                <span className="text-[15px] font-semibold leading-tight">{CONDITIONS[c].label}</span>
              </button>
            ))}
          </div>
          {tried && !condition && <p className="mt-1 text-sm font-medium text-danger">Scegli le condizioni</p>}
        </fieldset>

        {t && asksShipping(t.shippable) && <ShippingChoice value={spedibile} onChange={setSpedibile} />}

        {cat && (!t?.sided || side) && (
          <div className={`rounded-md border p-4 ${oemOk ? "border-ok bg-ok-bg" : "border-hair bg-label"}`}>
            <p className="text-[15px]">Codice OE atteso</p>
            <p className="code text-[26px] font-bold leading-tight">{cat.oem}</p>
            <p className="text-sm text-ink-2">{cat.manufacturer} · montabile su {cat.platforms.length} {cat.platforms.length === 1 ? "modello" : "modelli"}{cat.platforms.length > 1 ? `: ${cat.platforms.map(platformLabel).join(", ")}` : ""}</p>
            <p className="mt-1 text-[13px] text-ink-3">Fonte: catalogo ricambi (simulato)</p>
            {oemOk ? (
              <p className="mt-3 flex items-center gap-2 font-semibold text-ok"><Check className="size-5" strokeWidth={3} aria-hidden /> Codice verificato sul pezzo: compatibilità dichiarata</p>
            ) : (
              <div className="mt-3 grid grid-cols-2 gap-2">
                <Button variant="secondary" onClick={() => setOemOk(true)}>Coincide col pezzo</Button>
                <Button variant="quiet" onClick={() => (document.querySelector("details") as HTMLDetailsElement | null)?.setAttribute("open", "")}>Diverso / illeggibile</Button>
              </div>
            )}
          </div>
        )}

        <details className="rounded-md border border-hair bg-label">
          <summary className="flex min-h-12 cursor-pointer list-none items-center gap-2 px-4 py-3 font-semibold [&::-webkit-details-marker]:hidden">
            <ChevronRight className="size-5 shrink-0 text-band transition-transform duration-200 [[open]>summary>&]:rotate-90" aria-hidden />
            Dati facoltativi: codice OEM, difetti, prezzo
          </summary>
          <div className="space-y-4 border-t border-hair-soft p-4">
            <Field label="Codice OEM (se leggibile)" hint="Non dichiara compatibilità finché non viene verificato">
              <input className="field code uppercase" value={oem} onChange={(e) => setOem(e.target.value)} />
            </Field>
            <Field label="Difetti">
              <input className="field" value={defects} onChange={(e) => setDefects(e.target.value)} />
            </Field>
            <Field label="Prezzo proposto (€)" hint={cat ? `Nuovo originale ≈ ${cat.newPrice} € (catalogo simulato)` : t ? `Riferimento tipologia: ${t.basePrice} €` : undefined}>
              <span className="flex items-center gap-2">
                <input className="field code" inputMode="numeric" value={price} onChange={(e) => setPrice(e.target.value.replace(/[^0-9]/g, ""))} />
                {suggested !== undefined && String(suggested) !== price && (
                  <button type="button" onClick={() => setPrice(String(suggested))} className="min-h-12 shrink-0 rounded-md border border-band/40 bg-band-tint px-3 text-[15px] font-semibold text-band">
                    Usa {suggested} €
                  </button>
                )}
              </span>
            </Field>
          </div>
        </details>

        {t && (
          <p className="rounded-md bg-carton px-4 py-3 text-[15px]">
            <span className="text-ink-3">Descrizione: </span>
            <b>{description}</b>
            <span className="block text-sm text-ink-3">da {v.id} · {v.plate} · pratica {v.dossier.number || "da registrare"}</span>
          </p>
        )}
      </div>

      <div className="sticky bottom-[calc(72px+env(safe-area-inset-bottom))] z-20 mt-6 md:bottom-4">
        <Button size="lg" className="w-full" onClick={save}>
          <Check className="size-6" strokeWidth={3} aria-hidden />
          Salva e genera etichetta
        </Button>
      </div>
      <div className="h-6" />
    </div>
  );
}
