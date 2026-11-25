import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { AccessoView } from "./view";
import { percorsoDaSicuro } from "@/lib/accesso/percorsi";
import { demoPubblica } from "@/lib/accesso/demo-pubblica";

export const metadata: Metadata = { title: "Accedi · Gestionale" };
// Il percorso di ritorno arriva dall'indirizzo: la pagina non si prepara in anticipo.
export const instant = false;

export default async function AccessoPage({ searchParams }: { searchParams: Promise<{ da?: string | string[]; manuale?: string }> }) {
  const { da, manuale } = await searchParams;
  const ritorno = percorsoDaSicuro(Array.isArray(da) ? da[0] : da);
  // Vetrina online: niente credenziali, si rientra nella demo (anche quando la sessione si perde). ?manuale=1 per il login vero.
  if (demoPubblica() && manuale !== "1") redirect(`/demo?da=${encodeURIComponent(ritorno)}`);
  return <AccessoView da={ritorno} />;
}
