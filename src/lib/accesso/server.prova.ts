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
// Email senza chiave: inviaEmail le scrive nel log (le prove le leggono da lì); link costruiti dalla richiesta
delete process.env.RESEND_API_KEY;
delete process.env.EMAIL_MITTENTE;
delete process.env.BETTER_AUTH_URL;

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
        headers: { origin: "http://localhost:3000", "content-type": "application/json", "cf-connecting-ip": "203.0.113.7" },
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

test("cambiare IP a ogni tentativo non serve: 10 password sbagliate per lo stesso account → bloccato anche con quella giusta", async () => {
  const cred = JSON.parse(await readFile(path.join(process.env.DATI_DIR!, "credenziali-demo.json"), "utf8")) as Record<string, { email?: string; password?: string }>;
  const valori = Object.values(cred).find((v) => !!v.password && !!v.email)!;
  const email = valori.email!;
  const prova = (password: string, ip: string) =>
    m.auth.auth.handler(
      new Request("http://localhost:3000/api/auth/sign-in/email", {
        method: "POST",
        headers: { origin: "http://localhost:3000", "content-type": "application/json", "cf-connecting-ip": ip },
        body: JSON.stringify({ email, password }),
      }),
    );
  const stati: number[] = [];
  for (let i = 0; i < 10; i++) stati.push((await prova("sbagliata-" + i, `198.51.100.${i + 1}`)).status);
  assert.ok(stati.every((s) => s === 401), stati.join());
  const giusta = await prova(valori.password!, "198.51.100.200");
  assert.equal(giusta.status, 429);
  // Nel registro dell'azienda dell'account
  const stato = JSON.parse(await readFile(path.join(process.env.DATI_DIR!, "aziende", demoId, "state.json"), "utf8"));
  assert.ok((stato.state.audit as { action: string }[]).some((x) => x.action === "Accesso bloccato per 15 minuti"));
});

test("20 accessi in parallelo sullo stesso account da 20 IP: al massimo 10 arrivano alla verifica della password", async () => {
  const email = "parallelo@prova.invalid";
  await c.internalAdapter.createUser({ name: "Parallelo", email, emailVerified: true }, { method: "admin" });
  const risposte = await Promise.all(
    Array.from({ length: 20 }, (_, i) =>
      m.auth.auth.handler(
        new Request("http://localhost:3000/api/auth/sign-in/email", {
          method: "POST",
          headers: { origin: "http://localhost:3000", "content-type": "application/json", "cf-connecting-ip": `192.0.2.${i + 1}` },
          body: JSON.stringify({ email, password: "sbagliata-123" }),
        }),
      ),
    ),
  );
  const stati = risposte.map((r) => r.status);
  assert.ok(stati.filter((s) => s === 401).length <= 10, stati.join());
  assert.ok(stati.filter((s) => s === 429).length >= 10, stati.join());
});

test("10 password sbagliate a gruppi di 5 in parallelo sullo stesso account: nessun tentativo perso, l'11° è 429 e il conto nel deposito è bloccato", async () => {
  const email = "gruppi@prova.invalid";
  const u = await c.internalAdapter.createUser({ name: "Gruppi", email, emailVerified: true }, { method: "admin" });
  const prova = (ip: string) =>
    m.auth.auth.handler(
      new Request("http://localhost:3000/api/auth/sign-in/email", {
        method: "POST",
        headers: { origin: "http://localhost:3000", "content-type": "application/json", "cf-connecting-ip": ip },
        body: JSON.stringify({ email, password: "sbagliata-123" }),
      }),
    );
  const stati: number[] = [];
  for (let gruppo = 0; gruppo < 2; gruppo++) {
    const r = await Promise.all(Array.from({ length: 5 }, (_, i) => prova(`192.0.2.${100 + gruppo * 5 + i}`)));
    stati.push(...r.map((x) => x.status));
  }
  assert.ok(stati.every((s) => s === 401), stati.join());
  const undicesimo = await prova("192.0.2.200");
  assert.equal(undicesimo.status, 429);
  const { deposito } = await import("../deposito/index.ts");
  const dopo = await deposito().aggiornaContoAccount(`u:${u.id}`, (p) => ({ stato: p ?? { errori: [], bloccatoFino: null, inVolo: new Map() }, risultato: p }));
  assert.ok(dopo && dopo.bloccatoFino !== null && dopo.bloccatoFino > Date.now(), "il conto nel deposito deve risultare bloccato");
});

