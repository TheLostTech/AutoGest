import type { Metadata } from "next";
import { RegistratiView } from "./view";

export const metadata: Metadata = { title: "Registrati · Gestionale", robots: { index: false } };
// Il codice invito arriva dall'indirizzo: la pagina non si prepara in anticipo.
export const instant = false;

export default async function RegistratiPage({ searchParams }: { searchParams: Promise<{ invito?: string | string[] }> }) {
  const { invito } = await searchParams;
  const codice = (Array.isArray(invito) ? invito[0] : invito) ?? "";
  return <RegistratiView invito={codice.slice(0, 40)} />;
}
