// Battito del blocco di inattività: la persona ha toccato lo schermo o premuto un tasto. Per una sessione da PIN
// segna l'attività sul server all'istante dell'ultimo tocco (le letture automatiche non la segnano).
// Al massimo uno al minuto per scheda. L'istante mandato dal browser può solo accorciare: il server non va mai oltre adesso.
import { connection } from "next/server";
import { accessoDaRichiesta } from "@/lib/accesso/server";

export async function POST(req: Request) {
  await connection();
  const corpo = (await req.json().catch(() => ({}))) as { ultimoTocco?: unknown };
  const t = typeof corpo.ultimoTocco === "number" && Number.isFinite(corpo.ultimoTocco) ? corpo.ultimoTocco : Date.now();
  const a = await accessoDaRichiesta(req, { attivitaAlle: t });
  if (a instanceof Response) return a;
  return new Response(null, { status: 204, headers: { "Cache-Control": "no-store" } });
}
