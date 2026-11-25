// Collegamenti sul server: lettura, modifica e scrittura dentro un solo aggiornamento del deposito, e messaggi
// d'errore per il browser filtrati. Deposito finto (in memoria, una modifica per volta come la riga bloccata di
// Postgres). Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import type { Deposito, Modifica, TipoDocumento } from "./deposito/tipi.ts";

process.env.CHIAVE_COLLEGAMENTI = "0123456789abcdef".repeat(4);

function depositoFinto() {
  const doc = new Map<string, unknown>();
  let fila: Promise<unknown> = Promise.resolve();
  const conti = { letture: 0, aggiornamenti: 0, scritture: 0 };
  let guasto: Error | null = null;
  const d = {
    async leggiDocumento<T>(az: string, tipo: TipoDocumento) {
      conti.letture++;
      return (doc.get(`${az}/${tipo}`) ?? null) as T | null;
    },
    aggiornaDocumento<T, R>(az: string, tipo: TipoDocumento, fn: (p: T | null) => Modifica<T, R> | Promise<Modifica<T, R>>) {
      conti.aggiornamenti++;
      const run = fila.then(async () => {
        if (guasto) throw guasto;
        const chiave = `${az}/${tipo}`;
        // Copia, come una lettura dal database: fn non tocca il documento salvato finché non si scrive
        const prima = doc.has(chiave) ? (structuredClone(doc.get(chiave)) as T) : null;
        // Un passo asincrono in mezzo: due modifiche senza fila si accavallerebbero qui
        await new Promise((r) => setTimeout(r, 2));
        const m = await fn(prima);
        if (!m.nonScrivere) {
          conti.scritture++;
          doc.set(chiave, structuredClone(m.dati));
        }
        return m.risultato;
      });
      fila = run.catch(() => undefined);
      return run;
    },
  } as unknown as Deposito;
  return { d, doc, conti, guasta: (e: Error | null) => void (guasto = e) };
}

const g = globalThis as typeof globalThis & { __deposito?: Deposito };
const f = depositoFinto();
g.__deposito = f.d;

const { erroreSalvataggio, modificaServizio, scollegaServizio, ErroreCollegamenti } = await import("./collegamenti-server.ts");
const { servizioById } = await import("./collegamenti.ts");
const { CollegamentiIlleggibili } = await import("./collegamenti-file.ts");

const rvfu = servizioById("rvfu")!;
const ia = servizioById("ia")!;

test("due servizi salvati insieme: restano tutti e due (lettura e scrittura nello stesso aggiornamento)", async () => {
  const prima = { ...f.conti };
  const [a, b] = await Promise.all([
    modificaServizio("az-1", rvfu, { id: "rvfu", valori: { utente: "mario" }, segreti: { password: "segreta" } }),
    modificaServizio("az-1", ia, { id: "ia", valori: { modello: "m1" }, segreti: { chiave: "sk-123" } }),
  ]);
  assert.deepEqual(a.valori, { utente: "mario" });
  assert.deepEqual(a.segreti, { password: true });
  assert.deepEqual(b.segreti, { chiave: true });
  const salvato = f.doc.get("az-1/collegamenti") as Record<string, { segreti: Record<string, string> }>;
  assert.deepEqual(Object.keys(salvato).sort(), ["ia", "rvfu"]);
  // Segreti cifrati, mai in chiaro
  assert.ok(!JSON.stringify(salvato).includes("segreta"));
  assert.ok(!JSON.stringify(salvato).includes("sk-123"));
  // Nessuna lettura fuori dall'aggiornamento
  assert.equal(f.conti.letture, prima.letture);
  assert.equal(f.conti.aggiornamenti - prima.aggiornamenti, 2);
});

test("indirizzo cambiato senza reinserire la password: errore noto, 400 con il suo messaggio, nulla scritto", async () => {
  const prima = f.conti.scritture;
  const e = await modificaServizio("az-1", rvfu, { id: "rvfu", valori: { endpoint: "https://altro.example" } }).catch((x) => x);
  assert.ok(e instanceof ErroreCollegamenti);
  assert.equal(f.conti.scritture, prima);
  assert.deepEqual(erroreSalvataggio(e), { status: 400, error: "Hai cambiato l'indirizzo del servizio: reinserisci la password per confermare." });
});

test("file troppo grande: errore noto con il suo messaggio", async () => {
  const servFile = servizioById("rentri")!;
  const dati = Buffer.alloc(64 * 1024 + 1).toString("base64");
  const e = await modificaServizio("az-1", servFile, { id: "rentri", file: { certificato: { nome: "c.p12", dati } } }).catch((x) => x);
  assert.deepEqual(erroreSalvataggio(e), { status: 400, error: "File vuoto o troppo grande (massimo 64 KB)" });
});

test("documento rovinato (non un oggetto): CollegamentiIlleggibili, non sovrascritto", async () => {
  f.doc.set("az-rotta/collegamenti", ["non", "un", "oggetto"]);
  const e = await modificaServizio("az-rotta", ia, { id: "ia", valori: { modello: "x" } }).catch((x) => x);
  assert.ok(e instanceof CollegamentiIlleggibili);
  assert.deepEqual(f.doc.get("az-rotta/collegamenti"), ["non", "un", "oggetto"]);
  assert.equal(erroreSalvataggio(e).status, 400);
});

test("errore del database o della chiave: messaggio generico al browser, quello vero solo nel log", async () => {
  const log: unknown[][] = [];
  const prima = console.error;
  console.error = (...a: unknown[]) => void log.push(a);
  try {
    for (const vero of ['duplicate key value violates unique constraint "documento_pkey"', "CHIAVE_COLLEGAMENTI mancante o non valida"]) {
      f.guasta(new Error(vero));
      const e = await modificaServizio("az-1", ia, { id: "ia", valori: { modello: "m2" } }).catch((x) => x);
      f.guasta(null);
      const r = erroreSalvataggio(e);
      assert.equal(r.status, 500);
      assert.ok(!r.error.includes(vero));
      assert.match(r.error, /Salvataggio non riuscito/);
      assert.ok(log.some((riga) => riga.some((x) => x instanceof Error && x.message === vero)));
    }
  } finally {
    console.error = prima;
    f.guasta(null);
  }
});

test("scollega toglie solo quel servizio, nello stesso aggiornamento", async () => {
  const prima = f.conti.letture;
  await scollegaServizio("az-1", "ia");
  assert.deepEqual(Object.keys(f.doc.get("az-1/collegamenti") as object), ["rvfu"]);
  assert.equal(f.conti.letture, prima);
});
