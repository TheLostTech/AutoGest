import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import { indirizzoPubblico, originiVercel } from "./indirizzo";
import { inviaEmail } from "./invia";
import { emailConferma, emailProvaFinita, emailProvaInScadenza } from "./modelli";

const LINK = "https://app.example.test/x?t=1&u=2";
const PIEDE = "LOSTAR S.R.L.S. · Corso Massimo d'Azeglio 60, 10126 Torino (TO) · P. IVA e C.F. 13018890015 · REA TO-1333294";
const PIEDE_HTML = PIEDE.replace("'", "&#39;");
const MOTIVO = "Ricevi questa email perché ti sei registrato a Piazzale.";

const modelli = {
  conferma: emailConferma("Mario", LINK),
  scadenza: emailProvaInScadenza("Mario", 3, LINK),
  finita: emailProvaFinita("Mario", LINK),
};

describe("modelli email", () => {
  for (const [nome, e] of Object.entries(modelli)) {
    it(`${nome}: link, piede, motivo e privacy in testo e HTML`, () => {
      assert.ok(e.testo.includes(LINK));
      assert.ok(e.html.includes(LINK.replace(/&/g, "&amp;")));
      assert.ok(e.testo.includes(PIEDE));
      assert.ok(e.html.includes(PIEDE_HTML));
      assert.ok(e.testo.includes(MOTIVO) && e.html.includes(MOTIVO));
      assert.ok(e.testo.includes("/privacy") && e.html.includes("/privacy"));
      assert.ok(!/supabase/i.test(e.oggetto + e.testo + e.html));
    });
  }

  it("privacy: link assoluto preso dal link dell'email quando manca l'indirizzo pubblico", () => {
    for (const e of Object.values(modelli)) {
      assert.ok(e.testo.includes("Informativa privacy: https://app.example.test/privacy"), e.testo);
      assert.ok(e.html.includes('href="https://app.example.test/privacy"'));
    }
  });

  it("scappa i caratteri speciali del nome", () => {
    const e = emailConferma("<b>X</b>", LINK);
    assert.ok(e.html.includes("&lt;b&gt;X&lt;/b&gt;"));
    assert.ok(!e.html.includes("<b>X</b>"));
  });

  it("conferma: avverte chi non si è registrato", () => {
    const frase = "Se non sei stato tu a registrarti, ignora questo messaggio: senza conferma non succede nulla.";
    assert.ok(modelli.conferma.testo.includes(frase));
    assert.ok(modelli.conferma.html.includes(frase));
  });

  it("in scadenza: giorni nell'oggetto", () => {
    assert.ok(modelli.scadenza.oggetto.includes("3 giorni"));
    assert.ok(emailProvaInScadenza("M", 1, LINK).oggetto.includes("domani"));
  });
});

describe("indirizzoPubblico", () => {
  it("BETTER_AUTH_URL ha la precedenza, senza barra finale", () => {
    assert.equal(indirizzoPubblico({ BETTER_AUTH_URL: "https://a.it/", VERCEL: "1", VERCEL_URL: "x.vercel.app" }), "https://a.it");
  });
  it("su Vercel usa il ramo, poi il deploy", () => {
    assert.equal(indirizzoPubblico({ VERCEL: "1", VERCEL_BRANCH_URL: "b.vercel.app", VERCEL_URL: "d.vercel.app" }), "https://b.vercel.app");
    assert.equal(indirizzoPubblico({ VERCEL: "1", VERCEL_URL: "d.vercel.app" }), "https://d.vercel.app");
  });
  it("su Vercel in produzione usa l'indirizzo di produzione del progetto", () => {
    const env = { VERCEL: "1", VERCEL_ENV: "production", VERCEL_PROJECT_PRODUCTION_URL: "app.piazzale.it", VERCEL_BRANCH_URL: "b.vercel.app", VERCEL_URL: "d.vercel.app" };
    assert.equal(indirizzoPubblico(env), "https://app.piazzale.it");
    assert.equal(indirizzoPubblico({ ...env, VERCEL_ENV: "preview" }), "https://b.vercel.app");
    assert.equal(indirizzoPubblico({ ...env, VERCEL_PROJECT_PRODUCTION_URL: "" }), "https://b.vercel.app");
  });
  it("in locale è null", () => {
    assert.equal(indirizzoPubblico({}), null);
    assert.deepEqual(originiVercel({}), []);
  });
  it("origini Vercel senza doppioni", () => {
    assert.deepEqual(originiVercel({ VERCEL: "1", VERCEL_URL: "d.v.app", VERCEL_BRANCH_URL: "d.v.app", VERCEL_PROJECT_PRODUCTION_URL: "p.it" }), ["https://d.v.app", "https://p.it"]);
  });
});

