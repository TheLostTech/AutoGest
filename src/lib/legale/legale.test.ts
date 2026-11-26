// Documenti legali pubblici (/privacy, /condizioni): versione uguale a quella salvata con il consenso, sezioni, dati di Lostar. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { BRAND, PRODUTTORE } from "../config.ts";
import { VERSIONE_CONDIZIONI, VERSIONE_PRIVACY } from "../consensi.ts";
import { COMMISSIONE_ONLINE, euro, LISTINO } from "../listino.ts";
import { GIORNI_PROVA } from "../abbonamento.ts";
import { ORDINE_MODULI } from "../moduli.ts";
import { dataVersione, FORNITORI, pezziTesto, SERVIZI_COLLEGATI, voceServizioCollegato, type Documento, type Sezione } from "./comune.ts";
import { INFORMATIVA_PRIVACY } from "./privacy.ts";
import { CONDIZIONI } from "./condizioni.ts";

const righeSezione = (s: Sezione) => [...s.paragrafi, ...(s.elenco ?? []), ...(s.dopo ?? []).flatMap((b) => [...b.paragrafi, ...(b.elenco ?? [])])];
const testoSezione = (s: Sezione) => [s.titolo, ...righeSezione(s)].join("\n");
const testoDocumento = (d: Documento) => [d.titolo, ...d.sezioni.map(testoSezione)].join("\n");

test("la versione mostrata è quella salvata con il consenso", () => {
  assert.equal(INFORMATIVA_PRIVACY.versione, VERSIONE_PRIVACY);
  assert.match(VERSIONE_PRIVACY, /^\d{4}-\d{2}-\d{2}$/);
  assert.match(VERSIONE_CONDIZIONI, /^\d{4}-\d{2}-\d{2}$/);
});

test("data della versione scritta per esteso", () => {
  assert.equal(dataVersione("2026-11-27"), "27 novembre 2026");
  assert.equal(dataVersione("2027-01-05"), "5 gennaio 2027");
  assert.equal(dataVersione("2028-02-29"), "29 febbraio 2028");
});

test("data della versione impossibile: errore, non una data sbagliata in pagina", () => {
  for (const v of ["2026-02-31", "2026-02-29", "2026-04-31", "2026-13-01", "2026-00-10", "2026-11-00", "26-11-2026"]) {
    assert.throws(() => dataVersione(v), /Versione non valida/, v);
  }
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
  for (const f of [...FORNITORI, ...SERVIZI_COLLEGATI]) assert.ok(testo.includes(f.nome), `manca «${f.nome}»`);
  assert.ok(testo.includes(BRAND.azienda) && testo.includes(PRODUTTORE.nome));
});

test("fornitori (sub-responsabili) e servizi collegati dall'azienda (titolari autonomi) sono elenchi diversi", () => {
  assert.deepEqual(FORNITORI.map((f) => f.nome), ["Vercel", "Supabase", "Stripe", "Resend"]);
  assert.deepEqual(SERVIZI_COLLEGATI.map((f) => f.nome), ["eBay", "Openapi"]);
  for (const f of SERVIZI_COLLEGATI) assert.ok(f.soloSe, `${f.nome} senza soloSe`);
  const resend = FORNITORI.find((f) => f.nome === "Resend")!;
  assert.match(resend.dove, /Irlanda/);
});

