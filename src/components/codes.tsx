"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import QRCode from "qrcode";
import JsBarcode from "jsbarcode";
import { fetchAzienda } from "@/lib/accesso/azienda-client";

// Indirizzo base dei QR stampati (vedi /api/indirizzo): quello fisso dell'azienda se impostato,
// altrimenti quello di rete del server quando si stampa da "localhost", altrimenti quello in uso.
type BaseInfo = { fisso?: string; lan?: string };
let baseInfo: Promise<BaseInfo> | undefined;
const LOCAL_HOSTS = ["localhost", "127.0.0.1", "[::1]"];

export function usePublicBase() {
  const [info, setInfo] = useState<BaseInfo | null>(null);
  useEffect(() => {
    baseInfo ??= fetchAzienda("/api/indirizzo", { cache: "no-store" })
      .then((r) => (r.ok ? (r.json() as Promise<BaseInfo>) : {}))
      .catch(() => ({}));
    let alive = true;
    baseInfo.then((i) => alive && setInfo(i));
    return () => {
      alive = false;
    };
  }, []);
  if (typeof window === "undefined") return { base: "", ready: false, local: false };
  const { protocol, hostname, port, origin } = window.location;
  const isLocal = LOCAL_HOSTS.includes(hostname);
  const base = info?.fisso ?? (isLocal && info?.lan ? `${protocol}//${info.lan}${port ? `:${port}` : ""}` : origin);
  // local: i QR conterrebbero un indirizzo che si apre solo da questo computer
  return { base, ready: info !== null, local: isLocal && !info?.fisso && !info?.lan };
}

export const partPath = (id: string) => `/r/${id}`;

// QR disegnato come SVG puro: contiene solo l'ID univoco (come URL di apertura scheda).
export function Qr({ value, size = 120, className }: { value: string; size?: number; className?: string }) {
  const { cells, n } = useMemo(() => {
    const q = QRCode.create(value, { errorCorrectionLevel: "M" });
    const n = q.modules.size;
    const cells: [number, number][] = [];
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) if (q.modules.get(x, y)) cells.push([x, y]);
    return { cells, n };
  }, [value]);
  const pad = 2;
  return (
    <svg viewBox={`${-pad} ${-pad} ${n + pad * 2} ${n + pad * 2}`} width={size} height={size} className={className} shapeRendering="crispEdges" role="img" aria-label={`Codice QR ${value}`}>
      <rect x={-pad} y={-pad} width={n + pad * 2} height={n + pad * 2} fill="#fff" />
      <path d={cells.map(([x, y]) => `M${x} ${y}h1v1h-1z`).join("")} fill="#111418" />
    </svg>
  );
}

export function Barcode({ value, height = 40, className }: { value: string; height?: number; className?: string }) {
  const ref = useRef<SVGSVGElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    try {
      JsBarcode(ref.current, value, { format: "CODE128", displayValue: false, margin: 0, height, width: 2, lineColor: "#111418", background: "transparent" });
    } catch {
      ref.current.innerHTML = "";
    }
  }, [value, height]);
  return <svg ref={ref} className={className} preserveAspectRatio="none" aria-label={`Codice a barre ${value}`} />;
}

// Sotto l'anteprima di stampa: quale indirizzo finisce nei QR, così si vede prima di stampare 400 etichette.
export function QrAddressNote({ className = "" }: { className?: string }) {
  const { base, ready, local } = usePublicBase();
  if (!ready) return null;
  return (
    <p className={`text-[14px] ${local ? "font-semibold text-warn" : "text-ink-3"} ${className}`}>
      {local
        ? "Attenzione: i QR si aprirebbero solo da questo computer. Apri il gestionale dall'indirizzo di rete del server prima di stampare."
        : <>I QR aprono <b className="code text-ink-2">{base.replace(/^https?:\/\//, "")}</b>{base.startsWith("http://") ? ": i telefoni devono essere sulla rete dell'azienda." : "."}</>}
    </p>
  );
}
