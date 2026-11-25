import { randomBytes } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { cartellaAzienda } from "@/lib/server-data";
import { deposito } from "@/lib/deposito";
import { RICHIESTA_ESTENSIONE, type TipoRichiesta } from "@/lib/accesso/richieste";

// Richieste scritte: aziende/<id>/richieste/<casuale>.<ext> + un indice (registro.json) che dice a quale
// utente e a quale modifica si riferiscono, con data e autore.

export const FILE_RICHIESTA = /^[a-f0-9]{32}\.(pdf|jpg|png)$/;

export interface VoceRichiesta {
  userId: string;
  azione: string;
  quando: string;
  autore: string;
  fileId?: string;
  estremi?: string;
}

const dirRichieste = (aziendaId: string) => path.join(cartellaAzienda(aziendaId), "richieste");

export async function salvaFileRichiesta(aziendaId: string, tipo: TipoRichiesta, dati: Uint8Array): Promise<string> {
  const dir = dirRichieste(aziendaId);
  await mkdir(dir, { recursive: true });
  const fileId = `${randomBytes(16).toString("hex")}.${RICHIESTA_ESTENSIONE[tipo]}`;
  await writeFile(path.join(dir, fileId), dati, { flag: "wx" });
  return fileId;
}

export async function leggiFileRichiesta(aziendaId: string, fileId: string): Promise<Buffer | null> {
  if (!FILE_RICHIESTA.test(fileId)) return null;
  try {
    return await readFile(path.join(dirRichieste(aziendaId), fileId));
  } catch {
    return null;
  }
}

// L'indice è il documento "richieste" del deposito: le scritture vanno in fila lì.
async function leggiIndice(aziendaId: string): Promise<VoceRichiesta[]> {
  try {
    const v = await deposito().leggiDocumento<unknown>(aziendaId, "richieste");
    return Array.isArray(v) ? (v as VoceRichiesta[]) : [];
  } catch {
    return [];
  }
}

export const elencoRichieste = leggiIndice;

export function aggiungiRichiesta(aziendaId: string, voce: VoceRichiesta): Promise<void> {
  return deposito().aggiornaDocumento<VoceRichiesta[], void>(aziendaId, "richieste", (prima) => ({
    dati: [...(Array.isArray(prima) ? prima : []), voce],
    risultato: undefined,
  }));
}
