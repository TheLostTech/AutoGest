// Prove di contratto: valgono per ogni realizzazione di Deposito (disco, Supabase) e usano solo l'interfaccia.
import { test, after } from "node:test";
import assert from "node:assert/strict";
import type { Deposito } from "./tipi";

export function provaContratto(nome: string, crea: () => Promise<Deposito>, pulisci: () => Promise<void>): void {
  const A = "azienda-a1";
  const B = "azienda-b2";
  after(pulisci);
  const t = (cosa: string, fn: (d: Deposito) => Promise<void>) => test(`${nome}: ${cosa}`, async () => fn(await crea()));
  const inc = (p: { n: number } | null) => ({ dati: { n: (p?.n ?? 0) + 1 }, risultato: "ok" });

  t("documento assente dà null", async (d) => {
    assert.equal(await d.leggiDocumento("az-vuota", "abbonamento"), null);
  });

  t("aggiorna e rilegge", async (d) => {
    assert.equal(await d.aggiornaDocumento<{ n: number }, string>("az-agg", "abbonamento", inc), "ok");
    assert.deepEqual(await d.leggiDocumento("az-agg", "abbonamento"), { n: 1 });
  });

  t("nonScrivere non scrive", async (d) => {
    await d.aggiornaDocumento("az-nonscrivere", "ebay", () => ({ dati: { n: 1 }, risultato: 0, nonScrivere: true }));
    assert.equal(await d.leggiDocumento("az-nonscrivere", "ebay"), null);
  });

  t("venti aggiornamenti in parallelo", async (d) => {
    await Promise.all(Array.from({ length: 20 }, () => d.aggiornaDocumento<{ n: number }, string>("az-par", "archivio", inc)));
    assert.deepEqual(await d.leggiDocumento("az-par", "archivio"), { n: 20 });
  });

  t("fn asincrona", async (d) => {
    const r = await d.aggiornaDocumento<{ n: number }, string>("az-async", "collegamenti", async (p) => {
      await new Promise((ok) => setTimeout(ok, 5));
      return inc(p);
    });
    assert.equal(r, "ok");
    assert.deepEqual(await d.leggiDocumento("az-async", "collegamenti"), { n: 1 });
  });

  t("creaDocumento una volta sola", async (d) => {
    assert.equal(await d.creaDocumento("az-crea", "richieste", { v: 1 }), true);
    assert.equal(await d.creaDocumento("az-crea", "richieste", { v: 2 }), false);
    assert.deepEqual(await d.leggiDocumento("az-crea", "richieste"), { v: 1 });
  });

  t("file: salva e rilegge", async (d) => {
    const byte = Uint8Array.from([0, 1, 2, 255, 128, 7]);
    assert.equal(await d.salvaFile(A, "foto", "f1.jpg", byte), true);
    assert.deepEqual([...(await d.leggiFile(A, "foto", "f1.jpg"))!], [...byte]);
    assert.equal(await d.leggiFile(A, "foto", "assente.jpg"), null);
  });

  t("file: soloSeNuovo non sovrascrive", async (d) => {
    assert.equal(await d.salvaFile(A, "allegati", "x.pdf", Uint8Array.from([1, 2]), { soloSeNuovo: true }), true);
    assert.equal(await d.salvaFile(A, "allegati", "x.pdf", Uint8Array.from([9, 9]), { soloSeNuovo: true }), false);
    assert.deepEqual([...(await d.leggiFile(A, "allegati", "x.pdf"))!], [1, 2]);
  });

  t("file di un'altra azienda non si vede", async (d) => {
    await d.salvaFile(A, "visure", "v.pdf", Uint8Array.from([5]));
    assert.equal(await d.leggiFile(B, "visure", "v.pdf"), null);
  });

  t("nomi non validi rifiutati", async (d) => {
    const b = Uint8Array.from([1]);
    await assert.rejects(d.salvaFile(A, "foto", "../x.jpg", b));
    await assert.rejects(d.salvaFile(A, "foto", "a/b.jpg", b));
    await assert.rejects(d.salvaFile(A, "foto", "", b));
    await assert.rejects(d.leggiDocumento("../x", "archivio"));
    await assert.rejects(d.aggiornaDocumento("../x", "archivio", () => ({ dati: {}, risultato: 0 })));
    await assert.rejects(d.creaDocumento("../x", "archivio", {}));
    await assert.rejects(d.salvaFile(A, "richieste", "registro.json", b));
  });

  t("togliAzienda toglie solo quell'azienda", async (d) => {
    for (const az of ["az-togli-a", "az-togli-b"]) {
      await d.aggiornaDocumento<{ n: number }, string>(az, "archivio", inc);
      await d.salvaFile(az, "foto", "f.jpg", Uint8Array.from([3]));
      assert.equal(await d.creaDocumento(az, "registrazione", { titolare: az }), true);
    }
    await d.togliAzienda("az-togli-a");
    assert.equal(await d.leggiDocumento("az-togli-a", "archivio"), null);
    assert.equal(await d.leggiDocumento("az-togli-a", "registrazione"), null);
    assert.deepEqual(await d.leggiDocumento("az-togli-b", "registrazione"), { titolare: "az-togli-b" });
    assert.equal(await d.leggiFile("az-togli-a", "foto", "f.jpg"), null);
    assert.deepEqual(await d.leggiDocumento("az-togli-b", "archivio"), { n: 1 });
    assert.deepEqual([...(await d.leggiFile("az-togli-b", "foto", "f.jpg"))!], [3]);
  });

  t("conto account", async (d) => {
    const passo = () =>
      d.aggiornaContoAccount("u:contratto", (p) => ({
        stato: { errori: [...(p?.errori ?? []), 1], bloccatoFino: null, inVolo: new Map([["g", 5]]) },
        risultato: p === undefined,
      }));
    assert.equal(await passo(), true);
    assert.equal(await passo(), false);
    await d.aggiornaContoAccount("u:contratto", (p) => {
      assert.ok(p!.inVolo instanceof Map);
      assert.equal(p!.inVolo.get("g"), 5);
      assert.equal(p!.errori.length, 2);
      return { stato: p!, risultato: null };
    });
  });
}
