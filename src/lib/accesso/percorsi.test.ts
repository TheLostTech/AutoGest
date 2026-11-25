// Percorsi pubblici e ritorno dopo l'accesso. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { percorsoApi, percorsoDaSicuro, percorsoPubblico } from "./percorsi.ts";

test("percorsoDaSicuro rifiuta tutto ciò che può uscire dal sito", () => {
  for (const x of ["//x", "//evil.com", "/\\x", "/\t/x", "/\t/evil.com", "/\n/x", "/\r/x", "/%09/x", "https://evil.com", "javascript:alert(1)", "evil.com", "", "x/y"]) {
    assert.equal(percorsoDaSicuro(x), "/", JSON.stringify(x));
  }
  assert.equal(percorsoDaSicuro(null), "/");
  assert.equal(percorsoDaSicuro(undefined), "/");
});

test("percorsoDaSicuro mantiene un percorso interno con query", () => {
  assert.equal(percorsoDaSicuro("/ricambi?stato=bozza&q=a%20b"), "/ricambi?stato=bozza&q=a%20b");
  assert.equal(percorsoDaSicuro("/veicoli/V-1#note"), "/veicoli/V-1#note");
  assert.equal(percorsoDaSicuro("/"), "/");
});

test("percorsoDaSicuro: il risultato non è mai un indirizzo con due barre iniziali", () => {
  for (const x of ["/./", "//", "/a/..//x", "/%2F/x", "/.//x"]) {
    assert.ok(!percorsoDaSicuro(x).startsWith("//"), x);
  }
});

test("percorsoPubblico", () => {
  for (const p of ["/accesso", "/demo", "/negozio", "/negozio/carrello", "/ebay-simulato/x", "/scopri", "/news/1", "/registrati", "/condizioni", "/robots.txt", "/sitemap.xml"]) {
    assert.equal(percorsoPubblico(p), true, p);
  }
  for (const p of ["/", "/ricambi", "/negozio-finto", "/accessorio", "/registratix", "/condizionix", "/etichetta/X", "/api/demo-state"]) {
    assert.equal(percorsoPubblico(p), false, p);
  }
});

test("percorsoApi", () => {
  assert.equal(percorsoApi("/api"), true);
  assert.equal(percorsoApi("/api/sessione"), true);
  assert.equal(percorsoApi("/apix"), false);
  assert.equal(percorsoApi("/ricambi"), false);
});

test("percorsoPiattaforma riconosce solo l'area del super admin, che non è pubblica", async () => {
  const { percorsoPiattaforma } = await import("./percorsi.ts");
  for (const p of ["/piattaforma", "/piattaforma/nuova", "/piattaforma/aziende/x"]) {
    assert.equal(percorsoPiattaforma(p), true, p);
    assert.equal(percorsoPubblico(p), false, p);
  }
  for (const p of ["/piattaformax", "/", "/api/piattaforma/aziende"]) assert.equal(percorsoPiattaforma(p), false, p);
});

test("percorsoNegozio: negozio ed eBay simulato sì, le altre pagine pubbliche e la gestione no", async () => {
  const { percorsoNegozio } = await import("./percorsi.ts");
  for (const p of ["/negozio", "/negozio/A-000001", "/negozio/carrello", "/ebay-simulato/A-000001"]) assert.equal(percorsoNegozio(p), true, p);
  for (const p of ["/", "/scopri", "/news", "/accesso", "/negozi", "/negozio-x", "/vendite"]) assert.equal(percorsoNegozio(p), false, p);
});
