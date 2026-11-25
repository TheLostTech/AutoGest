// Prove del deposito su Supabase. Di serie girano solo quelle con un database finto (le transazioni, passo per passo).
// Il contratto completo gira solo sul progetto di prova (PROVA_DATABASE_URL, PROVA_SUPABASE_URL, PROVA_SUPABASE_KEY),
// mai sui dati veri; con PROVA_PG_LOCALE_URL (un Postgres locale usa e getta) gira sui documenti e sui conti,
// con i file in memoria. Ogni esecuzione usa id casuali e alla fine li toglie.
import { test } from "node:test";
import assert from "node:assert/strict";
import { randomBytes } from "node:crypto";
import { Pool, type PoolClient } from "pg";
import { opzioniPool } from "../db/pool.ts";
import { preparaSchema } from "../db/schema.ts";
import { provaContratto } from "./contratto.ts";
import { SQL_TEMPI, creaDepositoPostgres, creaDepositoSupabase, json, tipoContenuto, type SpazioFile } from "./supabase.ts";
import type { Deposito } from "./tipi.ts";

// Il deposito vero sotto id azienda e chiavi con un suffisso casuale: le prove non toccano mai dati già presenti
function conIdCasuali(d: Deposito, aziende: Set<string>, chiavi: Set<string>): Deposito {
  const s = randomBytes(4).toString("hex");
  const az = (id: string) => {
    const v = `${id}-${s}`;
    aziende.add(v);
    return v;
  };
  return {
    leggiDocumento: (id, tipo) => d.leggiDocumento(az(id), tipo),
    aggiornaDocumento: (id, tipo, fn) => d.aggiornaDocumento(az(id), tipo, fn),
    creaDocumento: (id, tipo, dati) => d.creaDocumento(az(id), tipo, dati),
    salvaFile: (id, cartella, nome, dati, opz) => d.salvaFile(az(id), cartella, nome, dati, opz),
    leggiFile: (id, cartella, nome) => d.leggiFile(az(id), cartella, nome),
    togliAzienda: (id) => d.togliAzienda(az(id)),
    aggiornaContoAccount: (chiave, fn) => {
      const v = `${chiave}:${s}`;
      chiavi.add(v);
      return d.aggiornaContoAccount(v, fn);
    },
  };
}

function contrattoSu(nome: string, urlDb: string, creaVero: (p: Pool) => Deposito) {
  const p = new Pool(opzioniPool(urlDb));
  const aziende = new Set<string>();
  const chiavi = new Set<string>();
  let pronto: Promise<Deposito> | undefined;
  provaContratto(
    nome,
    () =>
      (pronto ??= preparaSchema(p).then(() => conIdCasuali(creaVero(p), aziende, chiavi))),
    async () => {
      const vero = creaVero(p);
      // "../x-…" e simili non sono id validi: non c'è niente da togliere
      for (const id of aziende) await vero.togliAzienda(id).catch(() => undefined);
      if (chiavi.size) await p.query("delete from conto_account where chiave = any($1)", [[...chiavi]]);
      await p.end();
    },
  );
}

// File in memoria al posto dello spazio di Supabase, per provare la parte Postgres da sola
function spazioInMemoria(): SpazioFile {
  const m = new Map<string, Buffer>();
  return {
    async salva(percorso, dati, soloSeNuovo) {
      if (soloSeNuovo && m.has(percorso)) return false;
      m.set(percorso, Buffer.from(dati));
      return true;
    },
    leggi: async (percorso) => m.get(percorso) ?? null,
    async togliSotto(prefisso) {
      for (const k of [...m.keys()]) if (k.startsWith(`${prefisso}/`)) m.delete(k);
    },
  };
}

const { PROVA_DATABASE_URL, PROVA_SUPABASE_URL, PROVA_SUPABASE_KEY, PROVA_PG_LOCALE_URL } = process.env;

if (PROVA_DATABASE_URL && PROVA_SUPABASE_URL && PROVA_SUPABASE_KEY) {
  contrattoSu("supabase", PROVA_DATABASE_URL, (p) =>
    creaDepositoSupabase({ pool: p, url: PROVA_SUPABASE_URL, chiave: PROVA_SUPABASE_KEY }),
  );
} else {
  test("supabase: contratto", { skip: "servono PROVA_DATABASE_URL, PROVA_SUPABASE_URL e PROVA_SUPABASE_KEY (progetto di prova)" }, () => {});
}

