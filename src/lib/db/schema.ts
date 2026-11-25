// Tabelle dei dati in Postgres quando il deposito è Supabase (le tabelle di Better Auth le crea getMigrations).
// Ogni istruzione si può ripetere: si eseguono a ogni avvio (avvio.ts). Solo server.
// RLS accesa e nessuna regola, su queste e su tutte le altre tabelle di public (proteggiTabelle): dalle chiavi pubbliche
// di Supabase (Data API) non si legge né si scrive nulla; il server entra con DATABASE_URL (proprietario delle
// tabelle), che la RLS non ferma.
import type { Pool, PoolClient } from "pg";

// All'avvio un'istruzione di schema non deve restare in attesa per sempre di un lock (5 secondi) né girare all'infinito
// (30 secondi). Con il pooler di Supabase in modalità transazione un SET di sessione non resta tra un'istruzione e
// l'altra (la connessione al server cambia): le istruzioni girano su una sola connessione presa dal pool, dentro una
// transazione, con SET LOCAL (vale fino al commit). Il DDL di Postgres è transazionale: se una istruzione fallisce
// non resta nulla a metà.
export const SQL_TEMPI_AVVIO = ["set local lock_timeout = '5s'", "set local statement_timeout = '30s'"];

async function conTempiMassimi(p: Pool, corpo: (c: PoolClient) => Promise<void>): Promise<void> {
  const c = await p.connect();
  let rotta: Error | undefined;
  try {
    await c.query("begin");
    for (const q of SQL_TEMPI_AVVIO) await c.query(q);
    await corpo(c);
    await c.query("commit");
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

export const SQL_SCHEMA: string[] = [
  "create table if not exists documento (azienda_id text not null, tipo text not null, dati jsonb, aggiornato timestamptz not null default now(), primary key (azienda_id, tipo));",
  "create table if not exists conto_account (chiave text primary key, stato jsonb not null, aggiornato timestamptz not null default now());",
  "alter table documento enable row level security;",
  "alter table conto_account enable row level security;",
];

export async function preparaSchema(p: Pool): Promise<void> {
  await conTempiMassimi(p, async (c) => {
    for (const q of SQL_SCHEMA) await c.query(q);
  });
}

// Ruoli delle chiavi pubbliche di Supabase: ci sono su Supabase, non su un Postgres qualsiasi
const RUOLI_PUBBLICI = ["anon", "authenticated"];
const nome = (s: string) => `"${s.replaceAll('"', '""')}"`;
const accendiRls = (t: string) => `alter table public.${nome(t)} enable row level security;`;
const togliPermessi = (t: string, ruoli: string[]) => `revoke all on table public.${nome(t)} from ${ruoli.map(nome).join(", ")};`;

/** RLS accesa su ogni tabella e, se ci sono i ruoli pubblici, nessun permesso per loro. Si può ripetere. */
export function sqlProtezione(tabelle: string[], ruoli: string[]): string[] {
  return tabelle.flatMap((t) => [accendiRls(t), ...(ruoli.length ? [togliPermessi(t, ruoli)] : [])]);
}

/** Com'è adesso una tabella di public: RLS accesa o no, e quali ruoli pubblici hanno ancora qualche permesso. */
export interface StatoTabella {
  tabella: string;
  rls: boolean;
  ruoli: string[];
}

/** Solo le istruzioni che servono: RLS dove è spenta, revoke dove un ruolo pubblico ha ancora permessi. */
export function sqlProtezioneMancante(stato: StatoTabella[]): string[] {
  return stato.flatMap((t) => [...(t.rls ? [] : [accendiRls(t.tabella)]), ...(t.ruoli.length ? [togliPermessi(t.tabella, t.ruoli)] : [])]);
}

// Una sola lettura del catalogo: per ogni tabella di public (comprese quelle di Better Auth) la RLS e i ruoli pubblici
// che compaiono tra i permessi della tabella o di una sua colonna (concessi direttamente: la revoke toglie quelli).
export const SQL_STATO_TABELLE = `select c.relname::text as tabella, c.relrowsecurity as rls,
  array(
    select r.rolname::text from pg_roles r
    where r.rolname in (${RUOLI_PUBBLICI.map((r) => `'${r}'`).join(", ")}) and (
      exists (select 1 from aclexplode(c.relacl) a where a.grantee = r.oid)
      or exists (select 1 from pg_attribute att, aclexplode(att.attacl) a where att.attrelid = c.oid and a.grantee = r.oid)
    )
    order by r.rolname
  ) as ruoli
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relkind in ('r', 'p')
order by c.relname`;

// Si esegue a ogni avvio dopo le migrazioni, così anche le tabelle nuove restano chiuse. Ma "enable row level security"
// prende un lock esclusivo sulla tabella: si esegue solo dove manca qualcosa, e a regime l'avvio fa una lettura e basta.
export async function proteggiTabelle(p: Pool): Promise<void> {
  await conTempiMassimi(p, async (c) => {
    const r = await c.query<StatoTabella>(SQL_STATO_TABELLE);
    for (const q of sqlProtezioneMancante(r.rows)) await c.query(q);
  });
}
