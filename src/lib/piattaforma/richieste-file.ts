import { randomBytes } from "node:crypto";
import { deposito } from "@/lib/deposito";
import { DocumentoIlleggibile } from "@/lib/deposito/tipi";
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

export async function salvaFileRichiesta(aziendaId: string, tipo: TipoRichiesta, dati: Uint8Array): Promise<string> {
  const fileId = `${randomBytes(16).toString("hex")}.${RICHIESTA_ESTENSIONE[tipo]}`;
  await deposito().salvaFile(aziendaId, "richieste", fileId, dati, { soloSeNuovo: true });
  return fileId;
}

export async function leggiFileRichiesta(aziendaId: string, fileId: string): Promise<Buffer | null> {
  if (!FILE_RICHIESTA.test(fileId)) return null;
  try {
    return await deposito().leggiFile(aziendaId, "richieste", fileId);
  } catch {
    return null;
  }
}

// L'indice è il documento "richieste" del deposito: le scritture vanno in fila lì.
// Assente o corrotto (DocumentoIlleggibile): elenco vuoto. Ogni altro errore (database, rete) arriva a chi chiama.
async function leggiIndice(aziendaId: string): Promise<VoceRichiesta[]> {
  try {
    const v = await deposito().leggiDocumento<unknown>(aziendaId, "richieste");
    return Array.isArray(v) ? (v as VoceRichiesta[]) : [];
  } catch (e) {
    if (!(e instanceof DocumentoIlleggibile)) throw e;
    console.error("Registro delle richieste non leggibile", aziendaId, e);
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
