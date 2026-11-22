// Visura PRA: GET dice come lavora (Simulato, Sandbox, Produzione), POST chiede la visura a Openapi.
// Il token resta sul server (vedi visura-server.ts), uno per azienda. Senza Openapi configurato la pratica usa la visura simulata.
import { connection } from "next/server";
import { accessoDaRichiesta, soloRuoli } from "@/lib/accesso/server";
import { altroSito, richiestaDellApp } from "@/lib/collegamenti-server";
import { moduloAttivoSulServer } from "@/lib/moduli-server";
import { credenziali, ErroreVisura, richiediVisura, TIPI_VEICOLO, type TipoVeicolo } from "@/lib/visura-server";

const json = (body: unknown, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "no-store" } });

export async function GET(req: Request) {
  await connection();
  if (altroSito(req)) return json({ error: "Richiesta da un altro sito" }, 403);
  const acc = await accessoDaRichiesta(req);
  if (acc instanceof Response) return acc;
  try {
    return json({ modo: (await credenziali(acc.azienda.id))?.modo ?? "Simulato" });
  } catch (e) {
    return json({ error: e instanceof ErroreVisura ? e.message : "Controllo non riuscito" }, e instanceof ErroreVisura ? e.status : 500);
  }
}

export async function POST(req: Request) {
  await connection();
  // Ogni visura costa: solo richieste partite dall'app, solo da chi fa le pratiche
  if (!richiestaDellApp(req)) return json({ error: "Richiesta da un altro sito" }, 403);
  const acc = await accessoDaRichiesta(req);
  if (acc instanceof Response) return acc;
  const vietato = soloRuoli(acc, "accettazione", "responsabile");
  if (vietato) return vietato;
  // La visura è del modulo Accettazione: spento per l'azienda della sessione, la richiesta non parte nemmeno per vie traverse
  if (!(await moduloAttivoSulServer(acc.azienda.id, "accettazione"))) return json({ error: "Il modulo Accettazione non è attivo" }, 403);
  const body = (await req.json().catch(() => null)) as { targa?: unknown; tipo?: unknown } | null;
  const targa = String(body?.targa ?? "").replace(/\s+/g, "").toUpperCase();
  const tipo = String(body?.tipo ?? "AUTOVEICOLO") as TipoVeicolo;
  if (!/^[A-Z0-9]{5,8}$/.test(targa)) return json({ error: "Targa non valida" }, 400);
  if (!TIPI_VEICOLO.includes(tipo)) return json({ error: "Tipo di veicolo non valido" }, 400);
  try {
    const c = await credenziali(acc.azienda.id);
    if (!c) return json({ error: "Openapi non è configurato per la visura PRA" }, 409);
    const r = await richiediVisura(c, targa, tipo);
    return json({ ...r, modo: c.modo });
  } catch (e) {
    return json({ error: e instanceof ErroreVisura ? e.message : "Richiesta non riuscita" }, e instanceof ErroreVisura ? e.status : 500);
  }
}