test("email inesistenti: contatore comune da 30 al minuto, l'account vero intanto entra", async () => {
  const prova = (email: string, password: string, ip: string) =>
    m.auth.auth.handler(
      new Request("http://localhost:3000/api/auth/sign-in/email", {
        method: "POST",
        headers: { origin: "http://localhost:3000", "content-type": "application/json", "cf-connecting-ip": ip },
        body: JSON.stringify({ email, password }),
      }),
    );
  const stati: number[] = [];
  for (let i = 0; i < 35; i++) stati.push((await prova(`caso${i}@prova.invalid`, "x-12345678", `203.0.113.${i + 10}`)).status);
  assert.ok(stati.includes(429), stati.join());
  assert.ok(stati.filter((s) => s === 401).length <= 30, stati.join());
  const cred = JSON.parse(await readFile(path.join(process.env.DATI_DIR!, "credenziali-demo.json"), "utf8")) as Record<string, { email?: string; password?: string }>;
  // Il secondo account demo con email (il primo è stato bloccato dalla prova sopra)
  const vero = Object.values(cred).filter((v) => !!v.password && !!v.email)[1];
  if (!vero) return;
  const r = await prova(vero.email!, vero.password!, "203.0.113.200");
  assert.equal(r.status, 200);
});

// ——— Conferma dell'email del titolare registrato (spec prova-15-giorni, Task 5) ———

const SITO = "http://localhost:3000";
const RITORNO = "/accesso?confermata=1";
let ipN = 0;
const nuovoIp = () => `198.18.${Math.floor(++ipN / 250)}.${(ipN % 250) + 1}`;

/** Esegue fn catturando le email che inviaEmail scrive nel log (modalità senza chiave). */
async function conEmail<T>(fn: () => Promise<T>): Promise<{ r: T; email: string[] }> {
  const log = console.log;
  const email: string[] = [];
  console.log = (...a: unknown[]) => {
    const t = a.map(String).join(" ");
    if (t.startsWith("[email]")) email.push(t);
    else log(...a);
  };
  try {
    return { r: await fn(), email };
  } finally {
    console.log = log;
  }
}

const linkDa = (testo: string) => {
  const l = testo.match(/https?:\/\/\S*\/api\/auth\/verify-email\?\S+/)?.[0];
  assert.ok(l, `nessun link di conferma in: ${testo}`);
  return l!;
};

async function registra(email: string, azienda = "Ricambi Conferma", password = "password-lunga-1") {
  const { POST } = await import("../../app/api/registrazione/route.ts");
  return conEmail(async () => {
    const r = await POST(
      new Request(`${SITO}/api/registrazione`, {
        method: "POST",
        headers: { origin: SITO, host: "localhost:3000", "content-type": "application/json", "cf-connecting-ip": nuovoIp() },
        body: JSON.stringify({ azienda, nome: "Titolare Prova", email, password, condizioni: true }),
      }),
    );
    return { stato: r.status, corpo: (await r.json()) as Record<string, unknown> };
  });
}

const entra = (email: string, password: string) =>
  m.auth.auth.handler(
    new Request(`${SITO}/api/auth/sign-in/email`, {
      method: "POST",
      headers: { origin: SITO, "content-type": "application/json", "cf-connecting-ip": nuovoIp() },
      body: JSON.stringify({ email, password }),
    }),
  );

const apri = (link: string) => m.auth.auth.handler(new Request(link, { headers: { "cf-connecting-ip": nuovoIp() } }));

async function aziendaDi(userId: string): Promise<string> {
  const righe = await c.adapter.findMany({ model: "member", where: [{ field: "userId", value: userId }] });
  assert.equal(righe.length, 1);
  return righe[0].organizationId;
}

