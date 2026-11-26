// Documenti legali pubblici (/privacy): versione uguale a quella salvata con il consenso, sezioni, dati di Lostar. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { PRODUTTORE } from "../config.ts";
import { VERSIONE_CONDIZIONI, VERSIONE_PRIVACY } from "../consensi.ts";
import { dataVersione, FORNITORI, pezziTesto, type Documento, type Sezione } from "./comune.ts";
import { INFORMATIVA_PRIVACY } from "./privacy.ts";

const testoSezione = (s: Sezione) => [s.titolo, ...s.paragrafi, ...(s.elenco ?? [])].join("\n");
const testoDocumento = (d: Documento) => [d.titolo, ...d.sezioni.map(testoSezione)].join("\n");

test("la versione mostrata è quella salvata con il consenso", () => {
  assert.equal(INFORMATIVA_PRIVACY.versione, VERSIONE_PRIVACY);
  assert.match(VERSIONE_PRIVACY, /^\d{4}-\d{2}-\d{2}$/);
  assert.match(VERSIONE_CONDIZIONI, /^\d{4}-\d{2}-\d{2}$/);
});

test("data della versione scritta per esteso", () => {
  assert.equal(dataVersione("2026-11-27"), "27 novembre 2026");
  assert.equal(dataVersione("2027-01-05"), "5 gennaio 2027");
});

test("sezioni dell'informativa, in ordine", () => {
  assert.deepEqual(
    INFORMATIVA_PRIVACY.sezioni.map((s) => s.id),
    ["titolare", "dati", "finalita", "conservazione", "fornitori", "trasferimenti", "diritti", "cookie", "modifiche"],
  );
});

test("l'informativa nomina Lostar, la PEC, il Garante, i tempi e ogni fornitore", () => {
  const testo = testoDocumento(INFORMATIVA_PRIVACY);
  for (const atteso of [PRODUTTORE.ragioneSociale, PRODUTTORE.piva, PRODUTTORE.pec, "Garante", "consenso", "12 mesi", "10 anni", "BotID"]) {
    assert.ok(testo.includes(atteso), `manca «${atteso}»`);
  }
  for (const f of FORNITORI) assert.ok(testo.includes(f.nome), `manca il fornitore «${f.nome}»`);
});

test("Supabase compare solo nella sezione dei fornitori, mai il suo indirizzo", () => {
  for (const s of INFORMATIVA_PRIVACY.sezioni) {
    const testo = testoSezione(s);
    if (s.id !== "fornitori") assert.doesNotMatch(testo, /supabase/i, `Supabase nella sezione «${s.id}»`);
    assert.ok(!testo.toLowerCase().includes("supabase.co"), `indirizzo di Supabase nella sezione «${s.id}»`);
  }
  assert.doesNotMatch(INFORMATIVA_PRIVACY.titolo, /supabase/i);
  assert.match(testoSezione(INFORMATIVA_PRIVACY.sezioni.find((s) => s.id === "fornitori")!), /Supabase/);
});

test("[testo](indirizzo) nei paragrafi diventa un link, il resto resta testo", () => {
  assert.deepEqual(pezziTesto("Leggi l'[accordo](/condizioni#accordo) e scrivi a [pec](mailto:a@b.it)."), [
    "Leggi l'",
    { testo: "accordo", href: "/condizioni#accordo" },
    " e scrivi a ",
    { testo: "pec", href: "mailto:a@b.it" },
    ".",
  ]);
  assert.deepEqual(pezziTesto("Nessun link (art. 6.1.b)."), ["Nessun link (art. 6.1.b)."]);
});

test("ogni link dell'informativa porta a una pagina nostra, alla PEC o al Garante", () => {
  const pezzi = INFORMATIVA_PRIVACY.sezioni.flatMap((s) => [...s.paragrafi, ...(s.elenco ?? [])]).flatMap(pezziTesto);
  const link = pezzi.filter((p) => typeof p !== "string").map((p) => p.href);
  assert.ok(link.includes("/condizioni#accordo"));
  assert.ok(link.includes(`mailto:${PRODUTTORE.pec}`));
  for (const h of link) assert.match(h, /^(\/|mailto:|https:\/\/www\.garanteprivacy\.it$)/);
});
