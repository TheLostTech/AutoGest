import type { Metadata } from "next";
import { AccessoView } from "./view";
import { percorsoDaSicuro } from "@/lib/accesso/percorsi";

export const metadata: Metadata = { title: "Accedi · Gestionale" };
// Il percorso di ritorno arriva dall'indirizzo: la pagina non si prepara in anticipo.
export const instant = false;

export default async function AccessoPage({ searchParams }: { searchParams: Promise<{ da?: string | string[] }> }) {
  const { da } = await searchParams;
  return <AccessoView da={percorsoDaSicuro(Array.isArray(da) ? da[0] : da)} />;
}
