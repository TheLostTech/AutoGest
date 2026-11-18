// PDF della visura PRA salvato nella cartella dell'azienda. Contiene dati personali dell'intestatario:
// lo vede solo chi ha una sessione valida in quell'azienda (l'azienda viene dalla sessione, mai dall'indirizzo).
import { connection } from "next/server";
import { accessoDaRichiesta } from "@/lib/accesso/server";
import { altroSito } from "@/lib/collegamenti-server";
import { leggiPdf } from "@/lib/visura-server";

export async function GET(req: Request, ctx: { params: Promise<{ id: string }> }) {
  await connection();
  // Come le rotte sorelle: niente richieste da altri siti (né fetch, né incorporato in pagine altrui)
  if (altroSito(req) || req.headers.get("sec-fetch-site") === "cross-site") {
    return new Response("Richiesta non consentita", { status: 403 });
  }
  const acc = await accessoDaRichiesta(req);
  if (acc instanceof Response) return acc;
  const { id } = await ctx.params;
  const bytes = await leggiPdf(acc.azienda.id, id);
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
