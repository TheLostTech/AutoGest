// PDF della visura PRA salvato nella cartella dati. Contiene dati personali dell'intestatario:
// nel prototipo non c'è login (vedi collegamenti-server.ts), prima della produzione va protetto.
import { connection } from "next/server";
import { leggiPdf } from "@/lib/visura-server";

export async function GET(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  await connection();
  const { id } = await ctx.params;
  const bytes = await leggiPdf(id);
  if (!bytes) return new Response("Visura non trovata", { status: 404 });
  return new Response(new Uint8Array(bytes), {
    headers: { "Content-Type": "application/pdf", "Content-Disposition": `inline; filename="visura-${id}.pdf"`, "Cache-Control": "private, no-store" },
  });
}
