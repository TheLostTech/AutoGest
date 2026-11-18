// Stato di una visura chiesta a Openapi; quando è pronta il server scarica il PDF e ne dà l'indirizzo.
import { connection } from "next/server";
import { altroSito } from "@/lib/collegamenti-server";
import { credenziali, ErroreVisura, idValido, statoVisura } from "@/lib/visura-server";

const json = (body: unknown, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "no-store" } });

export async function GET(req: Request, ctx: { params: Promise<{ id: string }> }) {
  await connection();
  if (altroSito(req)) return json({ error: "Richiesta da un altro sito" }, 403);
  const { id } = await ctx.params;
  if (!idValido(id)) return json({ error: "Richiesta sconosciuta" }, 400);
  const c = await credenziali();
  if (!c) return json({ error: "Openapi non è configurato per la visura PRA" }, 409);
  try {
    return json(await statoVisura(c, id));
  } catch (e) {
    return json({ error: e instanceof ErroreVisura ? e.message : "Controllo non riuscito" }, e instanceof ErroreVisura ? e.status : 500);
  }
}
