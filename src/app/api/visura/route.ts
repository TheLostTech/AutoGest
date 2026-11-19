// Visura PRA: GET dice come lavora (Simulato, Sandbox, Produzione), POST chiede la visura a Openapi.
// Il token resta sul server (vedi visura-server.ts). Senza Openapi configurato la pratica usa la visura simulata.
import { connection } from "next/server";
import { altroSito, richiestaDellApp } from "@/lib/collegamenti-server";
import { moduloAttivoSulServer } from "@/lib/moduli-server";
import { credenziali, ErroreVisura, richiediVisura, TIPI_VEICOLO, type TipoVeicolo } from "@/lib/visura-server";

const json = (body: unknown, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "no-store" } });

export async function GET(req: Request) {
  await connection();
  if (altroSito(req)) return json({ error: "Richiesta da un altro sito" }, 403);
  return json({ modo: (await credenziali())?.modo ?? "Simulato" });
}

export async function POST(req: Request) {
  // Ogni visura costa: solo richieste partite dall'app
  if (!richiestaDellApp(req)) return json({ error: "Richiesta da un altro sito" }, 403);
  // La visura è del modulo Accettazione: spento, la richiesta non parte nemmeno per vie traverse
  if (!(await moduloAttivoSulServer("accettazione"))) return json({ error: "Il modulo Accettazione non è attivo" }, 403);
  const body = (await req.json().catch(() => null)) as { targa?: unknown; tipo?: unknown } | null;
  const targa = String(body?.targa ?? "").replace(/\s+/g, "").toUpperCase();
  const tipo = String(body?.tipo ?? "AUTOVEICOLO") as TipoVeicolo;
  if (!/^[A-Z0-9]{5,8}$/.test(targa)) return json({ error: "Targa non valida" }, 400);
  if (!TIPI_VEICOLO.includes(tipo)) return json({ error: "Tipo di veicolo non valido" }, 400);
  const c = await credenziali();
  if (!c) return json({ error: "Openapi non è configurato per la visura PRA" }, 409);
  try {
    const r = await richiediVisura(c, targa, tipo);
    return json({ ...r, modo: c.modo });
  } catch (e) {
    return json({ error: e instanceof ErroreVisura ? e.message : "Richiesta non riuscita" }, e instanceof ErroreVisura ? e.status : 500);
  }
}
