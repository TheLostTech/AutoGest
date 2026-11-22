// Codici invito per la registrazione: elenco e creazione. Solo super admin con codice dal telefono verificato.
import { connection } from "next/server";
import { superadminDaRichiesta } from "@/lib/accesso/server";
import { creaInvito, elencoInviti } from "@/lib/piattaforma/inviti";
import { contesto, daAltroSito, errore, leggiJson, ok, testo } from "@/lib/piattaforma/server";

export async function GET(req: Request) {
  await connection();
  const g = await superadminDaRichiesta(req);
  if (g instanceof Response) return g;
  const c = await contesto();
  return ok({ inviti: await elencoInviti(c) });
}

export async function POST(req: Request) {
  const g = await superadminDaRichiesta(req);
  if (g instanceof Response) return g;
  const x = daAltroSito(req, true);
  if (x) return x;
  const corpo = await leggiJson(req);
  const nota = corpo?.nota == null || corpo.nota === "" ? "" : testo(corpo.nota, 0, 120);
  if (nota === null) return errore(400, "La nota può avere al massimo 120 caratteri.");
  const c = await contesto();
  const { codice, scade } = await creaInvito(c, g.utente.id, nota);
  return ok({ codice, link: `/registrati?invito=${codice}`, scade: new Date(scade).toISOString() }, 201);
}
