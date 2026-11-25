// Decisione sul controllo dei robot della registrazione. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { registrazioneDaRobot } from "./robot.ts";

const guasto = async (): Promise<{ isBot: boolean }> => {
  throw new Error("The 'x-vercel-oidc-token' header is missing from the request.");
};

// Fa girare fn con le variabili date (undefined = tolta) e con i log raccolti, poi rimette tutto com'era
async function con<T>(env: Record<string, string | undefined>, fn: (log: string[]) => Promise<T>): Promise<T> {
  const prima = Object.fromEntries(Object.keys(env).map((k) => [k, process.env[k]]));
  const { info, error } = console;
  const log: string[] = [];
  console.info = (...a: unknown[]) => void log.push(a.map(String).join(" "));
  console.error = (...a: unknown[]) => void log.push(a.map(String).join(" "));
  const metti = (v: Record<string, string | undefined>) => {
    for (const [k, x] of Object.entries(v)) if (x === undefined) delete process.env[k];
    else process.env[k] = x;
  };
  metti(env);
  try {
    return await fn(log);
  } finally {
    metti(prima);
    console.info = info;
    console.error = error;
  }
}

test("registrazioneDaRobot su Vercel: segue la risposta di BotID", async () => {
  await con({ VERCEL: "1" }, async () => {
    assert.equal(await registrazioneDaRobot(async () => ({ isBot: true })), true);
    assert.equal(await registrazioneDaRobot(async () => ({ isBot: false })), false);
  });
});

test("registrazioneDaRobot su Vercel: se BotID non risponde si rifiuta, con l'errore nel log", async () => {
  await con({ VERCEL: "1", NODE_ENV: "production" }, async (log) => {
    assert.equal(await registrazioneDaRobot(guasto), true);
    assert.ok(log.some((r) => r.includes("Controllo dei robot non riuscito")));
  });
});

test("registrazioneDaRobot fuori da Vercel, anche in produzione: si salta BotID con una riga nel log", async () => {
  await con({ VERCEL: undefined, NODE_ENV: "production" }, async (log) => {
    let chiamato = false;
    const robot = async () => {
      chiamato = true;
      return { isBot: true };
    };
    assert.equal(await registrazioneDaRobot(robot), false);
    assert.equal(await registrazioneDaRobot(guasto), false);
    assert.equal(chiamato, false);
    assert.ok(log.some((r) => r.includes("saltato fuori da Vercel")));
  });
});
