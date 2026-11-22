// Catalogo pubblico del negozio: solo gli annunci online (o eBay) con i campi che le pagine pubbliche leggono.
// Senza accesso: mai altro dell'archivio dell'azienda (vedi catalogo-pubblico.ts).
import { connection } from "next/server";
import { leggiStato } from "@/lib/archivio-azienda";
import { catalogoPubblico } from "@/lib/catalogo-pubblico";
import { datiNegozio, risposta } from "@/lib/negozio-server";

export async function GET() {
  await connection();
  const negozio = await datiNegozio();
  if (!negozio) return risposta({ annunci: [], parts: [], vehicles: [], pagamentoAttivo: false });
  try {
    const s = await leggiStato(negozio.id);
    return risposta({ ...catalogoPubblico((s.state ?? {}) as Parameters<typeof catalogoPubblico>[0]), pagamentoAttivo: negozio.demo });
  } catch (e) {
    console.error("Catalogo del negozio non leggibile", e);
    return risposta({ error: "Il catalogo non è disponibile in questo momento." }, 503);
  }
}