test("ruoli: registro delle attività e account dei dipendenti sono dell'azienda, non un nostro legittimo interesse", () => {
  const finalita = testoSezione(INFORMATIVA_PRIVACY.sezioni.find((s) => s.id === "finalita")!);
  const legittimo = righeSezione(INFORMATIVA_PRIVACY.sezioni.find((s) => s.id === "finalita")!).filter((r) => r.includes("6.1.f"));
  for (const r of legittimo) assert.doesNotMatch(r, /registro delle attività/, r);
  assert.match(finalita, /6\.1\.b/);
  const dati = testoSezione(INFORMATIVA_PRIVACY.sezioni.find((s) => s.id === "dati")!);
  assert.match(dati, /art\. 14/);
  assert.match(dati, /\/condizioni#accordo/);
});

test("nomi del prodotto e dell'azienda presi dal codice, mai scritti a mano nel testo", () => {
  for (const f of ["privacy.ts", "comune.ts", "condizioni.ts"]) {
    const codice = readFileSync(new URL(`./${f}`, import.meta.url), "utf8")
      .split("\n")
      .filter((r) => !r.trim().startsWith("//"))
      .join("\n");
    assert.doesNotMatch(codice, /Piazzale|Lostar|LOSTAR/, f);
  }
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
  const pezzi = INFORMATIVA_PRIVACY.sezioni.flatMap(righeSezione).flatMap(pezziTesto);
  const link = pezzi.filter((p) => typeof p !== "string").map((p) => p.href);
  assert.ok(link.includes("/condizioni#accordo"));
  assert.ok(link.includes(`mailto:${PRODUTTORE.pec}`));
  for (const h of link) assert.match(h, /^(\/|mailto:|https:\/\/www\.garanteprivacy\.it$)/);
});

test("cookie: titolo con la memoria del browser, id invariato; decisione automatica di BotID contestabile alla PEC", () => {
  const cookie = INFORMATIVA_PRIVACY.sezioni.find((s) => s.id === "cookie")!;
  assert.equal(cookie.titolo, "Cookie e memoria del browser");
  const diritti = testoSezione(INFORMATIVA_PRIVACY.sezioni.find((s) => s.id === "diritti")!);
  assert.match(diritti, /BotID/);
  assert.match(diritti, /art\. 22/);
});

test("ordine di lettura: il Garante viene dopo l'elenco dei diritti", () => {
  const diritti = INFORMATIVA_PRIVACY.sezioni.find((s) => s.id === "diritti")!;
  assert.ok(!diritti.paragrafi.some((p) => p.includes("Garante")));
  assert.ok((diritti.dopo ?? []).some((b) => b.paragrafi.some((p) => p.includes("Garante"))));
});

test("servizio collegato: titolare autonomo, con la sua informativa; niente garanzie di trasferimento nostre", () => {
  assert.equal(
    voceServizioCollegato({ nome: "eBay", cosa: "annunci dei ricambi", soloSe: "l'azienda collega il suo account eBay" }),
    "eBay, solo se l'azienda collega il suo account eBay: annunci dei ricambi. È titolare autonomo: dove e come tratta i dati lo dice la sua informativa.",
  );
  for (const f of SERVIZI_COLLEGATI) assert.deepEqual(Object.keys(f).sort(), ["cosa", "nome", "soloSe"], f.nome);
  const fornitori = testoSezione(INFORMATIVA_PRIVACY.sezioni.find((s) => s.id === "fornitori")!);
  assert.match(fornitori, /a uno dei servizi qui sotto/);
  for (const f of SERVIZI_COLLEGATI) assert.ok(fornitori.includes(voceServizioCollegato(f)), f.nome);
});

test("cookie: solo tecnici, compreso quello della verifica in due passaggi", () => {
  const cookie = INFORMATIVA_PRIVACY.sezioni.find((s) => s.id === "cookie")!;
  assert.doesNotMatch(testoSezione(cookie), /due cookie/);
  assert.match(cookie.paragrafi.join("\n"), /Usiamo solo cookie tecnici:/);
  assert.ok(cookie.elenco?.some((v) => v.includes("verifica in due passaggi, per pochi minuti durante l'accesso con il codice")));
});

test("conservazione: email e password 15 minuti; i blocchi del PIN restano finché l'azienda non li toglie", () => {
  const cons = testoSezione(INFORMATIVA_PRIVACY.sezioni.find((s) => s.id === "conservazione")!);
  assert.doesNotMatch(cons, /tentativi di accesso sbagliati: pochi minuti/);
  assert.match(cons, /email e password[^.]*15 minuti/);
  assert.match(cons, /PIN/);
  assert.match(cons, /sblocca il dispositivo/);
});

// Condizioni del servizio (/condizioni), Task 2
const sezioneCondizioni = (id: string) => {
  const s = CONDIZIONI.sezioni.find((x) => x.id === id);
  assert.ok(s, `manca la sezione «${id}»`);
  return s;
};

test("condizioni: versione salvata con il consenso e sezioni in ordine, con l'accordo per ultimo", () => {
  assert.equal(CONDIZIONI.versione, VERSIONE_CONDIZIONI);
  assert.equal(CONDIZIONI.titolo, "Condizioni del servizio");
  assert.deepEqual(
    CONDIZIONI.sezioni.map((s) => s.id),
    ["parti", "servizio", "prova", "abbonamento", "commissione", "disdetta", "dati", "responsabilita", "modifiche", "legge", "accordo"],
  );
  assert.equal(sezioneCondizioni("accordo").titolo, "Allegato: accordo sul trattamento dei dati per conto del cliente (art. 28 GDPR)");
});

test("condizioni: prezzi, prova e commissione presi dal codice", () => {
  const testo = testoDocumento(CONDIZIONI);
  for (const m of ORDINE_MODULI) {
    for (const atteso of [LISTINO[m].nome, euro(LISTINO[m].mese), euro(LISTINO[m].anno)]) assert.ok(testo.includes(atteso), `manca «${atteso}» (${m})`);
  }
  const abbonamento = testoSezione(sezioneCondizioni("abbonamento"));
  for (const m of ORDINE_MODULI) assert.ok(abbonamento.includes(`${LISTINO[m].nome}: ${euro(LISTINO[m].mese)} al mese oppure ${euro(LISTINO[m].anno)} all'anno`), m);
  for (const atteso of ["IVA esclusa", `${GIORNI_PROVA} giorni`, `${COMMISSIONE_ONLINE * 100}%`, "consumatori", "Torino"]) {
    assert.ok(testo.includes(atteso), `manca «${atteso}»`);
  }
  assert.ok(testoSezione(sezioneCondizioni("prova")).includes(`${GIORNI_PROVA} giorni`));
  assert.ok(testoSezione(sezioneCondizioni("commissione")).includes(`${COMMISSIONE_ONLINE * 100}%`));
  assert.match(testoSezione(sezioneCondizioni("commissione")), /banco/);
  assert.match(testoSezione(sezioneCondizioni("legge")), /foro di Torino/);
  assert.match(testoSezione(sezioneCondizioni("parti")), /consumatori/);
});

test("condizioni: nessun prezzo, percentuale o durata della prova scritti a mano nel codice", () => {
  const codice = readFileSync(new URL("./condizioni.ts", import.meta.url), "utf8")
    .split("\n")
    .filter((r) => !r.trim().startsWith("//"))
    .join("\n");
  assert.doesNotMatch(codice, /€|\d\s*%|\d+,\d\d\b/);
  assert.ok(!codice.includes(`${GIORNI_PROVA} giorni`));
});

test("condizioni: Lostar per esteso, PEC e link all'informativa e all'accordo", () => {
  const testo = testoDocumento(CONDIZIONI);
  for (const atteso of [PRODUTTORE.ragioneSociale, PRODUTTORE.sede, PRODUTTORE.piva, PRODUTTORE.rea, BRAND.azienda]) assert.ok(testo.includes(atteso), `manca «${atteso}»`);
  const link = CONDIZIONI.sezioni.flatMap(righeSezione).flatMap(pezziTesto).filter((p) => typeof p !== "string").map((p) => p.href);
  for (const atteso of ["/privacy", "#accordo", `mailto:${PRODUTTORE.pec}`]) assert.ok(link.includes(atteso), `manca il link ${atteso}`);
  for (const h of link) assert.match(h, /^(\/|#|mailto:)/);
});

test("accordo: art. 28, ruoli come nell'informativa, sub-responsabili e servizi collegati fuori elenco", () => {
  const accordo = sezioneCondizioni("accordo");
  const testo = testoSezione(accordo);
  for (const atteso of ["art. 28", "titolare", "responsabile", "dipendenti", "registro delle attività", "proprietari dei veicoli", "ingiustificato ritardo", "12 mesi"]) {
    assert.ok(testo.includes(atteso), `manca «${atteso}»`);
  }
  for (const f of FORNITORI) assert.ok(testo.includes(f.nome), `manca «${f.nome}»`);
  for (const f of SERVIZI_COLLEGATI) assert.ok(testo.includes(voceServizioCollegato(f)), `manca «${f.nome}»`);
  assert.match(testo, /non sono nostri sub-responsabili/);
  // I sub-responsabili sono l'elenco di FORNITORI, i servizi collegati un elenco a parte
  const elenchi = [accordo.elenco ?? [], ...(accordo.dopo ?? []).map((b) => b.elenco ?? [])];
  const sub = elenchi.find((e) => e.some((v) => v.startsWith("Supabase")))!;
  assert.equal(sub.length, FORNITORI.length);
  for (const f of SERVIZI_COLLEGATI) assert.ok(!sub.some((v) => v.startsWith(f.nome)), `${f.nome} tra i sub-responsabili`);
  assert.match(testo, /\[informativa privacy\]\(\/privacy\)/);
});

test("condizioni: Supabase compare solo nell'accordo, mai il suo indirizzo", () => {
  for (const s of CONDIZIONI.sezioni) {
    const testo = testoSezione(s);
    if (s.id !== "accordo") assert.doesNotMatch(testo, /supabase/i, `Supabase nella sezione «${s.id}»`);
    assert.ok(!testo.toLowerCase().includes("supabase.co"), s.id);
  }
  assert.doesNotMatch(CONDIZIONI.titolo, /supabase/i);
});
