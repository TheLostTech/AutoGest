// Prova lato server di accessoDaRichiesta con Better Auth vero, su un database SQLite temporaneo (DATI_DIR in /tmp).
// Il database si crea con le stesse migrazioni dell'avvio (avviaPiattaforma). Si lancia con npm test
// (node --import ./scripts/alias-ts.mjs: risolve "@/..." come Next). Mai sui dati veri: DATI_DIR è sempre nuova.
import { test, before } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { createHash, randomBytes } from "node:crypto";

process.env.DATI_DIR = mkdtempSync(path.join(tmpdir(), "prova-accesso-"));
delete process.env.BETTER_AUTH_SECRET;
delete process.env.SUPERADMIN_EMAIL;

type Mod = {
  accesso: typeof import("./server.ts");
  avvio: typeof import("./avvio.ts");
  auth: typeof import("../auth/server.ts");
  crypto: typeof import("better-auth/crypto");
  crea: typeof import("../piattaforma/crea.ts");
  regole: typeof import("./regole.ts");
};
let m: Mod;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let c: any;
let demoId = "";
let altraId = "";
let membroId = "";
let superId = "";

before(async () => {
  m = {
    accesso: await import("./server.ts"),
    avvio: await import("./avvio.ts"),
    auth: await import("../auth/server.ts"),
    crypto: await import("better-auth/crypto"),
    crea: await import("../piattaforma/crea.ts"),
    regole: await import("./regole.ts"),
  };
  await m.avvio.avviaPiattaforma();
  c = await m.auth.auth.$context;
  const orgs = await c.adapter.findMany({ model: "organization" });
  demoId = orgs[0].id;
  altraId = (await m.crea.creaAzienda(c, "Altra Demolizioni", "altra-prova", false)).id;
  const membri = await c.adapter.findMany({ model: "member", where: [{ field: "organizationId", value: demoId }] });
  const resp = membri.find((x: { role: string }) => x.role.includes("responsabile"));
  membroId = resp.userId;
  const sa = await c.internalAdapter.createUser({ name: "Super Prova", email: "super@prova.invalid", emailVerified: true, role: "superadmin", twoFactorEnabled: true }, { method: "admin" });
  superId = sa.id;
});

async function cookieDi(token: string): Promise<string> {
  const firma = await m.crypto.makeSignature(token, c.secret);
  return `${c.authCookies.sessionToken.name}=${encodeURIComponent(`${token}.${firma}`)}`;
}

async function sessione(userId: string, campi: Record<string, unknown>): Promise<string> {
  const s = await c.internalAdapter.createSession(userId, false, campi, true);
  return s.token;
}

async function richiesta(token: string, extra: Record<string, string> = {}, altriCookie = ""): Promise<Request> {
  const cookie = [await cookieDi(token), altriCookie].filter(Boolean).join("; ");
  return new Request("http://localhost/api/sessione", { headers: { cookie, ...extra } });
}

const esito = async (r: unknown) => (r instanceof Response ? { stato: r.status, corpo: (await r.json()) as { motivo?: string } } : { stato: 200, accesso: r as { azienda: { id: string }; ruoli: string[]; assistenza?: unknown; dispositivoCondiviso?: boolean } });

test("membro dell'azienda attiva: accesso con i suoi ruoli", async () => {
  const t = await sessione(membroId, { activeOrganizationId: demoId });
  const e = await esito(await m.accesso.accessoDaRichiesta(await richiesta(t)));
  assert.equal(e.stato, 200);
  assert.equal(e.accesso!.azienda.id, demoId);
  assert.ok(e.accesso!.ruoli.includes("responsabile"));
});

test("azienda attiva di cui non è membro: 403 non-membro", async () => {
  const t = await sessione(membroId, { activeOrganizationId: altraId });
  const e = await esito(await m.accesso.accessoDaRichiesta(await richiesta(t)));
  assert.equal(e.stato, 403);
  assert.equal(e.corpo!.motivo, "non-membro");
});

test("x-azienda diversa dall'azienda della sessione: 409 azienda-cambiata; uguale: accesso", async () => {
  const t = await sessione(membroId, { activeOrganizationId: demoId });
  const no = await esito(await m.accesso.accessoDaRichiesta(await richiesta(t, { "x-azienda": altraId })));
  assert.equal(no.stato, 409);
  assert.equal(no.corpo!.motivo, "azienda-cambiata");
  const si = await esito(await m.accesso.accessoDaRichiesta(await richiesta(t, { "x-azienda": demoId })));
  assert.equal(si.stato, 200);
});

test("PIN scaduto per inattività: 401 sessione-scaduta e sessione cancellata", async () => {
  const d = await c.adapter.create({ model: "dispositivo", data: { organizationId: demoId, nome: "Tablet prova", tokenHash: randomBytes(16).toString("hex"), creatoDa: membroId, creato: new Date(), bloccato: false, erroriPin: "[]" } });
  const t = await sessione(membroId, { activeOrganizationId: demoId, tipoAccesso: "pin", dispositivoId: d.id, expiresAt: new Date(Date.now() + m.regole.PIN_TURNO_MS) });
  const viva = await esito(await m.accesso.accessoDaRichiesta(await richiesta(t)));
  assert.equal(viva.stato, 200);
  await c.adapter.update({ model: "session", where: [{ field: "token", value: t }], update: { updatedAt: new Date(Date.now() - m.regole.PIN_INATTIVITA_MS - 10_000) } });
  const e = await esito(await m.accesso.accessoDaRichiesta(await richiesta(t)));
  assert.equal(e.stato, 401);
  assert.equal(e.corpo!.motivo, "sessione-scaduta");
  assert.equal(await c.adapter.findOne({ model: "session", where: [{ field: "token", value: t }] }), null);
});

