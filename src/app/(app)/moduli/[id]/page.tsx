import { notFound } from "next/navigation";
import { ORDINE_MODULI, type Modulo } from "@/lib/moduli";
import ModuloView from "./view";

// I quattro moduli sono noti: si prerenderizzano tutti, il parametro sceglie solo quale mostrare.
export const instant = false;

export function generateStaticParams() {
  return ORDINE_MODULI.map((id) => ({ id }));
}

export default async function ModuloPage({ params }: PageProps<"/moduli/[id]">) {
  const { id } = await params;
  if (!ORDINE_MODULI.includes(id as Modulo)) notFound();
  return <ModuloView modulo={id as Modulo} />;
}
