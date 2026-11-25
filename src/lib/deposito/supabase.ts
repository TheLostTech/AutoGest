// Deposito su Supabase (cloud): documenti e conti dei tentativi in Postgres (tabelle documento e conto_account,
// create da preparaSchema all'avvio), file nello spazio privato di Supabase (Storage, bucket "piazzale").
// Solo server: la chiave service_role non esce mai da qui e a chi chiama arrivano solo byte, mai indirizzi di
// supabase.co. Le due parti sono separate (SpazioFile) così i documenti si provano anche senza lo spazio.
import { createClient } from "@supabase/supabase-js";
import type { Pool, PoolClient } from "pg";
import { idAziendaValido } from "../accesso/id-azienda";
import type { StatoAccount } from "../accesso/tentativi-account";
import type { CartellaFile, Deposito, TipoDocumento } from "./tipi";

/** Dove stanno i byte dei file. I percorsi arrivano già controllati: <aziendaId>/<cartella>/<nome>. */
export interface SpazioFile {
  /** false se `soloSeNuovo` e il file c'era già. */
  salva(percorso: string, dati: Uint8Array, soloSeNuovo: boolean): Promise<boolean>;
  leggi(percorso: string): Promise<Buffer | null>;
  /** Toglie tutti i file sotto `<prefisso>/`. */
  togliSotto(prefisso: string): Promise<void>;
}

// Stessi controlli del disco (disco.ts)
const TIPI: readonly TipoDocumento[] = ["archivio", "abbonamento", "collegamenti", "ebay", "richieste", "registrazione"];
const CARTELLE: readonly CartellaFile[] = ["foto", "allegati", "visure", "richieste"];
const NOME_FILE = /^[A-Za-z0-9._-]{1,128}$/;

function azienda(id: string): string {
  if (!idAziendaValido(id)) throw new Error("Id azienda non valido");
  return id;
}
function documento(aziendaId: string, tipo: TipoDocumento): [string, TipoDocumento] {
  azienda(aziendaId);
  if (!TIPI.includes(tipo)) throw new Error("Tipo di documento non valido");
  return [aziendaId, tipo];
}
function percorsoFile(aziendaId: string, cartella: CartellaFile, nome: string): string {
  azienda(aziendaId);
  if (!CARTELLE.includes(cartella)) throw new Error("Cartella non valida");
  if (!NOME_FILE.test(nome) || nome.includes("..")) throw new Error("Nome di file non valido");
  // il registro delle richieste è un documento, non un file
  if (cartella === "richieste" && nome === "registro.json") throw new Error("Nome di file non valido");
  return `${aziendaId}/${cartella}/${nome}`;
}

// Limiti dentro il database, solo per questa transazione (come SET LOCAL): un'istruzione che dura più di 15 secondi
// si ferma, e così una transazione lasciata aperta senza lavoro (che terrebbe bloccata la riga "for update").
// Qui e non nei parametri d'avvio della connessione: il pooler di Supabase (modalità transazione) non li applica.
export const SQL_TEMPI =
  "select set_config('statement_timeout', '15s', true), set_config('idle_in_transaction_session_timeout', '15s', true)";

/**
 * Una transazione su una connessione del pool. `corpo` dice se confermare (commit) o annullare (rollback);
 * su errore si annulla. La connessione torna sempre al pool, e si butta se nemmeno il rollback riesce.
 */
async function transazione<R>(p: Pool, corpo: (c: PoolClient) => Promise<{ risultato: R; conferma: boolean }>): Promise<R> {
  const c = await p.connect();
  let rotta: Error | undefined;
  try {
    await c.query("begin");
    await c.query(SQL_TEMPI);
    const { risultato, conferma } = await corpo(c);
    await c.query(conferma ? "commit" : "rollback");
    return risultato;
  } catch (e) {
    try {
      await c.query("rollback");
    } catch (e2) {
      rotta = e2 instanceof Error ? e2 : new Error("rollback non riuscito");
    }
    throw e;
  } finally {
    c.release(rotta);
  }
}