describe("inviaEmail", () => {
  const env = { ...process.env };
  const fetchOriginale = globalThis.fetch;
  const logOriginale = console.log;
  const erroreOriginale = console.error;
  afterEach(() => {
    process.env = { ...env };
    globalThis.fetch = fetchOriginale;
    console.log = logOriginale;
    console.error = erroreOriginale;
  });
  const e = { a: "x@y.it", oggetto: "Ciao", testo: "t", html: "<p>t</p>" };

  it("con chiave chiama Resend con intestazione e corpo giusti", async () => {
    process.env.RESEND_API_KEY = "re_prova";
    process.env.EMAIL_MITTENTE = "Lostar Technology <noreply@lostartechnology.com>";
    let chiamata: { url: string; init: RequestInit } | null = null;
    globalThis.fetch = (async (url: string, init: RequestInit) => {
      chiamata = { url, init };
      return new Response("{}", { status: 200 });
    }) as typeof fetch;
    await inviaEmail(e);
    assert.equal(chiamata!.url, "https://api.resend.com/emails");
    assert.ok(chiamata!.init.signal instanceof AbortSignal, "la richiesta ha un tempo massimo");
    assert.equal((chiamata!.init.headers as Record<string, string>).Authorization, "Bearer re_prova");
    assert.deepEqual(JSON.parse(chiamata!.init.body as string), {
      from: "Lostar Technology <noreply@lostartechnology.com>",
      to: ["x@y.it"],
      subject: "Ciao",
      text: "t",
      html: "<p>t</p>",
    });
  });

  it("errore HTTP: lancia; nel log né la chiave né il contenuto dell'email", async () => {
    process.env.RESEND_API_KEY = "re_segreta";
    process.env.EMAIL_MITTENTE = "Lostar Technology <noreply@lostartechnology.com>";
    const segreto = { a: "x@y.it", oggetto: "Ciao", testo: "testo-riservato-123", html: "<p>html-riservato-456</p>" };
    // Anche se Resend rimandasse indietro chiave e contenuto, nel log non arrivano
    globalThis.fetch = (async () =>
      new Response(JSON.stringify({ name: "validation_error", message: `re_segreta testo-riservato-123 html-riservato-456 x@y.it` }), { status: 422 })) as typeof fetch;
    const righe: string[] = [];
    console.error = (...a: unknown[]) => righe.push(a.map(String).join(" "));
    await assert.rejects(inviaEmail(segreto), (x: Error) => x.message === "Email non inviata");
    const log = righe.join("\n");
    assert.ok(log.includes("422"), log);
    for (const vietato of ["re_segreta", "testo-riservato-123", "html-riservato-456"]) assert.ok(!log.includes(vietato), `${vietato} nel log: ${log}`);
  });

  it("con la chiave ma senza mittente: lancia senza chiamare Resend", async () => {
    process.env.RESEND_API_KEY = "re_prova";
    delete process.env.EMAIL_MITTENTE;
    let fetchChiamata = false;
    globalThis.fetch = (async () => {
      fetchChiamata = true;
      return new Response("{}");
    }) as typeof fetch;
    await assert.rejects(inviaEmail(e), (x: Error) => x.message === "Invio email non configurato");
    assert.equal(fetchChiamata, false);
  });

  it("senza chiave fuori produzione: niente fetch, scrive nel log", async () => {
    delete process.env.RESEND_API_KEY;
    (process.env as Record<string, string>).NODE_ENV = "test";
    let fetchChiamata = false;
    globalThis.fetch = (async () => {
      fetchChiamata = true;
      return new Response("{}");
    }) as typeof fetch;
    const righe: string[] = [];
    console.log = (m: string) => righe.push(m);
    await inviaEmail(e);
    assert.equal(fetchChiamata, false);
    assert.ok(righe[0].startsWith("[email] a x@y.it: Ciao"));
  });

  it("senza chiave in produzione: lancia", async () => {
    delete process.env.RESEND_API_KEY;
    (process.env as Record<string, string>).NODE_ENV = "production";
    await assert.rejects(inviaEmail(e), (x: Error) => x.message === "Invio email non configurato");
  });
});
