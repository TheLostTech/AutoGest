import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { AccessoView } from "./view";
import { percorsoDaSicuro } from "@/lib/accesso/percorsi";
import { demoPubblica } from "@/lib/accesso/demo-pubblica";
import { avvisoConferma } from "@/lib/accesso/conferma";

const primo = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);

export const metadata: Metadata = { title: "Accedi · Gestionale" };
// Il percorso di ritorno arriva dall'indirizzo: la pagina non si prepara in anticipo.
export const instant = false;

type Parametri = { da?: string | string[]; manuale?: string; confermata?: string | string[]; error?: string | string[] };

export default async function AccessoPage({ searchParams }: { searchParams: Promise<Parametri> }) {
  const { da, manuale, confermata, error } = await searchParams;
  const ritorno = percorsoDaSicuro(primo(da));
  // Arrivo dal link dell'email di conferma (?confermata=1, con &error=… se il link è scaduto o non valido)
  const avviso = avvisoConferma(primo(confermata), primo(error));
  // Vetrina online: niente credenziali, si rientra nella demo (anche quando la sessione si perde). ?manuale=1 per il login vero.
  if (demoPubblica() && manuale !== "1" && !avviso) redirect(`/demo?da=${encodeURIComponent(ritorno)}`);
  return <AccessoView da={ritorno} avviso={avviso} />;
}
