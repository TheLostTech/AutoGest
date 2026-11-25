// Decisione sul controllo dei robot della registrazione. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { registrazioneDaRobot } from "./robot.ts";

const guasto = async (): Promise<{ isBot: boolean }> => {
  throw new Error("The 'x-vercel-oidc-token' header is missing from the request.");
};

// Fa girare fn con i log raccolti, poi rimette la console com'era
async function conLog<T>(fn: (log: string[]) => Promise<T>): Promise<T> {
  const { info, warn, error } = console;
  const log: string[] = [];
  const scrivi = (...a: unknown[]) => void log.push(a.map(String).join(" "));
  console.info = console.warn = console.error = scrivi;
  try {
    return await fn(log);
  } finally {
    Object.assign(console, { info, warn, error });
  }
}

// Un controllo che non va mai chiamato fuori da Vercel
function spia(isBot: boolean) {
  const s = { chiamate: 0, controlla: async () => (s.chiamate++, { isBot }) };
  return s;
}

test("su Vercel: segue la risposta di BotID; se non risponde si rifiuta, con l'errore nel log", async () => {
  await conLog(async (log) => {
    const env = { VERCEL: "1", NODE_ENV: "production" };
    assert.equal(await registrazioneDaRobot(async () => ({ isBot: true }), env), true);
    assert.equal(await registrazioneDaRobot(async () => ({ isBot: false }), env), false);
    assert.equal(await registrazioneDaRobot(guasto, env), true);
    assert.ok(log.some((r) => r.includes("Controllo dei robot non riuscito")));
  });
});

test("fuori da Vercel, in sviluppo e nelle prove: si salta BotID con una riga nel log", async () => {
  await conLog(async (log) => {
    for (const NODE_ENV of ["development", "test", undefined]) {
      const s = spia(true);
      assert.equal(await registrazioneDaRobot(s.controlla, { NODE_ENV }), false, String(NODE_ENV));
      assert.equal(s.chiamate, 0);
    }
    assert.ok(log.some((r) => r.includes("saltato fuori da Vercel")));
  });
});

test("fuori da Vercel, in produzione con PIAZZALE_SENZA_BOTID=1: si salta e il log dice che la rinuncia è attiva", async () => {
  await conLog(async (log) => {
    const s = spia(true);
    assert.equal(await registrazioneDaRobot(s.controlla, { NODE_ENV: "production", PIAZZALE_SENZA_BOTID: "1" }), false);
    assert.equal(s.chiamate, 0);
    assert.ok(log.some((r) => r.includes("PIAZZALE_SENZA_BOTID=1")));
  });
});

test("fuori da Vercel, in produzione senza rinuncia: si rifiuta e il log spiega perché", async () => {
  await conLog(async (log) => {
    for (const PIAZZALE_SENZA_BOTID of [undefined, "", "0", "true"]) {
      const s = spia(false);
      assert.equal(await registrazioneDaRobot(s.controlla, { NODE_ENV: "production", PIAZZALE_SENZA_BOTID }), true, String(PIAZZALE_SENZA_BOTID));
      assert.equal(s.chiamate, 0);
    }
    assert.ok(log.some((r) => r.includes("serve BotID oppure la rinuncia esplicita PIAZZALE_SENZA_BOTID=1")));
  });
});