if (PROVA_PG_LOCALE_URL) {
  const spazio = spazioInMemoria();
  contrattoSu("postgres locale, file in memoria", PROVA_PG_LOCALE_URL, (p) => creaDepositoPostgres(p, spazio));
}

// --- Database finto: si registrano le istruzioni e si risponde come Postgres ---

type Chiamata = { q: string; v?: unknown[] };
function finto(righe: (q: string) => unknown[] = () => []) {
  const chiamate: Chiamata[] = [];
  const rilasci: unknown[] = [];
  let connessioni = 0;
  const client = {
    query: async (q: string, v?: unknown[]) => {
      chiamate.push({ q, v });
      const rows = righe(q);
      return { rows, rowCount: rows.length };
    },
    release: (e?: unknown) => rilasci.push(e),
  } as unknown as PoolClient;
  const pool = {
    connect: async () => {
      connessioni++;
      return client;
    },
    query: client.query,
  } as unknown as Pool;
  return { pool, chiamate, rilasci, connessioni: () => connessioni };
}
const nessunFile: SpazioFile = {
  salva: async () => assert.fail("nessun file"),
  leggi: async () => assert.fail("nessun file"),
  togliSotto: async () => assert.fail("nessun file"),
};
// I limiti di tempo della transazione (SQL_TEMPI) compaiono come "tempi"
const passi = (c: Chiamata[]) => c.map((x) => (x.q === SQL_TEMPI ? "tempi" : x.q.split(" ").slice(0, 2).join(" ")));

test("aggiornaDocumento: begin, riga se manca, lettura bloccata, update, commit, connessione resa", async () => {
  const f = finto((q) => (q.startsWith("select") ? [{ dati: { n: 1 } }] : []));
  const d = creaDepositoPostgres(f.pool, nessunFile);
  const r = await d.aggiornaDocumento<{ n: number }, string>("az-1", "richieste", (p) => ({ dati: { n: p!.n + 1 }, risultato: "ok" }));
  assert.equal(r, "ok");
  assert.deepEqual(passi(f.chiamate), ["begin", "tempi", "insert into", "select dati", "update documento", "commit"]);
  assert.match(f.chiamate[2].q, /on conflict do nothing/);
  assert.match(f.chiamate[3].q, /for update$/);
  assert.deepEqual(f.chiamate[4].v, ["az-1", "richieste", '{"n":2}']);
  assert.deepEqual(f.rilasci, [undefined]);
});

test("aggiornaDocumento: un elenco si salva come JSON, non come array di Postgres", async () => {
  const f = finto();
  const d = creaDepositoPostgres(f.pool, nessunFile);
  await d.aggiornaDocumento("az-1", "richieste", () => ({ dati: [{ a: 1 }], risultato: 0 }));
  assert.equal(f.chiamate[4].v![2], '[{"a":1}]');
});

test("aggiornaDocumento: nonScrivere annulla la transazione (la riga vuota non resta)", async () => {
  const f = finto();
  const d = creaDepositoPostgres(f.pool, nessunFile);
  assert.equal(await d.aggiornaDocumento("az-1", "ebay", () => ({ dati: {}, risultato: 7, nonScrivere: true })), 7);
  assert.deepEqual(passi(f.chiamate), ["begin", "tempi", "insert into", "select dati", "rollback"]);
  assert.deepEqual(f.rilasci, [undefined]);
});

test("aggiornaDocumento: errore in fn → rollback, connessione resa, errore a chi chiama", async () => {
  const f = finto();
  const d = creaDepositoPostgres(f.pool, nessunFile);
  await assert.rejects(
    d.aggiornaDocumento("az-1", "archivio", async () => {
      throw new Error("rotto");
    }),
    /rotto/,
  );
  assert.deepEqual(passi(f.chiamate), ["begin", "tempi", "insert into", "select dati", "rollback"]);
  assert.deepEqual(f.rilasci, [undefined]);
});

