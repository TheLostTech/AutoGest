// Il deposito è l'unico punto da cui il resto dell'app legge e scrive documenti e file delle aziende.
// Ha due realizzazioni: su disco (prototipo, prove) e su Supabase. Le prove di contratto sono le stesse per entrambe.
import type { StatoAccount } from "../accesso/tentativi-account";

export type TipoDocumento = "archivio" | "abbonamento" | "collegamenti" | "ebay" | "richieste";
export type CartellaFile = "foto" | "allegati" | "visure" | "richieste";

/** Esito di una modifica: i dati nuovi, il valore da restituire a chi chiama e, se serve, il "non scrivere nulla". */
export interface Modifica<T, R> {
  dati: T;
  risultato: R;
  nonScrivere?: boolean;
}

/** Il documento c'è ma non si legge (JSON rovinato): non si sovrascrive mai, si segnala. */
export class DocumentoIlleggibile extends Error {
  readonly tipo: TipoDocumento;
  readonly aziendaId: string;
  constructor(tipo: TipoDocumento, aziendaId: string, causa?: unknown) {
    super(`Documento ${tipo} dell'azienda ${aziendaId} illeggibile`, { cause: causa });
    this.name = "DocumentoIlleggibile";
    this.tipo = tipo;
    this.aziendaId = aziendaId;
  }
}

export interface Deposito {
  leggiDocumento<T>(aziendaId: string, tipo: TipoDocumento): Promise<T | null>;
  /** Lettura e scrittura atomiche per (azienda, tipo): le chiamate sulla stessa coppia vanno una dopo l'altra. */
  aggiornaDocumento<T, R>(
    aziendaId: string,
    tipo: TipoDocumento,
    fn: (prima: T | null) => Modifica<T, R> | Promise<Modifica<T, R>>,
  ): Promise<R>;
  /** false se il documento c'era già (in quel caso non si tocca). */
  creaDocumento<T>(aziendaId: string, tipo: TipoDocumento, dati: T): Promise<boolean>;
  /** false se `soloSeNuovo` e il file c'era già. */
  salvaFile(
    aziendaId: string,
    cartella: CartellaFile,
    nome: string,
    dati: Uint8Array,
    opz?: { soloSeNuovo?: boolean },
  ): Promise<boolean>;
  leggiFile(aziendaId: string, cartella: CartellaFile, nome: string): Promise<Buffer | null>;
  /** Toglie documenti e file dell'azienda. */
  togliAzienda(aziendaId: string): Promise<void>;
  aggiornaContoAccount<R>(
    chiave: string,
    fn: (prima: StatoAccount | undefined) => { stato: StatoAccount; risultato: R },
  ): Promise<R>;
}
