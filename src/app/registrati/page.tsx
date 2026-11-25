import type { Metadata } from "next";
import { modalitaStripe } from "@/lib/stripe/server";
import { RegistratiView } from "./view";

export const metadata: Metadata = { title: "Registrati · Gestionale", robots: { index: false } };

export default async function RegistratiPage() {
  // La riga "Ambiente di prova" solo con le chiavi di prova di Stripe
  return <RegistratiView prova={modalitaStripe() === "prova"} />;
}