test("conferma: il titolare registrato non entra prima di confermare; il link fa partire i 15 giorni e chiude le altre sessioni", async () => {
  const email = "titolare-conferma@prova.invalid";
  const reg = await registra(email);
  assert.equal(reg.r.stato, 201, JSON.stringify(reg.r.corpo));
  assert.deepEqual(reg.r.corpo, { ok: true, conferma: true, inviata: true });
  assert.equal(reg.email.length, 1);
  assert.ok(reg.email[0].includes(`a ${email}`));
  const link = linkDa(reg.email[0]);
  assert.ok(link.startsWith(`${SITO}/api/auth/verify-email?`), link);

  // Password sbagliata: risponde come per tutti (401), senza dire che l'account aspetta la conferma
  const sbagliata = await entra(email, "non-questa-123");
  assert.equal(sbagliata.status, 401);
  const prima = await entra(email, "password-lunga-1");
  assert.equal(prima.status, 403);
  assert.equal(((await prima.json()) as { code?: string }).code, "EMAIL_DA_CONFERMARE");

  const u = (await c.internalAdapter.findUserByEmail(email)).user;
  const orgId = await aziendaDi(u.id);
  const { leggiAbbonamento } = await import("../abbonamento-server.ts");
  assert.equal((await leggiAbbonamento(orgId))?.fineProva, null);
  // Una sessione aperta prima della conferma (da chiunque): dopo il link non vale più
  const vecchia = await sessione(u.id, {});

  const ora = Date.now();
  const r = await apri(link);
  assert.equal(r.status, 302);
  assert.equal(r.headers.get("location"), RITORNO);
  assert.ok((r.headers.get("set-cookie") ?? "").includes(c.authCookies.sessionToken.name), "accesso automatico dopo la conferma");
  const a = await leggiAbbonamento(orgId);
  assert.ok(a?.fineProva !== null && Math.abs(a!.fineProva! - (ora + 15 * 86_400_000)) < 5000, String(a?.fineProva));
  assert.equal(await c.adapter.findOne({ model: "session", where: [{ field: "token", value: vecchia }] }), null);
  assert.equal((await c.adapter.findMany({ model: "session", where: [{ field: "userId", value: u.id }] })).length, 1);
  const { deposito } = await import("../deposito/index.ts");
  const scheda = await deposito().leggiDocumento<{ confermata: string | null }>(orgId, "registrazione");
  assert.ok(scheda?.confermata && Math.abs(Date.parse(scheda.confermata) - ora) < 5000);
  const stato = JSON.parse(await readFile(path.join(process.env.DATI_DIR!, "aziende", orgId, "state.json"), "utf8"));
  assert.ok((stato.state.audit as { action: string }[]).some((x) => x.action === "Email confermata: prova di 15 giorni iniziata"));

  const dopo = await entra(email, "password-lunga-1");
  assert.equal(dopo.status, 200);

  // Seconda apertura dello stesso link: si torna alla pagina, la fine della prova non si sposta
  const due = await apri(link);
  assert.equal(due.status, 302);
  assert.equal(due.headers.get("location"), RITORNO);
  assert.equal((await leggiAbbonamento(orgId))?.fineProva, a!.fineProva);

  // Titolare confermato: la stessa email non si registra di nuovo
  const ancora = await registra(email, "Altro Nome");
  assert.equal(ancora.r.stato, 409);
  assert.equal(ancora.email.length, 0);
});

test("conferma: link non valido torna alla pagina di accesso con l'errore", async () => {
  const r = await apri(`${SITO}/api/auth/verify-email?token=non-valido&callbackURL=${encodeURIComponent(RITORNO)}`);
  assert.equal(r.status, 302);
  assert.equal(r.headers.get("location"), `${RITORNO}&error=INVALID_TOKEN`);
});

test("conferma: rimandare l'email dalla pagina di accesso manda un nuovo link solo al titolare in attesa", async () => {
  const email = "rimanda@prova.invalid";
  assert.equal((await registra(email, "Rimanda Ricambi")).r.stato, 201);
  const rimanda = (a: string) =>
    conEmail(() =>
      m.auth.auth.handler(
        new Request(`${SITO}/api/auth/send-verification-email`, {
          method: "POST",
          headers: { origin: SITO, "content-type": "application/json", "cf-connecting-ip": nuovoIp() },
          body: JSON.stringify({ email: a, callbackURL: RITORNO }),
        }),
      ),
    );
  const si = await rimanda(email);
  assert.equal(si.r.status, 200);
  assert.equal(si.email.length, 1);
  linkDa(si.email[0]);
  // Un dipendente con l'email non verificata: nessuna email (e la stessa risposta)
  await m.crea.creaMembro(c, demoId, { nome: "Dipendente Rimanda", ruoli: ["magazziniere"], email: "dip-rimanda@prova.invalid", password: "password-lunga-2" });
  const no = await rimanda("dip-rimanda@prova.invalid");
  assert.equal(no.r.status, 200);
  assert.equal(no.email.length, 0);
});

