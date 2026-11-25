// Chiave delle credenziali dei collegamenti in cloud: solo da CHIAVE_COLLEGAMENTI, mai da un file.
// Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { chiaveDalleVariabili } from "./cifratura.ts";

const SUPABASE = { SUPABASE_URL: "u", SUPABASE_SERVICE_ROLE_KEY: "k", DATABASE_URL: "d" };
const HEX = "0123456789abcdef".repeat(4);
const MSG = { message: "CHIAVE_COLLEGAMENTI mancante o non valida" };

test("con Supabase la chiave viene da CHIAVE_COLLEGAMENTI (64 caratteri esadecimali)", () => {
  assert.deepEqual(chiaveDalleVariabili({ ...SUPABASE, CHIAVE_COLLEGAMENTI: HEX }), Buffer.from(HEX, "hex"));
});

test("con Supabase, chiave mancante o non valida: errore", () => {
  assert.throws(() => chiaveDalleVariabili(SUPABASE), MSG);
  assert.throws(() => chiaveDalleVariabili({ ...SUPABASE, CHIAVE_COLLEGAMENTI: HEX.slice(1) }), MSG);
  assert.throws(() => chiaveDalleVariabili({ ...SUPABASE, CHIAVE_COLLEGAMENTI: "z".repeat(64) }), MSG);
});

test("su disco: la variabile se valida, altrimenti null (poi si usa il file nella cartella dati, come prima)", () => {
  assert.deepEqual(chiaveDalleVariabili({ CHIAVE_COLLEGAMENTI: HEX }), Buffer.from(HEX, "hex"));
  assert.equal(chiaveDalleVariabili({}), null);
  assert.equal(chiaveDalleVariabili({ CHIAVE_COLLEGAMENTI: "corta" }), null);
});
