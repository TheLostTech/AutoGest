// Ritorno da Stripe Checkout: il server legge la sessione e, se è pagata, sincronizza subito, senza aspettare l'avviso
// di Stripe (spec registrazione-pagamento, sezione 4). Fuori da AppShell: qui il riquadro di pagamento non si apre.
import { Suspense } from "react";
import type { Metadata } from "next";
import { headers } from "next/headers";
import { moduliDaAbbonamento } from "@/lib/abbonamento";
import { accessoDaRichiesta } from "@/lib/accesso/server";
import { esitoCheckout } from "@/lib/stripe/server";
import { FattoView, type EsitoFatto } from "./view";

export const metadata: Metadata = { title: "Abbonamento · Gestionale", robots: { index: false } };
// Dipende dalla sessione e dall'indirizzo: la pagina non si prepara in anticipo.
export const instant = false;

type Props = { searchParams: Promise<{ session_id?: string | string[] }> };

async function esito(searchParams: Props["searchParams"]): Promise<EsitoFatto> {
  const { session_id } = await searchParams;
  const sessionId = (Array.isArray(session_id) ? session_id[0] : session_id) ?? "";
  // accessoDaRichiesta legge la sessione dalle intestazioni: la richiesta si ricostruisce da quelle della pagina
  const a = await accessoDaRichiesta(new Request("http://gestionale.local/abbonamento/fatto", { headers: new Headers(await headers()) }));
  if (a instanceof Response) {
    const j = (await a.json().catch(() => null)) as { error?: string } | null;
    return { tipo: "errore", messaggio: j?.error ?? "Accedi per continuare." };
  }
  if (!a.azienda.registrata || !(a.ruoli.includes("responsabile") || a.assistenza)) {
    return { tipo: "errore", messaggio: "Il pagamento dell'abbonamento lo vede solo il titolare." };
  }
  const e = await esitoCheckout(a.azienda.id, sessionId);
  if ("errore" in e) return { tipo: "errore", messaggio: e.errore };
  if (e.pagata) return { tipo: "pagata", moduli: moduliDaAbbonamento(e.abbonamento) };
  return { tipo: "in-corso", sessionId };
}

async function Esito({ searchParams }: Props) {
  return <FattoView esito={await esito(searchParams)} />;
}

export default function FattoPage({ searchParams }: Props) {
  return (
    <Suspense fallback={<FattoView esito={{ tipo: "attesa" }} />}>
      <Esito searchParams={searchParams} />
    </Suspense>
  );
}