// I dati vanno a Postgres come testo JSON: pg trasformerebbe un array JS in un array di Postgres, non in jsonb.
// jsonb non accetta il carattere NUL (\u0000): uno solo, incollato in un campo, farebbe fallire ogni salvataggio
// successivo dell'azienda. Si toglie da testi e nomi dei campi.
const senzaNul = (s: string) => s.replaceAll("\0", "");
export const json = (v: unknown) =>
  JSON.stringify(v, (_k, x: unknown) => {
    if (typeof x === "string") return senzaNul(x);
    if (x && typeof x === "object" && !Array.isArray(x) && Object.keys(x).some((k) => k.includes("\0"))) {
      return Object.fromEntries(Object.entries(x).map(([k, val]) => [senzaNul(k), val]));
    }
    return x;
  });

type StatoSalvato = { errori: number[]; bloccatoFino: number | null; inVolo: Record<string, number> };
const statoDaSalvare = (s: StatoAccount): StatoSalvato => ({
  errori: s.errori,
  bloccatoFino: s.bloccatoFino,
  inVolo: Object.fromEntries(s.inVolo),
});
const statoLetto = (s: StatoSalvato | null): StatoAccount | undefined =>
  s ? { errori: s.errori, bloccatoFino: s.bloccatoFino, inVolo: new Map(Object.entries(s.inVolo ?? {})) } : undefined;

/** Documenti e conti in Postgres, file in `spazio`. */
export function creaDepositoPostgres(p: Pool, spazio: SpazioFile): Deposito {
  return {
    async leggiDocumento<T>(aziendaId: string, tipo: TipoDocumento) {
      const r = await p.query<{ dati: T | null }>("select dati from documento where azienda_id = $1 and tipo = $2", documento(aziendaId, tipo));
      return r.rows[0]?.dati ?? null;
    },

    async aggiornaDocumento(aziendaId, tipo, fn) {
      const chiave = documento(aziendaId, tipo);
      return transazione(p, async (c) => {
        // La riga c'è sempre (vuota se il documento non c'era) così "for update" mette in fila anche il primo
        // salvataggio; se poi non si scrive, il rollback la toglie
        await c.query("insert into documento (azienda_id, tipo, dati) values ($1, $2, null) on conflict do nothing", chiave);
        const r = await c.query("select dati from documento where azienda_id = $1 and tipo = $2 for update", chiave);
        const m = await fn(r.rows[0]?.dati ?? null);
        if (m.nonScrivere) return { risultato: m.risultato, conferma: false };
        await c.query("update documento set dati = $3::jsonb, aggiornato = now() where azienda_id = $1 and tipo = $2", [
          ...chiave,
          json(m.dati),
        ]);
        return { risultato: m.risultato, conferma: true };
      });
    },

    async creaDocumento(aziendaId, tipo, dati) {
      const r = await p.query(
        "insert into documento (azienda_id, tipo, dati) values ($1, $2, $3::jsonb) on conflict do nothing returning 1",
        [...documento(aziendaId, tipo), json(dati)],
      );
      return r.rowCount === 1;
    },

    async salvaFile(aziendaId, cartella, nome, dati, opz) {
      return spazio.salva(percorsoFile(aziendaId, cartella, nome), dati, !!opz?.soloSeNuovo);
    },

    async leggiFile(aziendaId, cartella, nome) {
      return spazio.leggi(percorsoFile(aziendaId, cartella, nome));
    },

    async togliAzienda(aziendaId) {
      azienda(aziendaId);
      await p.query("delete from documento where azienda_id = $1", [aziendaId]);
      for (const cartella of CARTELLE) await spazio.togliSotto(`${aziendaId}/${cartella}`);
    },

    async aggiornaContoAccount(chiave, fn) {
      return transazione(p, async (c) => {
        await c.query("insert into conto_account (chiave, stato) values ($1, 'null'::jsonb) on conflict do nothing", [chiave]);
        const r = await c.query<{ stato: StatoSalvato | null }>("select stato from conto_account where chiave = $1 for update", [chiave]);
        const { stato, risultato } = fn(statoLetto(r.rows[0]?.stato ?? null));
        await c.query("update conto_account set stato = $2::jsonb, aggiornato = now() where chiave = $1", [chiave, json(statoDaSalvare(stato))]);
        return { risultato, conferma: true };
      });
    },
  };
}

