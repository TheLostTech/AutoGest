// Giro giornaliero degli avvisi di fine prova. Lo chiama Vercel (vercel.json) con "Authorization: Bearer <CRON_SECRET>":
// senza il segreto giusto 401, prima di toccare qualunque dato. La risposta contiene solo conteggi.
import { connection } from "next/server";
import { segretoValido } from "@/lib/avvisi-prova";
import { mandaAvvisiProva } from "@/lib/avvisi-prova-server";
import { contesto } from "@/lib/piattaforma/server";

const NO_STORE = { "Cache-Control": "no-store" };

export async function GET(req: Request) {
  await connection();
  if (!segretoValido(req.headers.get("authorization"), process.env.CRON_SECRET)) {
    return Response.json({ error: "Non autorizzato." }, { status: 401, headers: NO_STORE });
  }
  try {
    const esito = await mandaAvvisiProva(await contesto(), Date.now());
    return Response.json(esito, { headers: NO_STORE });
  } catch (e) {
    console.error("Avvisi di fine prova: giro non riuscito", e instanceof Error ? e.message : "errore");
    return Response.json({ error: "Giro non riuscito." }, { status: 500, headers: NO_STORE });
  }
}
