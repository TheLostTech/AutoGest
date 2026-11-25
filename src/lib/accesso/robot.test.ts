// Decisione sul controllo dei robot della registrazione. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { registrazioneDaRobot } from "./robot.ts";

const guasto = async (): Promise<{ isBot: boolean }> => {
  throw new Error("The 'x-vercel-oidc-token' header is missing from the request.");
};

test("registrazioneDaRobot: segue la risposta di BotID", async () => {
  assert.equal(await registrazioneDaRobot(async () => ({ isBot: true }), true), true);
  assert.equal(await registrazioneDaRobot(async () => ({ isBot: false }), true), false);
  assert.equal(await registrazioneDaRobot(async () => ({ isBot: true }), false), true);
});

test("registrazioneDaRobot: se BotID non risponde, in produzione si rifiuta, fuori si lascia passare", async () => {
  const errori = console.error;
  console.error = () => {};
  try {
    assert.equal(await registrazioneDaRobot(guasto, true), true);
    assert.equal(await registrazioneDaRobot(guasto, false), false);
  } finally {
    console.error = errori;
  }
});
