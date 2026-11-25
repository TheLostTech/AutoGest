// Tabelle dei dati in Postgres quando il deposito è Supabase (le tabelle di Better Auth le crea getMigrations).
// Ogni istruzione si può ripetere: si eseguono a ogni avvio (avvio.ts). Solo server.
// RLS accesa e nessuna regola, su queste e su tutte le altre tabelle di public (proteggiTabelle): dalle chiavi pubbliche
// di Supabase (Data API) non si legge né si scrive nulla; il server entra con DATABASE_URL (proprietario delle
// tabelle), che la RLS non ferma.
import type { Pool } from "pg";

export const SQL_SCHEMA: string[] = [
  "create table if not exists documento (azienda_id text not null, tipo text not null, dati jsonb, aggiornato timestamptz not null default now(), primary key (azienda_id, tipo));",
  "create table if not exists conto_account (chiave text primary key, stato jsonb not null, aggiornato timestamptz not null default now());",
  "alter table documento enable row level security;",
  "alter table conto_account enable row level security;",
];

export async function preparaSchema(p: Pool): Promise<void> {
  for (const q of SQL_SCHEMA) await p.query(q);
}

// Ruoli delle chiavi pubbliche di Supabase: ci sono su Supabase, non su un Postgres qualsiasi
const RUOLI_PUBBLICI = ["anon", "authenticated"];
const nome = (s: string) => `"${s.replaceAll('"', '""')}"`;

/** RLS accesa su ogni tabella e, se ci sono i ruoli pubblici, nessun permesso per loro. Si può ripetere. */
export function sqlProtezione(tabelle: string[], ruoli: string[]): string[] {
  return tabelle.flatMap((t) => [
    `alter table public.${nome(t)} enable row level security;`,
    ...(ruoli.length ? [`revoke all on table public.${nome(t)} from ${ruoli.map(nome).join(", ")};`] : []),
  ]);
}

// Tutte le tabelle di public, comprese quelle di Better Auth (utenti, sessioni, account, secondo fattore…):
// si esegue a ogni avvio dopo le migrazioni, così anche le tabelle nuove restano chiuse.
export async function proteggiTabelle(p: Pool): Promise<void> {
  const tabelle = await p.query<{ tablename: string }>("select tablename from pg_tables where schemaname = 'public' order by tablename");
  const ruoli = await p.query<{ rolname: string }>(
    `select rolname from pg_roles where rolname in (${RUOLI_PUBBLICI.map((r) => `'${r}'`).join(", ")}) order by rolname`,
  );
  const sql = sqlProtezione(tabelle.rows.map((r) => r.tablename), ruoli.rows.map((r) => r.rolname));
  for (const q of sql) await p.query(q);
}
