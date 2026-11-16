"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ScanLine, VideoOff } from "lucide-react";
import { useStore } from "@/lib/store";
import { Button, Notice, PageTitle } from "@/components/ui";

type Detector = { detect: (src: HTMLVideoElement) => Promise<{ rawValue: string }[]> };

function extractId(raw: string) {
  const m = raw.toUpperCase().match(/R-\d{6}/);
  return m?.[0];
}

export default function Scansione() {
  const router = useRouter();
  const parts = useStore((s) => s.parts);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [camera, setCamera] = useState<"off" | "on" | "unsupported" | "denied">("off");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const streamRef = useRef<MediaStream | null>(null);

  const open = (raw: string) => {
    const id = extractId(raw) ?? raw.trim().toUpperCase();
    if (parts.some((p) => p.id === id)) {
      streamRef.current?.getTracks().forEach((t) => t.stop());
      router.push(`/ricambi/${id}`);
    } else setError(`Nessun ricambio con codice «${raw.trim()}». Controlla l'etichetta o cerca nel magazzino.`);
  };

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
          if (r[0]) return open(r[0].rawValue);
        } catch {}
        requestAnimationFrame(loop);
      };
      loop();
    } catch {
      setCamera("denied");
    }
  }

  useEffect(() => () => streamRef.current?.getTracks().forEach((t) => t.stop()), []);
  const samples = parts.filter((p) => p.status === "disponibile").slice(0, 4);

  return (
    <div className="mx-auto max-w-xl">
      <PageTitle title="Scansiona etichetta" sub="Inquadra il QR o il codice a barre: si apre la scheda con provenienza, stato e posizione." />
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
                <p className="max-w-xs">{camera === "unsupported" ? "Questo browser non legge i codici dalla fotocamera. Su smartphone Android con Chrome funziona; qui puoi digitare il codice." : "Accesso alla fotocamera negato. Digita il codice stampato sotto il QR."}</p>
              </>
            )}
          </div>
        )}
      </div>

      <form
        className="mt-5 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          open(code);
        }}
      >
        <input className="field code text-[22px] font-bold uppercase" placeholder="R-002301" value={code} onChange={(e) => setCode(e.target.value)} aria-label="Codice ricambio" />
        <Button type="submit">Apri</Button>
      </form>
      {error && <div className="mt-3"><Notice tone="danger">{error}</Notice></div>}
      <p className="mt-4 text-sm text-ink-3">
        Codici di prova:{" "}
        {samples.map((p) => (
          <button key={p.id} onClick={() => open(p.id)} className="code mx-1 font-semibold text-band underline">{p.id}</button>
        ))}
      </p>
    </div>
  );
}
