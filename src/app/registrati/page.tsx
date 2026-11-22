import type { Metadata } from "next";
import { modalitaStripe } from "@/lib/stripe/server";
import { RegistratiView } from "./view";

export const metadata: Metadata = { title: "Registrati · Gestionale", robots: { index: false } };
// Il codice invito arriva dall'indirizzo: la pagina non si prepara in anticipo.
export const instant = false;

export default async function RegistratiPage({ searchParams }: { searchParams: Promise<{ invito?: string | string[] }> }) {
  const { invito } = await searchParams;
  const codice = (Array.isArray(invito) ? invito[0] : invito) ?? "";
  // La riga "Ambiente di prova" solo con le chiavi di prova di Stripe
  return <RegistratiView invito={codice.slice(0, 40)} prova={modalitaStripe() === "prova"} />;
}
