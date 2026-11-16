import { redirect } from "next/navigation";

// Il QR contiene solo l'ID: questo indirizzo apre la scheda corretta.
export default async function OpenPart({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  redirect(`/ricambi/${encodeURIComponent(id.toUpperCase())}`);
}
