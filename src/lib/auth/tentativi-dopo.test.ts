// Dopo l'accesso con email (hook "after"): chiudere il gettone non deve mai lanciare, perché la sessione è già creata.
// Deposito finto. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import type { AuthContext } from "better-auth";
import type { StatoAccount } from "../accesso/tentativi-account.ts";
import type { Deposito } from "../deposito/tipi.ts";

let guasto: Error | null = null;
const conti = new Map<string, StatoAccount>();
const finto = {
  async aggiornaContoAccount<R>(k: string, fn: (p: StatoAccount | undefined) => { stato: StatoAccount; risultato: R }) {
    if (guasto) throw guasto;
    const { stato, risultato } = fn(conti.get(k));
    conti.set(k, stato);
    return risultato;
  },
} as unknown as Deposito;
(globalThis as typeof globalThis & { __deposito?: Deposito }).__deposito = finto;

const { chiudiTentativo } = await import("./tentativi-account.ts");

const conLog = async (fn: () => Promise<void>) => {
  const righe: unknown[][] = [];
  const prima = console.error;
  console.error = (...a: unknown[]) => void righe.push(a);
  try {
    await fn();
  } finally {
    console.error = prima;
  }
  return righe;
};
const nessunContesto = {} as AuthContext;

test("deposito che non risponde: nessun errore a Better Auth, solo una riga nel log", async () => {
  guasto = new Error("Connection terminated unexpectedly");
  try {
    const log = await conLog(() => chiudiTentativo(nessunContesto, { k: "u:1", gettone: "g", userId: "1" }, "giusta"));
    assert.equal(log.length, 1);
    assert.match(String(log[0][0]), /\[tentativi\]/);
    assert.equal(log[0][1], guasto);
  } finally {
    guasto = null;
  }
});

test("registro del blocco che fallisce: nessun errore, il blocco resta salvato", async () => {
  const ora = Date.now();
  conti.set("u:2", { errori: Array.from({ length: 9 }, (_, i) => ora - 1000 * (i + 1)), bloccatoFino: null, inVolo: new Map([["g2", ora]]) });
  const c = {
    internalAdapter: { findUserById: async () => ({ id: "2", name: "Mario" }) },
    adapter: {
      findMany: async () => {
        throw new Error("relation member does not exist");
      },
    },
  } as unknown as AuthContext;
  const log = await conLog(() => chiudiTentativo(c, { k: "u:2", gettone: "g2", userId: "2" }, "sbagliata"));
  assert.equal(log.length, 1);
  const s = conti.get("u:2")!;
  assert.ok(s.bloccatoFino && s.bloccatoFino > ora);
  assert.equal(s.inVolo.size, 0);
});

test("tutto a posto: gettone chiuso, niente nel log", async () => {
  conti.set("u:3", { errori: [], bloccatoFino: null, inVolo: new Map([["g3", Date.now()]]) });
  const log = await conLog(() => chiudiTentativo(nessunContesto, { k: "u:3", gettone: "g3", userId: "3" }, "giusta"));
  assert.equal(log.length, 0);
  assert.equal(conti.get("u:3")!.inVolo.size, 0);
});
