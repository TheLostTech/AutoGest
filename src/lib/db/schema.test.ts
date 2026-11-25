// Tabelle dei dati in Postgres (deposito Supabase): si possono creare a ogni avvio senza errori né duplicati.
// Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import type { Pool } from "pg";
import { SQL_SCHEMA, preparaSchema, proteggiTabelle, sqlProtezione } from "./schema.ts";

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

test("preparaSchema esegue le istruzioni una dopo l'altra, nell'ordine", async () => {
  const eseguite: string[] = [];
  let inCorso = 0;
  const finto = {
    query: async (q: string) => {
      assert.equal(inCorso++, 0, "due istruzioni insieme");
      await new Promise((r) => setTimeout(r, 1));
      eseguite.push(q);
      inCorso--;
      return { rows: [] };
    },
  } as unknown as Pool;
  await preparaSchema(finto);
  assert.deepEqual(eseguite, SQL_SCHEMA);
});

test("un errore del database arriva a chi chiama", async () => {
  const finto = { query: async () => { throw new Error("permesso negato"); } } as unknown as Pool;
  await assert.rejects(preparaSchema(finto), /permesso negato/);
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

test("proteggiTabelle legge tabelle di public e ruoli esistenti, poi esegue le istruzioni", async () => {
  const eseguite: string[] = [];
  const finto = {
    query: async (q: string) => {
      if (/from pg_tables/.test(q)) {
        assert.match(q, /schemaname = 'public'/);
        return { rows: [{ tablename: "user" }, { tablename: "rateLimit" }] };
      }
      if (/from pg_roles/.test(q)) {
        assert.match(q, /'anon'/);
        assert.match(q, /'authenticated'/);
        return { rows: [{ rolname: "anon" }] };
      }
      eseguite.push(q);
      return { rows: [] };
    },
  } as unknown as Pool;
  await proteggiTabelle(finto);
  assert.deepEqual(eseguite, sqlProtezione(["user", "rateLimit"], ["anon"]));
});
