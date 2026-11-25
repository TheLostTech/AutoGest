import { test } from "node:test";
import assert from "node:assert/strict";
import { percorsoAuthPermesso } from "./percorsi-auth.ts";

test("endpoint usati dall'app: permessi con il loro metodo", () => {
  assert.equal(percorsoAuthPermesso("POST", "/api/auth/sign-in/email"), true);
  assert.equal(percorsoAuthPermesso("POST", "/api/auth/sign-out"), true);
  assert.equal(percorsoAuthPermesso("GET", "/api/auth/get-session"), true);
  assert.equal(percorsoAuthPermesso("POST", "/api/auth/organization/set-active"), true);
  assert.equal(percorsoAuthPermesso("POST", "/api/auth/two-factor/verify-totp"), true);
  assert.equal(percorsoAuthPermesso("GET", "/api/auth/pin-dispositivo/nomi"), true);
  assert.equal(percorsoAuthPermesso("POST", "/api/auth/pin-dispositivo/entra/"), true);
  assert.equal(percorsoAuthPermesso("POST", "/api/auth/send-verification-email"), true);
  assert.equal(percorsoAuthPermesso("GET", "/api/auth/verify-email"), true);
});

test("tutto il resto: 404 (profilo, admin, lasciare l'azienda, metodo sbagliato, varianti)", () => {
  for (const [m, p] of [
    ["POST", "/api/auth/update-user"],
    ["POST", "/api/auth/change-email"],
    ["POST", "/api/auth/change-password"],
    ["POST", "/api/auth/organization/leave"],
    ["POST", "/api/auth/organization/update"],
    ["POST", "/api/auth/admin/set-user-password"],
    ["POST", "/api/auth/two-factor/disable"],
    ["POST", "/api/auth/sign-up/email"],
    ["GET", "/api/auth/sign-out"],
    ["GET", "/api/auth/send-verification-email"],
    ["POST", "/api/auth/verify-email"],
    ["POST", "/api/auth/request-password-reset"],
    ["POST", "/api/auth/get-session"],
    ["POST", "/api/auth/update%2Duser"],
    ["POST", "/api/auth//update-user"],
    ["POST", "/api/auth"],
    ["POST", "/altro/sign-in/email"],
  ]) {
    assert.equal(percorsoAuthPermesso(m, p), false, `${m} ${p}`);
  }
});
