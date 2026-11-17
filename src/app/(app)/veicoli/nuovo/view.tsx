"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Camera, Keyboard, Loader2, Search } from "lucide-react";
import { useStore } from "@/lib/store";
import { Button, Field, Notice, PageTitle, Panel, Plate } from "@/components/ui";
import { PLATFORMS } from "@/lib/catalog";
import { savePhoto, lookupPlate, OCR_SAMPLES, PLATE_RE, simulateOcr, VIN_RE, type OcrResult } from "@/lib/services";

export default function NuovoVeicolo() {
  const router = useRouter();
  const { vehicles, addVehicle, log } = useStore();
  const fileRef = useRef<HTMLInputElement>(null);

  const [photo, setPhoto] = useState<string>();
  const [ocr, setOcr] = useState<OcrResult | null>(null);
  const [reading, setReading] = useState(false);
  const [plate, setPlate] = useState("");
  const [lookupState, setLookupState] = useState<"idle" | "loading" | "found" | "notfound" | "error">("idle");
  const [lookupError, setLookupError] = useState("");
  const [simulateFail, setSimulateFail] = useState(false);
  const [f, setF] = useState({ make: "", model: "", version: "", platform: "", year: "", fuel: "Benzina", vin: "", color: "", km: "", weight: "", notes: "" });
  const [touched, setTouched] = useState(false);

  const normPlate = plate.replace(/\s+/g, "").toUpperCase();
  const dup = normPlate ? vehicles.find((v) => v.plate === normPlate) : undefined;
  const dupVin = f.vin ? vehicles.find((v) => v.vin === f.vin.toUpperCase()) : undefined;
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value });

  async function onPhoto(file?: File) {
    if (!file) return;
    setPhoto(await savePhoto(file, 900));
    setReading(true);
    setOcr(null);
    const res = await simulateOcr(Date.now() % 97);
    setOcr(res);
    setPlate(res.plate);
    setReading(false);
    setLookupState("idle");
  }

  async function doLookup() {
    setLookupState("loading");
    setLookupError("");
    try {
      const r = await lookupPlate(normPlate, simulateFail);
      if (!r) {
        setLookupState("notfound");
        return;
      }
      setF((x) => ({ ...x, make: r.make, model: r.model, version: r.version, platform: r.platform, year: String(r.year), fuel: r.fuel, vin: r.vin, color: r.color }));
      setLookupState("found");
    } catch (e) {
      setLookupError((e as Error).message);
      setLookupState("error");
      log({ entity: "sistema", entityId: "banca-dati-veicoli", action: "Errore servizio esterno", detail: (e as Error).message });
    }
  }

  const plateOk = PLATE_RE.test(normPlate);
  const vinOk = !f.vin || VIN_RE.test(f.vin.toUpperCase());
  const verified = lookupState === "found" && !!f.vin && vinOk;
  const canSave = plateOk && !dup && !dupVin && f.make && f.model && vinOk;

  function save() {
    setTouched(true);
    if (!canSave) return;
    const id = addVehicle({
      plate: normPlate,
      vin: f.vin.toUpperCase(),
      make: f.make,
      model: f.model,
      version: f.version,
      platform: f.platform || "sconosciuta",
      year: Number(f.year) || 0,
      fuel: f.fuel,
      km: f.km ? Number(f.km) : undefined,
      weightKg: f.weight ? Number(f.weight) : undefined,
      color: f.color,
      dossier: { number: "", kind: "Certificato di Rottamazione Digitale", status: "da registrare" },
      verification: verified ? "verificato" : "da verificare",
      work: "accettato",
      photo,
      notes: f.notes || undefined,
    });
    router.push(`/veicoli/${id}`);
  }

  return (
    <div className="mx-auto max-w-3xl">
      <PageTitle title="Nuovo ingresso veicolo" sub="Il veicolo si identifica una volta sola: tutti i ricambi erediteranno targa, telaio e pratica." />

      <Panel title="1 · Targa">
        <div className="space-y-4 p-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <Button size="lg" onClick={() => fileRef.current?.click()} disabled={reading}>
              {reading ? <Loader2 className="size-5 animate-spin" aria-hidden /> : <Camera className="size-5" aria-hidden />}
              {reading ? "Lettura targa…" : "Fotografa la targa"}
            </Button>
            <Button size="lg" variant="secondary" onClick={() => document.getElementById("plate")?.focus()}>
              <Keyboard className="size-5" aria-hidden />
              Digita la targa
            </Button>
          </div>
          <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={(e) => onPhoto(e.target.files?.[0])} />

          {photo && (
            <div className="grid gap-4 sm:grid-cols-[200px_1fr]">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={photo} alt="Foto della targa" className="aspect-[4/3] w-full rounded border border-hair object-cover" />
              <div>
                {reading && <p className="text-ink-2">Riconoscimento caratteri in corso…</p>}
                {ocr && (
                  <div className="space-y-2">
                    <p className="text-sm font-semibold text-ink-2">Letto dall&apos;OCR (simulato) · affidabilità {Math.round(ocr.confidence * 100)}%</p>
                    <div className="code flex gap-1 text-[34px] font-bold">
                      {ocr.plate.split("").map((c, i) => (
                        <span key={i} className={`grid h-14 w-9 place-items-center rounded ${ocr.uncertain.includes(i) ? "bg-warn-bg text-warn ring-2 ring-warn" : "bg-carton"}`}>
                          {c}
                        </span>
                      ))}
                    </div>
                    <p className="text-sm text-ink-2">I caratteri evidenziati sono incerti: confronta con la targa reale e correggi qui sotto se serve.</p>
                  </div>
                )}
              </div>
            </div>
          )}

          <Field label="Targa" error={touched && !plateOk ? "Formato targa non valido (es. AB123CD)" : undefined} hint="Formato italiano AB123CD. Correggi a mano se l'OCR ha sbagliato.">
            <input id="plate" className="field code text-[22px] font-bold uppercase tracking-[0.08em]" value={plate} onChange={(e) => { setPlate(e.target.value.toUpperCase()); setLookupState("idle"); }} placeholder="AB123CD" maxLength={9} autoComplete="off" />
          </Field>
          {!photo && (
            <p className="text-sm text-ink-3">
              Targhe di prova presenti nella banca dati simulata: {OCR_SAMPLES.map((p) => (
                <button key={p} type="button" onClick={() => { setPlate(p); setLookupState("idle"); }} className="code mx-0.5 font-semibold text-band underline">{p}</button>
              ))}
            </p>
          )}

          {dup && (
            <Notice tone="danger">
              Veicolo già presente: <Link className="code font-bold underline" href={`/veicoli/${dup.id}`}>{dup.id}</Link> · {dup.make} {dup.model}, ingresso del {new Date(dup.intakeAt).toLocaleDateString("it-IT")}. Non è possibile registrarlo due volte.
            </Notice>
          )}
        </div>
      </Panel>

      <Panel title="2 · Identificazione" className="mt-5">
        <div className="space-y-4 p-4">
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="secondary" onClick={doLookup} disabled={!plateOk || !!dup || lookupState === "loading"}>
              {lookupState === "loading" ? <Loader2 className="size-5 animate-spin" aria-hidden /> : <Search className="size-5" aria-hidden />}
              Cerca dati veicolo
            </Button>
            <label className="flex min-h-11 items-center gap-2 text-sm font-medium text-ink-2">
              <input type="checkbox" checked={simulateFail} onChange={(e) => setSimulateFail(e.target.checked)} className="size-5 accent-[var(--band)]" />
              Simula servizio esterno non disponibile
            </label>
          </div>
          {lookupState === "found" && <Notice tone="ok">Dati trovati nella banca dati veicoli (simulata). Controlla che corrispondano al mezzo e al libretto.</Notice>}
          {lookupState === "notfound" && <Notice tone="warn">Nessun risultato per <span className="code font-bold">{normPlate}</span>. Compila a mano: il veicolo resterà «da verificare».</Notice>}
          {lookupState === "error" && <Notice tone="danger">{lookupError}</Notice>}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Marca" error={touched && !f.make ? "Obbligatoria" : undefined}>
              <input className="field" value={f.make} onChange={set("make")} />
            </Field>
            <Field label="Modello" error={touched && !f.model ? "Obbligatorio" : undefined}>
              <input className="field" value={f.model} onChange={set("model")} />
            </Field>
            <Field label="Versione / motorizzazione" hint="Solo se accertata">
              <input className="field" value={f.version} onChange={set("version")} />
            </Field>
            <Field label="Piattaforma per compatibilità" hint="Usata per confrontare le scorte (demo)">
              <select className="field" value={f.platform} onChange={set("platform")}>
                <option value="">Non determinata</option>
                {PLATFORMS.map((p) => (
                  <option key={p.id} value={p.id}>{p.label} · {p.years}</option>
                ))}
              </select>
            </Field>
            <Field label="Anno">
              <input className="field code" inputMode="numeric" value={f.year} onChange={set("year")} />
            </Field>
            <Field label="Alimentazione">
              <select className="field" value={f.fuel} onChange={set("fuel")}>
                {["Benzina", "Diesel", "GPL", "Metano", "Ibrida", "Elettrica"].map((x) => <option key={x}>{x}</option>)}
              </select>
            </Field>
            <Field label="Telaio (VIN)" error={!vinOk ? "Il VIN ha 17 caratteri, senza I, O, Q" : dupVin ? `Telaio già registrato su ${dupVin.id}` : undefined}>
              <input className="field code uppercase tracking-wide" value={f.vin} onChange={set("vin")} maxLength={17} />
            </Field>
            <Field label="Chilometri">
              <input className="field code" inputMode="numeric" value={f.km} onChange={set("km")} />
            </Field>
            <Field label="Peso in ingresso (kg)" hint="Dalla pesata: entra da solo nel registro rifiuti">
              <input className="field code" inputMode="numeric" value={f.weight} onChange={set("weight")} />
            </Field>
          </div>
        </div>
      </Panel>

      <Panel title="3 · Note e pratica" className="mt-5">
        <div className="grid gap-4 p-4 sm:grid-cols-2">
          <p className="rounded-md bg-carton px-4 py-3 text-[15px] text-ink-2 sm:col-span-2">
            La pratica si completa nella scheda del veicolo, dopo il salvataggio: chi consegna e documenti, visura, presa in carico nel RVFU (il numero del certificato lo assegna il registro) e radiazione.
          </p>
          <div className="sm:col-span-2">
            <Field label="Note">
              <textarea className="field" value={f.notes} onChange={set("notes")} />
            </Field>
          </div>
        </div>
      </Panel>

      <div className="sticky bottom-[calc(72px+env(safe-area-inset-bottom))] z-20 mt-6 flex items-center justify-between gap-3 rounded-md border border-hair bg-label p-2.5 shadow-[0_8px_24px_-12px_rgb(17_20_24/0.35)] md:bottom-4">
        <div className="flex min-w-0 flex-col gap-1 text-[13px] leading-tight sm:flex-row sm:items-center sm:gap-3 sm:text-sm">
          {plateOk && <Plate plate={normPlate} size="sm" />}
          <span className={verified ? "font-semibold text-ok" : "font-semibold text-warn"}>{verified ? "Verificato" : "Sarà «da verificare»"}</span>
        </div>
        <Button onClick={save} disabled={touched && !canSave} className="shrink-0">Registra ingresso</Button>
      </div>
    </div>
  );
}