test("password su un browser registrato come dispositivo: blocco dopo 5 minuti anche per il responsabile", async () => {
  const token = randomBytes(32).toString("base64url");
  await c.adapter.create({ model: "dispositivo", data: { organizationId: demoId, nome: "Tablet condiviso", tokenHash: createHash("sha256").update(token).digest("hex"), creatoDa: membroId, creato: new Date(), bloccato: false, erroriPin: "[]" } });
  const t = await sessione(membroId, { activeOrganizationId: demoId });
  const viva = await esito(await m.accesso.accessoDaRichiesta(await richiesta(t, {}, `dispositivo=${token}`)));
  assert.equal(viva.stato, 200);
  assert.equal(viva.accesso!.dispositivoCondiviso, true);
  await c.adapter.update({ model: "session", where: [{ field: "token", value: t }], update: { updatedAt: new Date(Date.now() - m.regole.PIN_INATTIVITA_MS - 10_000) } });
  const e = await esito(await m.accesso.accessoDaRichiesta(await richiesta(t, {}, `dispositivo=${token}`)));
  assert.equal(e.stato, 401);
  assert.equal(await c.adapter.findOne({ model: "session", where: [{ field: "token", value: t }] }), null);
});

test("super admin con secondo fattore: senza assistenza 403, con assistenza valida tutti i ruoli, scaduta 403", async () => {
  const t = await sessione(superId, { activeOrganizationId: demoId, dueFattoriVerificato: true });
  const senza = await esito(await m.accesso.accessoDaRichiesta(await richiesta(t)));
  assert.equal(senza.stato, 403);
  assert.equal(senza.corpo!.motivo, "assistenza-scaduta");
  const riga = await c.adapter.create({ model: "assistenza", data: { userId: superId, organizationId: demoId, motivo: "prova", inizio: new Date(), scade: new Date(Date.now() + 60_000) } });
  const con = await esito(await m.accesso.accessoDaRichiesta(await richiesta(t)));
  assert.equal(con.stato, 200);
  assert.ok(con.accesso!.assistenza);
  assert.equal(con.accesso!.ruoli.length, 6);
  await c.adapter.update({ model: "assistenza", where: [{ field: "id", value: riga.id }], update: { scade: new Date(Date.now() - 1000) } });
  const scaduta = await esito(await m.accesso.accessoDaRichiesta(await richiesta(t)));
  assert.equal(scaduta.stato, 403);
  await c.adapter.update({ model: "assistenza", where: [{ field: "id", value: riga.id }], update: { fine: new Date() } });
});

test("super admin senza il secondo fattore in questa sessione: 403 due-fattori", async () => {
  const t = await sessione(superId, { activeOrganizationId: demoId, dueFattoriVerificato: false });
  const e = await esito(await m.accesso.accessoDaRichiesta(await richiesta(t)));
  assert.equal(e.stato, 403);
  assert.equal(e.corpo!.motivo, "due-fattori");
});

test("uscita dall'account (/sign-out) durante l'assistenza: ingresso chiuso e 'Uscita assistenza' nel registro", async () => {
  const t = await sessione(superId, { activeOrganizationId: demoId, dueFattoriVerificato: true });
  const riga = await c.adapter.create({ model: "assistenza", data: { userId: superId, organizationId: demoId, motivo: "prova uscita", inizio: new Date(), scade: new Date(Date.now() + 60_000) } });
  const r = await m.auth.auth.handler(new Request("http://localhost:3000/api/auth/sign-out", { method: "POST", headers: { cookie: await cookieDi(t), origin: "http://localhost:3000", "content-type": "application/json" }, body: "{}" }));
  assert.equal(r.status, 200);
  const dopo = await c.adapter.findOne({ model: "assistenza", where: [{ field: "id", value: riga.id }] });
  assert.ok(dopo.fine, "l'ingresso di assistenza deve essere chiuso");
  const stato = JSON.parse(await readFile(path.join(process.env.DATI_DIR!, "aziende", demoId, "state.json"), "utf8"));
  const ultime = (stato.state.audit as { action: string; user: string }[]).slice(-3);
  assert.ok(ultime.some((x) => x.action === "Uscita assistenza" && x.user.includes("Super Prova")), JSON.stringify(ultime));
});

test("accesso con email: dal sesto tentativo sbagliato in un minuto 429", async () => {
  const stati: number[] = [];
  for (let i = 0; i < 6; i++) {
    const r = await m.auth.auth.handler(
      new Request("http://localhost:3000/api/auth/sign-in/email", {
        method: "POST",
        headers: { origin: "http://localhost:3000", "content-type": "application/json", "x-forwarded-for": "203.0.113.7" },
        body: JSON.stringify({ email: "nessuno@prova.invalid", password: "sbagliata-123" }),
      }),
    );
    stati.push(r.status);
  }
  assert.deepEqual(stati.slice(0, 5).every((s) => s === 401), true, stati.join());
  assert.equal(stati[5], 429, stati.join());
});

test("segreto: generato nella cartella dati (0600), mai il valore di prova di Better Auth", async () => {
  const { stat } = await import("node:fs/promises");
  const f = path.join(process.env.DATI_DIR!, ".segreto-accesso");
  assert.equal((await stat(f)).mode & 0o777, 0o600);
  assert.equal(c.secret, (await readFile(f, "utf8")).trim());
  assert.notEqual(c.secret, "better-auth-secret-12345678901234567890");
});
