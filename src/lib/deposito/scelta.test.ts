import { test } from "node:test";
import assert from "node:assert/strict";
import { sceltaDeposito } from "./index.ts";

const MSG = /Configurazione Supabase incompleta: servono SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY e DATABASE_URL/;

test("senza variabili si usa il disco", () => assert.equal(sceltaDeposito({}), "disco"));
test("con tutte e tre si usa Supabase", () =>
  assert.equal(sceltaDeposito({ SUPABASE_URL: "u", SUPABASE_SERVICE_ROLE_KEY: "k", DATABASE_URL: "d" }), "supabase"));
test("solo SUPABASE_URL è un errore", () => assert.throws(() => sceltaDeposito({ SUPABASE_URL: "u" }), MSG));
test("solo DATABASE_URL è un errore", () => assert.throws(() => sceltaDeposito({ DATABASE_URL: "d" }), MSG));