export function tipoContenuto(nome: string): string {
  const est = nome.toLowerCase().split(".").pop();
  if (est === "jpg" || est === "jpeg") return "image/jpeg";
  if (est === "png") return "image/png";
  if (est === "pdf") return "application/pdf";
  return "application/octet-stream";
}

// Errori dello spazio: codice HTTP, codice nel corpo ("404", "409") o nome dell'errore (NoSuchKey…)
type ErroreSpazio = { status?: number; statusCode?: string; code?: string };
const haCodice = (e: unknown, http: number, nomi: string[]) => {
  const x = e as ErroreSpazio;
  return x.status === http || x.statusCode === String(http) || (!!x.code && nomi.includes(x.code));
};
const nonTrovato = (e: unknown) => haCodice(e, 404, ["NoSuchKey", "NoSuchBucket", "NotFound"]);
const giaEsiste = (e: unknown) => haCodice(e, 409, ["KeyAlreadyExists", "ResourceAlreadyExists", "BucketAlreadyExists", "Duplicate"]);
// Il messaggio resta generico; l'errore dello spazio va in `cause` (non contiene la chiave)
const errore = (cosa: string, causa: unknown) => new Error(`Spazio file: ${cosa} non riuscito`, { cause: causa });

const PAGINA = 1000;

/** Lo spazio di Supabase (Storage) con la chiave service_role, in un bucket privato creato se manca. */
function spazioSupabase(url: string, chiave: string, bucket: string): SpazioFile {
  const storage = createClient(url, chiave, {
    auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
  }).storage;
  const b = () => storage.from(bucket);

  // Alla prima scrittura: il bucket c'è ed è privato, oppure si crea privato. Se non riesce si riprova la volta dopo.
  let pronto: Promise<void> | null = null;
  const bucketPronto = () =>
    (pronto ??= (async () => {
      const { data, error } = await storage.getBucket(bucket);
      if (data) {
        if (data.public) throw new Error(`Spazio file: il bucket ${bucket} è pubblico, deve essere privato`);
        return;
      }
      if (!nonTrovato(error)) throw errore("controllo del bucket", error);
      const creato = await storage.createBucket(bucket, { public: false });
      if (creato.error && !giaEsiste(creato.error)) throw errore("creazione del bucket", creato.error);
    })().catch((e) => {
      pronto = null;
      throw e;
    }));

  return {
    async salva(percorso, dati, soloSeNuovo) {
      await bucketPronto();
      const { error } = await b().upload(percorso, dati, { upsert: !soloSeNuovo, contentType: tipoContenuto(percorso) });
      if (!error) return true;
      if (soloSeNuovo && giaEsiste(error)) return false;
      throw errore("salvataggio", error);
    },

    async leggi(percorso) {
      const { data, error } = await b().download(percorso);
      if (error) {
        if (nonTrovato(error)) return null;
        throw errore("lettura", error);
      }
      return Buffer.from(await data.arrayBuffer());
    },

    async togliSotto(prefisso) {
      // Prima l'elenco completo (a pagine), poi la rimozione: togliendo mentre si sfoglia le pagine scorrerebbero
      const percorsi: string[] = [];
      for (let offset = 0; ; offset += PAGINA) {
        const { data, error } = await b().list(prefisso, { limit: PAGINA, offset, sortBy: { column: "name", order: "asc" } });
        if (error) {
          if (nonTrovato(error)) return;
          throw errore("elenco", error);
        }
        // le voci senza id sono sottocartelle: nelle cartelle dell'azienda non ce ne sono
        for (const f of data) if (f.id) percorsi.push(`${prefisso}/${f.name}`);
        if (data.length < PAGINA) break;
      }
      for (let i = 0; i < percorsi.length; i += PAGINA) {
        const { error } = await b().remove(percorsi.slice(i, i + PAGINA));
        if (error && !nonTrovato(error)) throw errore("rimozione", error);
      }
    },
  };
}

export function creaDepositoSupabase(opz: { pool: Pool; url: string; chiave: string; bucket?: string }): Deposito {
  return creaDepositoPostgres(opz.pool, spazioSupabase(opz.url, opz.chiave, opz.bucket ?? "piazzale"));
}
