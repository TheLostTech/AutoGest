// Tabelle dei dati in Postgres quando il deposito è Supabase (le tabelle di Better Auth le crea getMigrations).
// Ogni istruzione si può ripetere: si eseguono a ogni avvio (avvio.ts). Solo server.
// RLS accesa e nessuna regola: dalle chiavi pubbliche di Supabase non si legge né si scrive nulla;
// il server entra con DATABASE_URL (proprietario delle tabelle), che la RLS non ferma.
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