test("aggiornaDocumento: se anche il rollback fallisce la connessione si butta", async () => {
  const f = finto((q) => {
    if (q === "commit" || q === "rollback") throw new Error(`${q} fallito`);
    return [];
  });
  const d = creaDepositoPostgres(f.pool, nessunFile);
  await assert.rejects(d.aggiornaDocumento("az-1", "archivio", () => ({ dati: {}, risultato: 0 })), /commit fallito/);
  assert.equal(f.rilasci.length, 1);
  assert.ok(f.rilasci[0] instanceof Error);
});

test("leggiDocumento: riga assente o dati vuoti danno null", async () => {
  let righe: unknown[] = [];
  const f = finto(() => righe);
  const d = creaDepositoPostgres(f.pool, nessunFile);
  assert.equal(await d.leggiDocumento("az-1", "archivio"), null);
  righe = [{ dati: null }];
  assert.equal(await d.leggiDocumento("az-1", "archivio"), null);
  righe = [{ dati: { a: 1 } }];
  assert.deepEqual(await d.leggiDocumento("az-1", "archivio"), { a: 1 });
});

test("creaDocumento: insert … on conflict do nothing returning 1", async () => {
  let righe: unknown[] = [{ "?column?": 1 }];
  const f = finto(() => righe);
  const d = creaDepositoPostgres(f.pool, nessunFile);
  assert.equal(await d.creaDocumento("az-1", "abbonamento", { v: 1 }), true);
  assert.match(f.chiamate[0].q, /^insert into documento .* on conflict do nothing returning 1$/);
  assert.deepEqual(f.chiamate[0].v, ["az-1", "abbonamento", '{"v":1}']);
  righe = [];
  assert.equal(await d.creaDocumento("az-1", "abbonamento", { v: 2 }), false);
});

test("creaDocumento: la scheda della registrazione è un tipo valido", async () => {
  const f = finto(() => [{ "?column?": 1 }]);
  const d = creaDepositoPostgres(f.pool, nessunFile);
  assert.equal(await d.creaDocumento("az-1", "registrazione", { titolare: "Mario" }), true);
  assert.deepEqual(f.chiamate[0].v, ["az-1", "registrazione", '{"titolare":"Mario"}']);
});

test("id, tipi e cartelle non validi: rifiutati prima di toccare il database o lo spazio", async () => {
  const f = finto();
  const d = creaDepositoPostgres(f.pool, nessunFile);
  await assert.rejects(d.leggiDocumento("a/b", "archivio"), /Id azienda non valido/);
  await assert.rejects(d.aggiornaDocumento("", "archivio", () => ({ dati: {}, risultato: 0 })), /Id azienda non valido/);
  await assert.rejects(d.leggiDocumento("az-1", "altro" as "archivio"), /Tipo di documento non valido/);
  await assert.rejects(d.salvaFile("az-1", "altro" as "foto", "a.jpg", new Uint8Array()), /Cartella non valida/);
  await assert.rejects(d.leggiFile("az-1", "foto", ".."), /Nome di file non valido/);
  await assert.rejects(d.leggiFile("az-1", "richieste", "registro.json"), /Nome di file non valido/);
  await assert.rejects(d.togliAzienda("../x"), /Id azienda non valido/);
  assert.equal(f.connessioni(), 0);
  assert.equal(f.chiamate.length, 0);
});

test("file: percorso <azienda>/<cartella>/<nome>; togliAzienda toglie righe e ogni cartella", async () => {
  const f = finto();
  const visti: string[] = [];
  const spazio: SpazioFile = {
    salva: async (p, _d, solo) => (visti.push(`salva ${p} ${solo}`), true),
    leggi: async (p) => (visti.push(`leggi ${p}`), null),
    togliSotto: async (p) => void visti.push(`togli ${p}`),
  };
  const d = creaDepositoPostgres(f.pool, spazio);
  await d.salvaFile("az-1", "visure", "v.pdf", new Uint8Array([1]), { soloSeNuovo: true });
  await d.salvaFile("az-1", "foto", "f.jpg", new Uint8Array([1]));
  await d.leggiFile("az-1", "allegati", "a.pdf");
  await d.togliAzienda("az-1");
  assert.deepEqual(visti, [
    "salva az-1/visure/v.pdf true",
    "salva az-1/foto/f.jpg false",
    "leggi az-1/allegati/a.pdf",
    "togli az-1/foto",
    "togli az-1/allegati",
    "togli az-1/visure",
    "togli az-1/richieste",
  ]);
  assert.deepEqual(f.chiamate, [{ q: "delete from documento where azienda_id = $1", v: ["az-1"] }]);
});

