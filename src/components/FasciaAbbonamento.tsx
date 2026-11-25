"use client";

// Fascia in cima al gestionale, solo per il titolare: prova gratuita in corso, pagamento non riuscito, oppure disdetta
// negli ultimi 7 giorni (spec registrazione-pagamento, sezione 6; prova-15-giorni, sezione 4). Il testo è la riga del
// conto alla rovescia. In prova c'è "Scegli i moduli" verso la pagina Abbonamento; negli ultimi 3 giorni (tono
// "avviso") la fascia è più evidente. L'ora è quella del browser (useOra), mai del server.
import Link from "next/link";
import { AlertTriangle, Clock } from "lucide-react";
import { contoAllaRovescia, fasciaDaMostrare, inProva, type Abbonamento } from "@/lib/abbonamento";
import { useOra } from "@/lib/use-ora";
import { ButtonLink } from "./ui";

const ABBONAMENTO = "/impostazioni/abbonamento";

export function FasciaAbbonamento({ abbonamento, qui }: { abbonamento: Abbonamento; qui: boolean }) {
  const ora = useOra();
  if (!ora || !fasciaDaMostrare(abbonamento, ora)) return null;
  const conto = contoAllaRovescia(abbonamento, ora);
  if (!conto) return null;
  const errore = conto.tono === "errore";
  const avviso = conto.tono === "avviso";

  if (inProva(abbonamento, ora)) {
    const Icona = avviso ? AlertTriangle : Clock;
    return (
      <p
        role="status"
        className={`no-print flex flex-wrap items-center justify-center gap-x-4 gap-y-2 px-4 text-center text-ink ${
          avviso ? "border-b-2 border-warn bg-warn-bg py-2.5 text-[16px]" : "border-b border-band/25 bg-band-tint py-2 text-[14px]"
        }`}
      >
        <span className="inline-flex items-center gap-2">
          <Icona className={`shrink-0 ${avviso ? "size-5 text-warn" : "size-4 text-band"}`} aria-hidden />
          <b>{conto.testo}</b>
        </span>
        {!qui && (
          <ButtonLink href={ABBONAMENTO} size="sm" variant={avviso ? "primary" : "secondary"}>
            Scegli i moduli
          </ButtonLink>
        )}
      </p>
    );
  }

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
        <Link href={ABBONAMENTO} className="font-semibold text-band underline">
          Vai ad Abbonamento
        </Link>
      )}
    </p>
  );
}