test("conferma: un dipendente con email non verificata e il super admin entrano come oggi", async () => {
  await m.crea.creaMembro(c, demoId, { nome: "Dipendente Prova", ruoli: ["magazziniere"], email: "dipendente-conferma@prova.invalid", password: "password-lunga-3" });
  const u = (await c.internalAdapter.findUserByEmail("dipendente-conferma@prova.invalid")).user;
  assert.equal(u.emailVerified, false);
  assert.equal((await entra("dipendente-conferma@prova.invalid", "password-lunga-3")).status, 200);
  const sa = await c.internalAdapter.createUser({ name: "Super Conferma", email: "super-conferma@prova.invalid", emailVerified: false, role: "superadmin" }, { method: "admin" });
  await c.internalAdapter.linkAccount({ userId: sa.id, providerId: "credential", accountId: sa.id, password: await c.password.hash("password-lunga-4") });
  assert.equal((await entra("super-conferma@prova.invalid", "password-lunga-4")).status, 200);
});

test("registrazione con l'email di un titolare che non ha confermato: la vecchia registrazione si toglie, vale la nuova", async () => {
  const email = "ripresa@prova.invalid";
  const prima = await registra(email, "Prima Ricambi", "password-prima-1");
  assert.equal(prima.r.stato, 201);
  const vecchioUtente = (await c.internalAdapter.findUserByEmail(email)).user.id;
  const vecchiaAzienda = await aziendaDi(vecchioUtente);
  const seconda = await registra(email, "Seconda Ricambi", "password-seconda-1");
  assert.equal(seconda.r.stato, 201, JSON.stringify(seconda.r.corpo));
  const nuovo = (await c.internalAdapter.findUserByEmail(email)).user;
  assert.notEqual(nuovo.id, vecchioUtente);
  assert.equal(await c.adapter.findOne({ model: "organization", where: [{ field: "id", value: vecchiaAzienda }] }), null);
  assert.equal(await c.internalAdapter.findUserById(vecchioUtente), null);
  assert.equal((await c.adapter.findMany({ model: "member", where: [{ field: "organizationId", value: vecchiaAzienda }] })).length, 0);
  const { deposito } = await import("../deposito/index.ts");
  assert.equal(await deposito().leggiDocumento(vecchiaAzienda, "registrazione"), null);
  const nuovaAzienda = await aziendaDi(nuovo.id);
  const org = await c.adapter.findOne({ model: "organization", where: [{ field: "id", value: nuovaAzienda }] });
  assert.equal(org.name, "Seconda Ricambi");
  // Il link della prima email non vale più; quello della seconda sì
  const vecchioLink = await apri(linkDa(prima.email[0]));
  assert.equal(vecchioLink.headers.get("location"), `${RITORNO}&error=INVALID_TOKEN`);
  assert.equal((await entra(email, "password-prima-1")).status, 401);
  assert.equal((await apri(linkDa(seconda.email[0]))).headers.get("location"), RITORNO);
  assert.equal((await entra(email, "password-seconda-1")).status, 200);
});

test("registrazione con l'email di un dipendente o del super admin: 409 come oggi, niente si tocca", async () => {
  await m.crea.creaMembro(c, demoId, { nome: "Dipendente 409", ruoli: ["vendite"], email: "dip-409@prova.invalid", password: "password-lunga-5" });
  for (const email of ["dip-409@prova.invalid", "super@prova.invalid"]) {
    const prima = (await c.internalAdapter.findUserByEmail(email)).user.id;
    const r = await registra(email, "Tentativo Ricambi");
    assert.equal(r.r.stato, 409, email);
    assert.equal(r.r.corpo.error, "Non è stato possibile registrarti con questa email. Se hai già un account, accedi.");
    assert.equal((await c.internalAdapter.findUserByEmail(email)).user.id, prima);
  }
});

test("registrazione: se l'email di conferma non parte, la registrazione resta e la risposta lo dice", async () => {
  process.env.RESEND_API_KEY = "re_finta_per_la_prova";
  delete process.env.EMAIL_MITTENTE;
  try {
    const r = await registra("non-inviata@prova.invalid", "Senza Email Ricambi");
    assert.equal(r.r.stato, 201);
    assert.deepEqual(r.r.corpo, { ok: true, conferma: true, inviata: false });
    assert.ok(await c.internalAdapter.findUserByEmail("non-inviata@prova.invalid"));
  } finally {
    delete process.env.RESEND_API_KEY;
  }
});
