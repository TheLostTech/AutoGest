// Connessione a Postgres: TLS sempre verificato con il certificato di Supabase, mai spento; senza TLS solo in locale.
// Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { opzioniPool } from "./pool.ts";

const REMOTO = "postgresql://postgres.abc:segreta@aws-0-eu-central-1.pooler.supabase.com:6543/postgres";
const caFinto = () => {
  const f = path.join(mkdtempSync(path.join(tmpdir(), "ca-")), "supabase-ca.crt");
  writeFileSync(f, "-----BEGIN CERTIFICATE-----\nprova\n-----END CERTIFICATE-----\n");
  return f;
};

test("localhost e 127.0.0.1: niente TLS, al massimo 3 connessioni", () => {
  for (const url of ["postgresql://u:p@localhost:5432/piazzale", "postgres://u:p@127.0.0.1/piazzale"]) {
    const o = opzioniPool(url, "/non/esiste.crt");
    assert.equal(o.ssl, false);
    assert.equal(o.max, 3);
    assert.equal(o.connectionString, url);
  }
});

test("database remoto: TLS con il certificato di Supabase, verifica mai spenta", () => {
  const f = caFinto();
  const o = opzioniPool(REMOTO, f);
  assert.equal(o.max, 3);
  assert.ok(o.ssl && typeof o.ssl === "object");
  assert.match(String(o.ssl.ca), /BEGIN CERTIFICATE/);
  assert.notEqual(o.ssl.rejectUnauthorized, false);
});

test("database remoto senza il file del certificato: errore chiaro, nessuna connessione senza verifica", () => {
  assert.throws(() => opzioniPool(REMOTO, "/non/esiste/supabase-ca.crt"), {
    message: "Certificato CA di Supabase mancante: src/lib/db/supabase-ca.crt",
  });
});

test("sslmode e simili nell'indirizzo si tolgono: non possono sostituire il certificato o spegnere la verifica", () => {
  const o = opzioniPool(`${REMOTO}?sslmode=no-verify&uselibpqcompat=true&sslrootcert=/tmp/x&application_name=piazzale`, caFinto());
  const q = new URL(o.connectionString!).searchParams;
  assert.deepEqual([...q.keys()], ["application_name"]);
  assert.match(o.connectionString!, /^postgresql:\/\/postgres\.abc:segreta@aws-0-eu-central-1\.pooler\.supabase\.com:6543\/postgres\?/);
});

test("indirizzo illeggibile: errore senza l'indirizzo dentro (c'è la password)", () => {
  assert.throws(
    () => opzioniPool("postgresql://u:segreta@@:x/", "/non/esiste.crt"),
    (e: Error & { input?: unknown }) => e.message === "DATABASE_URL non valido" && !JSON.stringify({ ...e, m: e.message }).includes("segreta"),
  );
});
