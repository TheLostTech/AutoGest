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

// Vista per guardare le registrazioni dal pannello di Supabase (Table Editor, tra le viste). Una riga per azienda con la
// scheda `registrazione` (la fonte dei contatti); l'abbonamento è facoltativo. Si crea dopo le migrazioni di Better Auth
// (usa organization). security_invoker: i permessi sono quelli di chi interroga, non del proprietario; in più
// proteggiTabelle toglie ogni permesso ad anon e authenticated.
// giorni_rimasti: solo in prova (stato nuovo con una fine), giorni interi arrotondati per eccesso, mai sotto 0; conta
// lo spostamento degli strumenti di prova solo con le chiavi di prova (come oraProva). moduli_pagati: solo con un
// abbonamento in corso (attivo, in ritardo, disdetto), separati da virgola.
export const SQL_VISTA_REGISTRAZIONI = `create or replace view registrazioni with (security_invoker = true) as
select
  coalesce(r.dati->>'azienda', o.name) as azienda,
  r.dati->>'titolare' as titolare,
  r.dati->>'email' as email,
  r.dati->>'telefono' as telefono,
  (r.dati->>'registrata')::timestamptz as registrata,
  (r.dati->>'confermata')::timestamptz as confermata,
  case when f.ms is not null then to_timestamp(f.ms / 1000.0) end as fine_prova,
  case when a.dati->>'stato' = 'nuovo' and f.ms is not null
    then greatest(0, ceil((f.ms - (extract(epoch from now()) * 1000 + case when a.dati->>'prova' = 'true' then coalesce((a.dati->>'spostamentoProva')::numeric, 0) else 0 end)) / 86400000.0))::integer
  end as giorni_rimasti,
  coalesce(a.dati->>'stato', 'nuovo') as stato,
  case when a.dati->>'stato' in ('attivo', 'in-ritardo', 'disdetto')
    then (select string_agg(m, ',' order by ord) from jsonb_array_elements_text(coalesce(a.dati->'moduli', '[]'::jsonb)) with ordinality as t(m, ord))
  end as moduli_pagati,
  jsonb_typeof(r.dati->'commerciale') = 'object' as consenso_commerciale
from documento r
left join organization o on o.id = r.azienda_id
left join documento a on a.azienda_id = r.azienda_id and a.tipo = 'abbonamento'
left join lateral (select (a.dati->>'fineProva')::numeric as ms where jsonb_typeof(a.dati->'fineProva') = 'number') f on true
where r.tipo = 'registrazione'
order by registrata desc nulls last`;

export async function preparaSchema(p: Pool): Promise<void> {
  await conTempiMassimi(p, async (c) => {
    for (const q of SQL_SCHEMA) await c.query(q);
    await c.query(SQL_VISTA_REGISTRAZIONI);
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
  /** Una vista: la RLS non esiste (si toglie solo il permesso). */
  vista?: boolean;
  ruoli: string[];
}

/** Solo le istruzioni che servono: RLS dove è spenta, revoke dove un ruolo pubblico ha ancora permessi. */
export function sqlProtezioneMancante(stato: StatoTabella[]): string[] {
  return stato.flatMap((t) => [...(t.rls || t.vista ? [] : [accendiRls(t.tabella)]), ...(t.ruoli.length ? [togliPermessi(t.tabella, t.ruoli)] : [])]);
}

// Una sola lettura del catalogo: per ogni tabella di public (comprese quelle di Better Auth) la RLS e i ruoli pubblici
// che compaiono tra i permessi della tabella o di una sua colonna (concessi direttamente: la revoke toglie quelli).
export const SQL_STATO_TABELLE = `select c.relname::text as tabella, c.relrowsecurity as rls, (c.relkind = 'v') as vista,
  array(
    select r.rolname::text from pg_roles r
    where r.rolname in (${RUOLI_PUBBLICI.map((r) => `'${r}'`).join(", ")}) and (
      exists (select 1 from aclexplode(c.relacl) a where a.grantee = r.oid)
      or exists (select 1 from pg_attribute att, aclexplode(att.attacl) a where att.attrelid = c.oid and a.grantee = r.oid)
    )
    order by r.rolname
  ) as ruoli
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relkind in ('r', 'p', 'v')
order by c.relname`;

// Si esegue a ogni avvio dopo le migrazioni, così anche le tabelle nuove restano chiuse. Ma "enable row level security"
// prende un lock esclusivo sulla tabella: si esegue solo dove manca qualcosa, e a regime l'avvio fa una lettura e basta.
export async function proteggiTabelle(p: Pool): Promise<void> {
  await conTempiMassimi(p, async (c) => {
    const r = await c.query<StatoTabella>(SQL_STATO_TABELLE);
    for (const q of sqlProtezioneMancante(r.rows)) await c.query(q);
  });
}
