import { test } from "node:test";
import assert from "node:assert/strict";
import { RICHIESTA_MAX_BYTE, richiestaObbligatoria, tipoRichiesta } from "./richieste.ts";

test("tipo dal contenuto, non dall'estensione", () => {
  assert.equal(tipoRichiesta(new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x2d])), "pdf");
  assert.equal(tipoRichiesta(new Uint8Array([0xff, 0xd8, 0xff, 0xe0])), "jpeg");
  assert.equal(tipoRichiesta(new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])), "png");
  assert.equal(tipoRichiesta(new TextEncoder().encode("ciao, sono un testo")), null);
  assert.equal(tipoRichiesta(new Uint8Array([])), null);
  assert.equal(tipoRichiesta(new Uint8Array([0x89, 0x50])), null);
});

test("limite e obbligo della richiesta scritta", () => {
  assert.equal(RICHIESTA_MAX_BYTE, 10_485_760);
  assert.equal(richiestaObbligatoria("crea"), true);
  assert.equal(richiestaObbligatoria("ruoli"), true);
  assert.equal(richiestaObbligatoria("pin"), false);
  assert.equal(richiestaObbligatoria("password"), false);
  assert.equal(richiestaObbligatoria("disattiva"), false);
});
