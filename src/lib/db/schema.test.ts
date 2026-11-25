// Tabelle dei dati in Postgres (deposito Supabase): si possono creare a ogni avvio senza errori né duplicati.
// Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import type { Pool } from "pg";
import { SQL_SCHEMA, SQL_STATO_TABELLE, SQL_TEMPI_AVVIO, preparaSchema, proteggiTabelle, sqlProtezione, sqlProtezioneMancante } from "./schema.ts";

// Un pool finto: connect() dà un client che registra tutto in `log`; `query` decide le risposte
const poolFinto = (query: (q: string) => Promise<{ rows: unknown[] }>, log: string[] = [], rilasci: unknown[] = []) =>
  ({
    connect: async () => ({
      query: async (q: string) => (log.push(q), query(q)),
      release: (e?: Error) => void rilasci.push(e),
    }),
  }) as unknown as Pool;

const RLS = /^alter table (\w+) enable row level security;?$/;

test("ogni istruzione si può ripetere: create … if not exists, oppure l'accensione della RLS", () => {
  assert.ok(SQL_SCHEMA.length > 0);
  for (const q of SQL_SCHEMA) assert.ok(/if not exists/i.test(q) || RLS.test(q.trim()), q);
});

test("documento e conto_account ci sono entrambe, con la RLS accesa", () => {
  for (const t of ["documento", "conto_account"]) {
    assert.ok(SQL_SCHEMA.some((q) => new RegExp(`^create table if not exists ${t} \\(`).test(q)), `manca la tabella ${t}`);
    assert.ok(SQL_SCHEMA.some((q) => RLS.exec(q.trim())?.[1] === t), `manca la RLS su ${t}`);
  }
});

test("preparaSchema: una connessione, transazione con i tempi massimi (5s lock, 30s istruzione), istruzioni in ordine", async () => {
  const log: string[] = [];
  const rilasci: unknown[] = [];
  let inCorso = 0;
  const finto = poolFinto(
    async () => {
      assert.equal(inCorso++, 0, "due istruzioni insieme");
      await new Promise((r) => setTimeout(r, 1));
      inCorso--;
      return { rows: [] };
    },
    log,
    rilasci,
  );
  await preparaSchema(finto);
  assert.deepEqual(SQL_TEMPI_AVVIO, ["set local lock_timeout = '5s'", "set local statement_timeout = '30s'"]);
  assert.deepEqual(log, ["begin", ...SQL_TEMPI_AVVIO, ...SQL_SCHEMA, "commit"]);
  assert.deepEqual(rilasci, [undefined]);
});

test("un errore del database arriva a chi chiama: rollback e connessione restituita", async () => {
  const log: string[] = [];
  const rilasci: unknown[] = [];
  const finto = poolFinto(async (q) => { if (q.startsWith("create")) throw new Error("permesso negato"); return { rows: [] }; }, log, rilasci);
  await assert.rejects(preparaSchema(finto), /permesso negato/);
  assert.equal(log.at(-1), "rollback");
  assert.ok(!log.includes("commit"));
  assert.deepEqual(rilasci, [undefined]);
});

test("rollback che non riesce: la connessione si butta", async () => {
  const rilasci: unknown[] = [];
  const finto = poolFinto(async (q) => { if (q !== "begin") throw new Error(q === "rollback" ? "rotta" : "permesso negato"); return { rows: [] }; }, [], rilasci);
  await assert.rejects(preparaSchema(finto), /permesso negato/);
  assert.equal((rilasci[0] as Error).message, "rotta");
});

test("sqlProtezione: RLS su ogni tabella, nomi tra virgolette (twoFactor resta twoFactor)", () => {
  assert.deepEqual(sqlProtezione(["user", "twoFactor", 'strano"nome'], []), [
    'alter table public."user" enable row level security;',
    'alter table public."twoFactor" enable row level security;',
    'alter table public."strano""nome" enable row level security;',
  ]);
});

test("sqlProtezione: con i ruoli di Supabase si tolgono anche tutti i permessi", () => {
  assert.deepEqual(sqlProtezione(["session"], ["anon", "authenticated"]), [
    'alter table public."session" enable row level security;',
    'revoke all on table public."session" from "anon", "authenticated";',
  ]);
  assert.deepEqual(sqlProtezione([], ["anon"]), []);
});

test("sqlProtezioneMancante: solo RLS spente e ruoli pubblici con permessi; tutto a posto = nessuna istruzione", () => {
  assert.deepEqual(
    sqlProtezioneMancante([
      { tabella: "user", rls: true, ruoli: [] },
      { tabella: "twoFactor", rls: false, ruoli: [] },
      { tabella: "session", rls: true, ruoli: ["anon"] },
      { tabella: 'strano"nome', rls: false, ruoli: ["anon", "authenticated"] },
    ]),
    [
      'alter table public."twoFactor" enable row level security;',
      'revoke all on table public."session" from "anon";',
      'alter table public."strano""nome" enable row level security;',
      'revoke all on table public."strano""nome" from "anon", "authenticated";',
    ],
  );
  assert.deepEqual(sqlProtezioneMancante([{ tabella: "user", rls: true, ruoli: [] }]), []);
  assert.deepEqual(sqlProtezioneMancante([]), []);
});

test("sqlProtezioneMancante dà le stesse istruzioni di sqlProtezione quando manca tutto", () => {
  assert.deepEqual(
    sqlProtezioneMancante([{ tabella: "session", rls: false, ruoli: ["anon", "authenticated"] }]),
    sqlProtezione(["session"], ["anon", "authenticated"]),
  );
});

test("lettura dello stato: tabelle di public, RLS, permessi di tabella e colonne dei soli ruoli pubblici", () => {
  assert.match(SQL_STATO_TABELLE, /n\.nspname = 'public'/);
  assert.match(SQL_STATO_TABELLE, /relkind in \('r', 'p'\)/);
  assert.match(SQL_STATO_TABELLE, /relrowsecurity as rls/);
  assert.match(SQL_STATO_TABELLE, /rolname in \('anon', 'authenticated'\)/);
  assert.match(SQL_STATO_TABELLE, /aclexplode\(c\.relacl\)/);
  assert.match(SQL_STATO_TABELLE, /aclexplode\(att\.attacl\)/);
});

test("proteggiTabelle: una lettura, poi solo le istruzioni che mancano (a regime nessuna), con i tempi massimi", async () => {
  let stato = [
    { tabella: "user", rls: false, ruoli: ["anon"] },
    { tabella: "rateLimit", rls: true, ruoli: [] },
  ];
  const log: string[] = [];
  const finto = poolFinto(async (q) => ({ rows: q === SQL_STATO_TABELLE ? stato : [] }), log);
  await proteggiTabelle(finto);
  assert.deepEqual(log, ["begin", ...SQL_TEMPI_AVVIO, SQL_STATO_TABELLE, ...sqlProtezione(["user"], ["anon"]), "commit"]);
  // Secondo avvio, tutto già protetto: nessun alter, nessun revoke
  log.length = 0;
  stato = stato.map((t) => ({ ...t, rls: true, ruoli: [] }));
  await proteggiTabelle(finto);
  assert.deepEqual(log, ["begin", ...SQL_TEMPI_AVVIO, SQL_STATO_TABELLE, "commit"]);
});

test("proteggiTabelle: un errore del database arriva a chi chiama", async () => {
  const finto = poolFinto(async (q) => { if (q === SQL_STATO_TABELLE) throw new Error("permesso negato"); return { rows: [] }; });
  await assert.rejects(proteggiTabelle(finto), /permesso negato/);
});
