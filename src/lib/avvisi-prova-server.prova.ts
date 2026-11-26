// Prova del giro degli avvisi su una cartella dati temporanea (mai i dati veri) e un contesto Better Auth finto.
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

process.env.DATI_DIR = mkdtempSync(path.join(tmpdir(), "prova-avvisi-"));
delete process.env.RESEND_API_KEY;
process.env.BETTER_AUTH_URL = "https://piazzale.prova.test";

const GIORNO = 86_400_000;
const ORA = Date.UTC(2026, 10, 26, 8);

const contestoFinto = (aziende: { id: string; metadata: unknown }[]) => ({
  adapter: {
    findMany: async ({ model }: { model: string }) =>
      model === "organization" ? aziende : [{ userId: "u1", role: "responsabile" }],
  },
  internalAdapter: { findUserById: async () => ({ email: "titolare@prova.test", name: "Anna" }) },
}) as never;

async function azienda(id: string, o: Record<string, unknown>) {
  const { aggiornaAbbonamento } = await import("./abbonamento-server.ts");
  const { ABBONAMENTO_NUOVO } = await import("./abbonamento.ts");
  await aggiornaAbbonamento(id, () => ({ ...ABBONAMENTO_NUOVO(true, ORA), ...o }));
}

test("giro: avvisa una volta sola, due giri insieme non raddoppiano, le aziende non registrate restano fuori", async () => {
  const { mandaAvvisiProva } = await import("./avvisi-prova-server.ts");
  const { leggiAbbonamento } = await import("./abbonamento-server.ts");
  await azienda("a-scade", { fineProva: ORA + 2 * GIORNO });
  await azienda("a-lontana", { fineProva: ORA + 10 * GIORNO });
  await azienda("a-demo", { fineProva: ORA + 1 * GIORNO });
  const c = contestoFinto([
    { id: "a-scade", metadata: JSON.stringify({ registrata: true }) },
    { id: "a-lontana", metadata: JSON.stringify({ registrata: true }) },
    { id: "a-demo", metadata: JSON.stringify({ demo: true }) },
  ]);
  const righe: string[] = [];
  const log = console.log;
  console.log = (...a: unknown[]) => { righe.push(String(a[0])); };
  try {
    const [x, y] = await Promise.all([mandaAvvisiProva(c, ORA), mandaAvvisiProva(c, ORA)]);
    assert.equal(x.mandati + y.mandati, 1);
    assert.equal(x.aziende, 2);
    const z = await mandaAvvisiProva(c, ORA);
    assert.equal(z.mandati, 0);
  } finally {
    console.log = log;
  }
  assert.equal(righe.filter((r) => r.startsWith("[email]")).length, 1);
  assert.ok((await leggiAbbonamento("a-scade"))?.avvisi.scadenza);
  assert.deepEqual((await leggiAbbonamento("a-lontana"))?.avvisi, {});
  assert.deepEqual((await leggiAbbonamento("a-demo"))?.avvisi, {});
});

test("giro: prova finita manda 'finita'; un invio fallito lascia il segno e non si ripete", async () => {
  const { mandaAvvisiProva } = await import("./avvisi-prova-server.ts");
  const { leggiAbbonamento } = await import("./abbonamento-server.ts");
  await azienda("a-finita", { fineProva: ORA - GIORNO });
  const c = contestoFinto([{ id: "a-finita", metadata: JSON.stringify({ registrata: true }) }]);
  const prima = process.env.NODE_ENV;
  (process.env as Record<string, string>).NODE_ENV = "production"; // senza chiave Resend l'invio fallisce
  const err = console.error;
  console.error = () => {};
  try {
    const e1 = await mandaAvvisiProva(c, ORA);
    assert.equal(e1.errori, 1);
    assert.equal(e1.mandati, 0);
    const e2 = await mandaAvvisiProva(c, ORA);
    assert.equal(e2.errori + e2.mandati, 0);
  } finally {
    console.error = err;
    (process.env as Record<string, string | undefined>).NODE_ENV = prima;
  }
  assert.ok((await leggiAbbonamento("a-finita"))?.avvisi.finita);
});

test("giro: senza indirizzo pubblico si ferma prima di segnare qualunque avviso", async () => {
  const { mandaAvvisiProva } = await import("./avvisi-prova-server.ts");
  const { leggiAbbonamento } = await import("./abbonamento-server.ts");
  await azienda("a-senza-indirizzo", { fineProva: ORA + GIORNO });
  const c = contestoFinto([{ id: "a-senza-indirizzo", metadata: JSON.stringify({ registrata: true }) }]);
  const url = process.env.BETTER_AUTH_URL;
  delete process.env.BETTER_AUTH_URL;
  try {
    await assert.rejects(mandaAvvisiProva(c, ORA), /Indirizzo pubblico/);
  } finally {
    process.env.BETTER_AUTH_URL = url;
  }
  assert.deepEqual((await leggiAbbonamento("a-senza-indirizzo"))?.avvisi, {});
});
