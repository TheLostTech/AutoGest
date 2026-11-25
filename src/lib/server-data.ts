import path from "node:path";
import { idAziendaValido } from "./accesso/id-azienda";

// Dove il server tiene i dati condivisi dell'azienda (archivio e foto).
// Di serie è la cartella .demo-data del progetto; sul server dell'azienda si sceglie con DATI_DIR,
// es. D:\AutoGest\dati su Windows Server: per il backup basta copiare quella cartella.
// Con il deposito Supabase (cloud) questa cartella non si usa: documenti e file passano dal deposito (src/lib/deposito),
// utenti e sessioni da Postgres (src/lib/db/pool.ts).
export const DATA_DIR = path.resolve(/*turbopackIgnore: true*/ process.env.DATI_DIR || path.join(process.cwd(), ".demo-data"));
// Solo per copiare i dati storici nell'azienda demo (Task 9): le foto vere stanno in cartellaFotoAzienda.
export const PHOTO_DIR = path.join(DATA_DIR, "foto");
// Database della piattaforma: utenti, aziende, ruoli e sessioni (Better Auth).
export const DB_FILE = path.join(DATA_DIR, "piattaforma.sqlite");

// Ogni azienda ha la sua cartella: aziende/<id>/ (archivio, foto, collegamenti, richieste).
// L'id arriva sempre dalla sessione, ma si controlla comunque: diventa un nome di cartella.
export function cartellaAzienda(id: string): string {
  if (!idAziendaValido(id)) throw new Error("Id azienda non valido");
  return path.join(DATA_DIR, "aziende", id);
}
export function cartellaFotoAzienda(id: string): string {
  return path.join(cartellaAzienda(id), "foto");
}
// Allegati PDF della pratica (es. ricevuta di avvenuta radiazione)
export function cartellaAllegatiAzienda(id: string): string {
  return path.join(cartellaAzienda(id), "allegati");
}
