import { redirect } from "next/navigation";
import { splitShelfCode } from "@/lib/warehouse";

// Il QR dell'etichetta scaffale porta qui: si apre la mappa su quello scaffale.
export default async function OpenShelf({ params }: { params: Promise<{ loc: string[] }> }) {
  const { loc } = await params;
  const l = splitShelfCode(loc.map(decodeURIComponent).join("/"));
  if (!l) redirect("/magazzino");
  redirect(`/magazzino?${new URLSearchParams({ mag: l.mag, c: l.corsia, s: l.scaffale, r: l.ripiano })}`);
}
