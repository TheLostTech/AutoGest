// Deposito su disco: gli stessi percorsi di sempre sotto aziende/<id>/, così i dati locali esistenti restano leggibili.
import { randomBytes } from "node:crypto";
import { link, mkdir, readFile, rename, rm, unlink, writeFile } from "node:fs/promises";
import path from "node:path";
import type { StatoAccount } from "../accesso/tentativi-account";
import { creaUnaVolta } from "../file-una-volta";
import { inFilaPer } from "../fila";
import { cartellaAzienda } from "../server-data";
import { DocumentoIlleggibile, type CartellaFile, type Deposito, type TipoDocumento } from "./tipi";

const FILE_DOCUMENTO: Record<TipoDocumento, { file: string; mode: number }> = {
  archivio: { file: "state.json", mode: 0o666 },
  abbonamento: { file: "abbonamento.json", mode: 0o666 },
  collegamenti: { file: "collegamenti.json", mode: 0o600 },
  ebay: { file: "ebay.json", mode: 0o600 },
  richieste: { file: path.join("richieste", "registro.json"), mode: 0o666 },
};
const NOME_FILE = /^[A-Za-z0-9._-]{1,128}$/;
const assente = (e: unknown) => (e as NodeJS.ErrnoException).code === "ENOENT";

const percorsoDocumento = (aziendaId: string, tipo: TipoDocumento) => {
  const d = FILE_DOCUMENTO[tipo];
  if (!d) throw new Error("Tipo di documento non valido");
  return { ...d, percorso: path.join(cartellaAzienda(aziendaId), d.file) };
};
function percorsoFile(aziendaId: string, cartella: CartellaFile, nome: string): string {
  if (!NOME_FILE.test(nome) || nome.includes("..")) throw new Error("Nome di file non valido");
  // il registro delle richieste è un documento, non un file
  if (cartella === "richieste" && nome === "registro.json") throw new Error("Nome di file non valido");
  return path.join(cartellaAzienda(aziendaId), cartella, nome);
}

async function leggi<T>(aziendaId: string, tipo: TipoDocumento): Promise<T | null> {
  const { percorso } = percorsoDocumento(aziendaId, tipo);
  let testo: string;
  try {
    testo = await readFile(percorso, "utf8");
  } catch (e) {
    if (assente(e)) return null;
    throw e;
  }
  try {
    return JSON.parse(testo) as T;
  } catch (e) {
    throw new DocumentoIlleggibile(tipo, aziendaId, e);
  }
}

// Come creaUnaVolta ma per byte: file temporaneo completo, poi collegamento al nome finale (fallisce se c'è già).
async function creaFileUnaVolta(percorso: string, contenuto: Uint8Array, mode: number): Promise<boolean> {
  await mkdir(path.dirname(percorso), { recursive: true });
  const tmp = `${percorso}.${process.pid}.${randomBytes(4).toString("hex")}.tmp`;
  await writeFile(tmp, contenuto, { mode });
  try {
    await link(tmp, percorso);
    return true;
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "EEXIST") return false;
    throw e;
  } finally {
    await unlink(tmp).catch(() => undefined);
  }
}

async function scrivi(percorso: string, contenuto: string | Uint8Array, mode: number): Promise<void> {
  await mkdir(path.dirname(percorso), { recursive: true });
  const tmp = `${percorso}.${process.pid}.${randomBytes(4).toString("hex")}.tmp`;
  await writeFile(tmp, contenuto, { mode });
  try {
    await rename(tmp, percorso);
  } catch (e) {
    await unlink(tmp).catch(() => undefined);
    throw e;
  }
}

// Conti dei tentativi di accesso: in memoria sulla globalThis, come oggi (un solo processo Node).
const g = globalThis as typeof globalThis & { __depositoConti?: Map<string, StatoAccount> };
const conti = (g.__depositoConti ??= new Map());

export function depositoDisco(): Deposito {
  return {
    leggiDocumento: (aziendaId, tipo) => leggi(aziendaId, tipo),

    async aggiornaDocumento(aziendaId, tipo, fn) {
      const { percorso, mode } = percorsoDocumento(aziendaId, tipo);
      return inFilaPer("deposito-documento", `${aziendaId}/${tipo}`, async () => {
        const m = await fn(await leggi(aziendaId, tipo));
        if (!m.nonScrivere) await scrivi(percorso, JSON.stringify(m.dati), mode);
        return m.risultato;
      });
    },

    async creaDocumento(aziendaId, tipo, dati) {
      const { percorso, mode } = percorsoDocumento(aziendaId, tipo);
      return inFilaPer("deposito-documento", `${aziendaId}/${tipo}`, async () => {
        await mkdir(path.dirname(percorso), { recursive: true });
        return creaUnaVolta(percorso, JSON.stringify(dati), mode);
      });
    },

    async salvaFile(aziendaId, cartella, nome, dati, opz) {
      const percorso = percorsoFile(aziendaId, cartella, nome);
      if (!opz?.soloSeNuovo) {
        await scrivi(percorso, dati, 0o666);
        return true;
      }
      return creaFileUnaVolta(percorso, dati, 0o666);
    },

    async leggiFile(aziendaId, cartella, nome) {
      try {
        return await readFile(percorsoFile(aziendaId, cartella, nome));
      } catch (e) {
        if (assente(e)) return null;
        throw e;
      }
    },

    async togliAzienda(aziendaId) {
      await rm(cartellaAzienda(aziendaId), { recursive: true, force: true });
    },

    aggiornaContoAccount(chiave, fn) {
      return inFilaPer("deposito-conto-account", chiave, async () => {
        const { stato, risultato } = fn(conti.get(chiave));
        conti.set(chiave, stato);
        return risultato;
      });
    },
  };
}
