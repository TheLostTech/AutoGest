// Segreto di Better Auth in cloud: solo dalla variabile, mai da un file.
// Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { segretoAccesso } from "./segreto.ts";

const SUPABASE = { SUPABASE_URL: "u", SUPABASE_SERVICE_ROLE_KEY: "k", DATABASE_URL: "d" };

test("con Supabase e senza BETTER_AUTH_SECRET: errore, nessun file generato", () => {
  assert.throws(() => segretoAccesso(SUPABASE), { message: "BETTER_AUTH_SECRET mancante" });
  assert.throws(() => segretoAccesso({ ...SUPABASE, BETTER_AUTH_SECRET: "   " }), { message: "BETTER_AUTH_SECRET mancante" });
});

test("con Supabase e BETTER_AUTH_SECRET: si usa la variabile", () => {
  const s = "x".repeat(40);
  assert.equal(segretoAccesso({ ...SUPABASE, BETTER_AUTH_SECRET: ` ${s} ` }), s);
});

test("su disco la variabile, se c'è, vale come prima", () => {
  assert.equal(segretoAccesso({ BETTER_AUTH_SECRET: "y".repeat(40) }), "y".repeat(40));
});
