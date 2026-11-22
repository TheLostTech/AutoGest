// Chi è collegato e a quale azienda: il client lo usa per ruoli, nome e fascia di assistenza.
import { connection } from "next/server";
import { accessoDaRichiesta } from "@/lib/accesso/server";

export async function GET(req: Request) {
  await connection();
  const a = await accessoDaRichiesta(req);
  if (a instanceof Response) return a;
  return Response.json(a, { headers: { "Cache-Control": "no-store" } });
}
