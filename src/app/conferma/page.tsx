import type { Metadata } from "next";
import { ConfermaView } from "./view";

// Il gettone sta nell'indirizzo: non va mandato ad altri siti come referrer
export const metadata: Metadata = { title: "Conferma l'email · Piazzale", referrer: "no-referrer", robots: { index: false } };
// Il gettone arriva dall'indirizzo: la pagina non si prepara in anticipo.
export const instant = false;

export default async function ConfermaPage({ searchParams }: { searchParams: Promise<{ token?: string | string[] }> }) {
  const { token } = await searchParams;
  return <ConfermaView token={(Array.isArray(token) ? token[0] : token) ?? ""} />;
}
