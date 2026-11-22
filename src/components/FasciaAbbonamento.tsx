"use client";

// Fascia in cima al gestionale, solo per il titolare: pagamento non riuscito, oppure disdetta negli ultimi 7 giorni
// (spec registrazione-pagamento, sezione 6). Il testo è la riga del conto alla rovescia.
import Link from "next/link";
import { AlertTriangle } from "lucide-react";
import { contoAllaRovescia, fasciaDaMostrare, type Abbonamento } from "@/lib/abbonamento";
import { useOra } from "@/lib/use-ora";

export function FasciaAbbonamento({ abbonamento, qui }: { abbonamento: Abbonamento; qui: boolean }) {
  const ora = useOra();
  if (!ora || !fasciaDaMostrare(abbonamento, ora)) return null;
  const conto = contoAllaRovescia(abbonamento, ora);
  if (!conto) return null;
  const errore = conto.tono === "errore";
  return (
    <p
      role="status"
      className={`no-print flex flex-wrap items-center justify-center gap-x-3 gap-y-1 border-b px-4 py-2 text-center text-[14px] text-ink ${errore ? "border-danger/40 bg-danger-bg" : "border-warn/40 bg-warn-bg"}`}
    >
      <span className="inline-flex items-center gap-2">
        <AlertTriangle className={`size-4 shrink-0 ${errore ? "text-danger" : "text-warn"}`} aria-hidden />
        <b>{conto.testo}</b>
      </span>
      {!qui && (
        <Link href="/impostazioni/abbonamento" className="font-semibold text-band underline">
          Vai ad Abbonamento
        </Link>
      )}
    </p>
  );
}
