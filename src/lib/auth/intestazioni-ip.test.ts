// Da quale intestazione si prende l'indirizzo del cliente per i limiti: quella che il davanti riscrive sempre.
// Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { intestazioniIp, ipCliente } from "./intestazioni-ip.ts";

test("su Vercel x-real-ip, altrimenti cf-connecting-ip (Cloudflare Tunnel)", () => {
  assert.deepEqual(intestazioniIp({ VERCEL: "1" }), ["x-real-ip"]);
  assert.deepEqual(intestazioniIp({}), ["cf-connecting-ip"]);
  assert.deepEqual(intestazioniIp({ VERCEL: "0" }), ["cf-connecting-ip"]);
});

test("ipCliente legge solo l'intestazione scelta", () => {
  const h = new Headers({ "x-real-ip": "203.0.113.1", "cf-connecting-ip": "198.51.100.2", "x-forwarded-for": "192.0.2.3" });
  assert.equal(ipCliente(h, { VERCEL: "1" }), "203.0.113.1");
  assert.equal(ipCliente(h, {}), "198.51.100.2");
  assert.equal(ipCliente(new Headers({ "x-forwarded-for": "192.0.2.3" }), {}), null);
  assert.equal(ipCliente(new Headers({ "cf-connecting-ip": "198.51.100.2" }), { VERCEL: "1" }), null);
});
