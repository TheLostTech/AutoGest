"use client";

import type { Gpsr, Produttore } from "@/lib/types";
import { Field } from "@/components/ui";

export interface GpsrScelta {
  esente: boolean;
  produttore: boolean;
  prod: Produttore;
}
export const GPSR_VUOTO: GpsrScelta = { esente: false, produttore: false, prod: { ragioneSociale: "", indirizzo: "", citta: "", cap: "", paese: "" } };

/** GPSR deciso dall'operatore, o undefined se la scelta non è completa. */
export function gpsrDaScelta(s: GpsrScelta): Gpsr | undefined {
  if (s.esente) return { tipo: "esente" };
  const p = s.prod;
  if (s.produttore && p.ragioneSociale.trim() && p.indirizzo.trim() && p.citta.trim() && p.cap.trim() && p.paese.trim()) return { tipo: "produttore", produttore: p };
  return undefined;
}

/** Passo "GPSR da confermare": pezzo messo in commercio prima del 13/12/2024, oppure i dati del produttore. */
export function GpsrStep({ value, onChange }: { value: GpsrScelta; onChange: (v: GpsrScelta) => void }) {
  const setP = (k: keyof Produttore, v: string) => onChange({ ...value, prod: { ...value.prod, [k]: v } });
  return (
    <div className="space-y-3 rounded-md border border-warn/50 bg-warn-bg p-3">
      <h3 className="font-semibold text-ink">GPSR da confermare</h3>
      <label className="flex min-h-11 items-center gap-3 text-[15px]">
        <input type="checkbox" className="size-5" checked={value.esente} onChange={(e) => onChange({ ...value, esente: e.target.checked, produttore: e.target.checked ? false : value.produttore })} />
        Pezzo messo in commercio prima del 13/12/2024
      </label>
      <label className="flex min-h-11 items-center gap-3 text-[15px]">
        <input type="checkbox" className="size-5" checked={value.produttore} onChange={(e) => onChange({ ...value, produttore: e.target.checked, esente: e.target.checked ? false : value.esente })} />
        Indico io il produttore
      </label>
      {value.produttore && (
        <div className="grid gap-3 md:grid-cols-2">
          <Field label="Ragione sociale"><input className="field" value={value.prod.ragioneSociale} onChange={(e) => setP("ragioneSociale", e.target.value)} /></Field>
          <Field label="Indirizzo"><input className="field" value={value.prod.indirizzo} onChange={(e) => setP("indirizzo", e.target.value)} /></Field>
          <Field label="Città"><input className="field" value={value.prod.citta} onChange={(e) => setP("citta", e.target.value)} /></Field>
          <Field label="CAP"><input className="field" value={value.prod.cap} onChange={(e) => setP("cap", e.target.value)} /></Field>
          <Field label="Paese"><input className="field" value={value.prod.paese} onChange={(e) => setP("paese", e.target.value)} /></Field>
          <Field label="Email (facoltativa)"><input className="field" value={value.prod.email ?? ""} onChange={(e) => setP("email", e.target.value)} /></Field>
        </div>
      )}
    </div>
  );
}
