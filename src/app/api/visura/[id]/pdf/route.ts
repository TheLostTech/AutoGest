// PDF della visura PRA salvato nella cartella dati. Contiene dati personali dell'intestatario:
// nel prototipo non c'è login (vedi collegamenti-server.ts), prima della produzione va protetto
// con una sessione autorizzata a vedere il veicolo.
import { connection } from "next/server";
import { altroSito } from "@/lib/collegamenti-server";
import { leggiPdf } from "@/lib/visura-server";

export async function GET(req: Request, ctx: { params: Promise<{ id: string }> }) {
  await connection();
  // Come le rotte sorelle: niente richieste da altri siti (né fetch, né incorporato in pagine altrui)
  if (altroSito(req) || req.headers.get("sec-fetch-site") === "cross-site") {
    return new Response("Richiesta non consentita", { status: 403 });
  }
  const { id } = await ctx.params;
  const bytes = await leggiPdf(id);
  if (!bytes) return new Response("Visura non trovata", { status: 404 });
  return new Response(new Uint8Array(bytes), {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `inline; filename="visura-${id}.pdf"`,
      "Cache-Control": "private, no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
