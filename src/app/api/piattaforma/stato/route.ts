// Stato del super admin per l'area Piattaforma: chi è e se il codice dal telefono è attivo e verificato.
// Non chiede il codice (serve a raggiungere la pagina Sicurezza prima di attivarlo).
import { connection } from "next/server";
import { ASSISTENZA_MS } from "@/lib/accesso/regole";
import { superadminBase, ok } from "@/lib/piattaforma/server";

export async function GET(req: Request) {
  await connection();
  const s = await superadminBase(req);
  if (s.risposta) return s.risposta;
  const pubblico = { utente: s.sessione.utente, dueFattoriAttivo: s.sessione.dueFattoriAttivo, dueFattoriVerificato: s.sessione.dueFattoriVerificato, aziendaAttiva: s.sessione.aziendaAttiva };
  return ok({ ...pubblico, assistenzaMinuti: ASSISTENZA_MS / 60_000 });
}
