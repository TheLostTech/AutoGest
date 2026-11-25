"use client";

import { useEffect, useState } from "react";
import { moduliDaAbbonamento, type Abbonamento } from "@/lib/abbonamento";
import { fetchAzienda } from "@/lib/accesso/azienda-client";
import { intestazioniPassive } from "@/lib/accesso/attivita";
import { BRAND } from "@/lib/config";
import { LISTINO } from "@/lib/listino";
import type { Modulo } from "@/lib/moduli";
import { ricaricaAbbonamento } from "@/lib/use-abbonamento";
import { ButtonLink, Notice } from "@/components/ui";

export type EsitoFatto =
  | { tipo: "attesa" }
  | { tipo: "pagata"; moduli: Modulo[] }
  | { tipo: "in-corso"; sessionId: string }
  | { tipo: "errore"; messaggio: string };

// Pagamento non ancora confermato (SEPA o simili): si ricontrolla ogni 3 secondi per 2 minuti
const OGNI_MS = 3_000;
const PER_MS = 120_000;

export function FattoView({ esito }: { esito: EsitoFatto }) {
  const [pagati, setPagati] = useState<Modulo[] | null>(esito.tipo === "pagata" ? esito.moduli : null);
  const [finito, setFinito] = useState(false);
  const sessionId = esito.tipo === "in-corso" ? esito.sessionId : null;

  useEffect(() => {
    if (!sessionId) return;
    let attivo = true;
    const inizio = Date.now();
    let t: ReturnType<typeof setTimeout>;
    const giro = async () => {
      try {
        // Il server rilegge la sessione da Stripe e sincronizza senza limite (come al primo ritorno)
        const r = await fetchAzienda(`/api/abbonamento/checkout?session_id=${encodeURIComponent(sessionId)}`, { cache: "no-store", headers: intestazioniPassive() });
        const j = r.ok ? ((await r.json()) as { pagata?: boolean; abbonamento?: Abbonamento }) : null;
        if (!attivo) return;
        if (j?.pagata && j.abbonamento) {
          setPagati(moduliDaAbbonamento(j.abbonamento, Date.now()));
          void ricaricaAbbonamento();
          return;
        }
      } catch {
        // rete assente: si riprova al prossimo giro
      }
      if (!attivo) return;
      if (Date.now() - inizio >= PER_MS) setFinito(true);
      else t = setTimeout(giro, OGNI_MS);
    };
    t = setTimeout(giro, OGNI_MS);
    return () => {
      attivo = false;
      clearTimeout(t);
    };
  }, [sessionId]);

  return (
    <main className="grid min-h-dvh place-items-center bg-ground px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="code text-[28px] font-bold uppercase leading-none tracking-wide text-band">{BRAND.azienda}</div>
          <p className="mt-1 text-[14px] font-medium text-ink-3">Gestionale autodemolizione</p>
        </div>
        <div className="label-sheet space-y-4 p-5" aria-live="polite">
          {pagati ? (
            <>
              <h1 className="code text-[18px] font-bold uppercase tracking-wide text-ink">Fatto: moduli attivi</h1>
              <ul className="divide-y divide-hair-soft rounded-md border border-hair">
                {pagati.map((m) => (
                  <li key={m} className="flex min-h-11 items-center gap-2 px-4 font-semibold">
                    <span className="size-2.5 rounded-full bg-ok" aria-hidden />
                    {LISTINO[m].nome}
                  </li>
                ))}
              </ul>
              <ButtonLink href="/" size="lg" className="w-full">
                Vai a Oggi
              </ButtonLink>
            </>
          ) : esito.tipo === "errore" ? (
            <>
              <h1 className="code text-[18px] font-bold uppercase tracking-wide text-ink">Pagamento</h1>
              <div role="alert">
                <Notice tone="danger">{esito.messaggio}</Notice>
              </div>
              <ButtonLink href="/" variant="secondary" className="w-full">
                Torna al gestionale
              </ButtonLink>
            </>
          ) : esito.tipo === "attesa" ? (
            <>
              <h1 className="code text-[18px] font-bold uppercase tracking-wide text-ink">Pagamento</h1>
              <p className="text-ink-2">Controllo il pagamento con Stripe…</p>
            </>
          ) : (
            <>
              <h1 className="code text-[18px] font-bold uppercase tracking-wide text-ink">Pagamento in corso</h1>
              {finito ? (
                <Notice tone="warn">Stripe non ha ancora confermato il pagamento. Riapri questa pagina tra qualche minuto, oppure torna al gestionale.</Notice>
              ) : (
                <Notice>Pagamento in corso: ti avvisiamo qui appena Stripe conferma</Notice>
              )}
              <ButtonLink href="/" variant="secondary" className="w-full">
                Torna al gestionale
              </ButtonLink>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