test("conto account: inVolo salvata come oggetto e riletta come Map", async () => {
  const f = finto((q) =>
    q.startsWith("select") ? [{ stato: { errori: [1], bloccatoFino: null, inVolo: { g: 5 } } }] : [],
  );
  const d = creaDepositoPostgres(f.pool, nessunFile);
  const r = await d.aggiornaContoAccount("u:x", (p) => {
    assert.ok(p!.inVolo instanceof Map);
    assert.equal(p!.inVolo.get("g"), 5);
    return { stato: { ...p!, inVolo: new Map([["h", 7]]) }, risultato: "fatto" };
  });
  assert.equal(r, "fatto");
  assert.deepEqual(passi(f.chiamate), ["begin", "tempi", "insert into", "select stato", "update conto_account", "commit"]);
  assert.deepEqual(JSON.parse(f.chiamate[4].v![1] as string), { errori: [1], bloccatoFino: null, inVolo: { h: 7 } });
  assert.deepEqual(f.rilasci, [undefined]);
});

test("conto account: la riga appena creata (stato null) arriva come undefined", async () => {
  const f = finto((q) => (q.startsWith("select") ? [{ stato: null }] : []));
  const d = creaDepositoPostgres(f.pool, nessunFile);
  const r = await d.aggiornaContoAccount("u:y", (p) => ({ stato: { errori: [], bloccatoFino: null, inVolo: new Map() }, risultato: p }));
  assert.equal(r, undefined);
});

test("transazioni: limiti di tempo solo per la transazione (SET LOCAL), subito dopo begin", () => {
  assert.match(SQL_TEMPI, /set_config\('statement_timeout', '15s', true\)/);
  assert.match(SQL_TEMPI, /set_config\('idle_in_transaction_session_timeout', '15s', true\)/);
});

test("JSON per jsonb: il carattere NUL si toglie da testi e nomi dei campi, il resto resta com'è", () => {
  const dati = { nome: "Ro\u0000ssi", note: ["a\u0000", "b"], annidato: { "chi\u0000ave": "v", n: 1, vero: true, nullo: null } };
  const testo = json(dati);
  assert.ok(!testo.includes("\\u0000"));
  assert.deepEqual(JSON.parse(testo), { nome: "Rossi", note: ["a", "b"], annidato: { chiave: "v", n: 1, vero: true, nullo: null } });
  // Un testo che contiene davvero la sequenza \u0000 scritta (barra e lettere) non si tocca
  assert.deepEqual(JSON.parse(json({ t: "\\u0000" })), { t: "\\u0000" });
  assert.equal(json([{ a: 1 }]), '[{"a":1}]');
});

test("aggiornaDocumento e creaDocumento mandano a Postgres il JSON senza NUL", async () => {
  const f = finto();
  const d = creaDepositoPostgres(f.pool, nessunFile);
  await d.aggiornaDocumento("az-1", "archivio", () => ({ dati: { x: "a\u0000b" }, risultato: 0 }));
  assert.equal(f.chiamate[4].v![2], '{"x":"ab"}');
  await d.creaDocumento("az-1", "abbonamento", { y: "\u0000" });
  assert.equal(f.chiamate.at(-1)!.v![2], '{"y":""}');
});

test("tipo del contenuto dal nome del file", () => {
  assert.equal(tipoContenuto("a.jpg"), "image/jpeg");
  assert.equal(tipoContenuto("A.JPEG"), "image/jpeg");
  assert.equal(tipoContenuto("b.png"), "image/png");
  assert.equal(tipoContenuto("c.pdf"), "application/pdf");
  assert.equal(tipoContenuto("d.bin"), "application/octet-stream");
  assert.equal(tipoContenuto("senza"), "application/octet-stream");
});
