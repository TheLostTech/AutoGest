"use client";

import { useEffect, useMemo, useRef } from "react";
import QRCode from "qrcode";
import JsBarcode from "jsbarcode";

export function partUrl(id: string) {
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  return `${origin}/r/${id}`;
}

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

export function absUrl(path: string) {
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  return `${origin}${path}`;
}
