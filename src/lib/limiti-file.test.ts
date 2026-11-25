import assert from "node:assert/strict";
import { test } from "node:test";
import { controllaDimensione, MAX_FILE_BYTES } from "./limiti-file";

test("file vuoto: rifiutato", () => {
  assert.deepEqual(controllaDimensione(0), { ok: false, messaggio: "File vuoto." });
});

test("fino a 3 MB: accettato", () => {
  assert.equal(MAX_FILE_BYTES, 3 * 1024 * 1024);
  assert.deepEqual(controllaDimensione(3 * 1024 * 1024), { ok: true });
});

test("oltre 3 MB: rifiutato con il messaggio", () => {
  assert.deepEqual(controllaDimensione(3 * 1024 * 1024 + 1), { ok: false, messaggio: "File più grande di 3 MB: riducilo e riprova." });
});
