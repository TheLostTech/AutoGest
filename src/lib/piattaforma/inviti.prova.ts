// Prova dei codici invito su un database temporaneo (DATI_DIR sempre nuova, mai i dati veri).
import { test, before } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

process.env.DATI_DIR = mkdtempSync(path.join(tmpdir(), "prova-inviti-"));
delete process.env.BETTER_AUTH_SECRET;
delete process.env.SUPERADMIN_EMAIL;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let c: any;
let inviti: typeof import("./inviti.ts");
let utenteId = "";
let aziendaId = "";
let altraId = "";

before(async () => {
  const avvio = await import("../accesso/avvio.ts");
  const auth = await import("../auth/server.ts");
  inviti = await import("./inviti.ts");
  await avvio.avviaPiattaforma();
  c = await auth.auth.$context;
  utenteId = (await c.internalAdapter.createUser({ name: "Super Prova", email: "super@prova.invalid", emailVerified: true, role: "superadmin" }, { method: "admin" })).id;
  aziendaId = (await (await import("./crea.ts")).creaAzienda(c, "Azienda Prova", "azienda-prova", false)).id;
  altraId = (await (await import("./crea.ts")).creaAzienda(c, "Altra Prova", "altra-prova", false)).id;
});

test("creaInvito dà un codice a gruppi e verificaInvito lo accetta in qualunque forma", async () => {
  const { codice, scade } = await inviti.creaInvito(c, utenteId, "Prova");
  assert.match(codice, /^[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}$/);
  assert.ok(scade > Date.now());
  assert.equal(await inviti.verificaInvito(c, codice), true);
  assert.equal(await inviti.verificaInvito(c, codice.toLowerCase().replaceAll("-", " ")), true);
  assert.equal(await inviti.verificaInvito(c, "AAAA-AAAA-AAAA"), false);
  assert.equal(await inviti.verificaInvito(c, "zzz"), false);
  // il codice in chiaro non è nel database
  const righe = await c.adapter.findMany({ model: "invito" });
  assert.ok(righe.every((r: { codiceHash: string }) => r.codiceHash !== codice && /^[0-9a-f]{64}$/.test(r.codiceHash)));
});

test("usaInvito accetta lo stesso codice una volta sola anche in parallelo", async () => {
  const { codice } = await inviti.creaInvito(c, utenteId, "");
  const esiti = await Promise.all([inviti.usaInvito(c, codice, aziendaId), inviti.usaInvito(c, codice, altraId)]);
  assert.deepEqual(esiti.slice().sort(), [false, true]);
});

test("un codice usato non è più valido", async () => {
  const { codice } = await inviti.creaInvito(c, utenteId, "");
  assert.equal(await inviti.usaInvito(c, codice, aziendaId), true);
  assert.equal(await inviti.verificaInvito(c, codice), false);
  assert.equal(await inviti.usaInvito(c, codice, aziendaId), false);
});

test("un codice scaduto non vale", async () => {
  const { codice } = await inviti.creaInvito(c, utenteId, "");
  const hash = (await import("node:crypto")).createHash("sha256").update(codice.replaceAll("-", "")).digest("hex");
  await c.adapter.update({ model: "invito", where: [{ field: "codiceHash", value: hash }], update: { scade: new Date(Date.now() - 1000) } });
  assert.equal(await inviti.verificaInvito(c, codice), false);
  assert.equal(await inviti.usaInvito(c, codice, aziendaId), false);
});

test("elencoInviti: stati, azienda, più recenti prima e mai il codice", async () => {
  const el = await inviti.elencoInviti(c);
  assert.ok(el.length >= 4);
  assert.ok(el.some((i) => i.stato === "valido") && el.some((i) => i.stato === "usato" && i.azienda) && el.some((i) => i.stato === "scaduto"));
  for (let k = 1; k < el.length; k++) assert.ok(el[k - 1].creato >= el[k].creato);
  assert.ok(el.every((i) => !("codice" in i) && !("codiceHash" in i)));
});
