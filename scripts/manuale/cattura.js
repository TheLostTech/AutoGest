// Cattura gli screenshot del manuale operativo (AutoLost).
// Ogni file ha lo stesso nome del segnaposto nel manuale: «[Screenshot · accettazione-01-oggi]» → accettazione-01-oggi.png
//
// Uso (con il gestionale avviato):
//   cd scripts/manuale && npm install && node cattura.js            tutti i ruoli
//   node cattura.js vendite                                          un ruolo solo
//   BASE=http://localhost:3210 OUT=./screenshot node cattura.js      indirizzo e cartella diversi
//
// Usa il Chrome installato sul computer (nessun browser da scaricare).
// Accanto a ogni .png salva un .txt con il testo della pagina, utile per ricontrollare il manuale.
// ATTENZIONE: alcune catture cambiano i dati (scarta un pezzo nei rottami, riempie il carrello, pubblica su eBay simulato).
// Lanciarle su una copia del gestionale con dati demo puliti, mai sui dati veri:
//   git archive HEAD | tar -x -C /tmp/copia && cp -cR node_modules /tmp/copia/   (copia pulita dell'ultimo commit)
//   cd /tmp/copia && DATI_DIR=/tmp/dati-manuale npx next dev -p 3214
//   BASE=http://localhost:3214 node cattura.js
// (cartella DATI_DIR vuota = dati demo di riferimento; controllare che /api/demo-state dia version 0.
//  next dev non parte due volte nella stessa cartella, per questo si usa una copia; node_modules va copiato, non collegato)

const { chromium } = require("playwright-core");
const fs = require("fs");
const path = require("path");

const BASE = process.env.BASE || "http://localhost:3210";
const OUT = path.resolve(process.env.OUT || path.join(__dirname, "screenshot"));
fs.mkdirSync(OUT, { recursive: true });

const PC = { width: 1440, height: 900 };
const TELEFONO = { width: 390, height: 844 };
const MAX_PC = 2400; // altezza massima della cattura, in punti
const MAX_TELEFONO = 2000;

// [nome, percorso, azione facoltativa prima della cattura]
const apriRicerca = async (page) => {
  await page.getByRole("button", { name: /Cerca/ }).filter({ visible: true }).first().click();
  const campo = page.getByLabel("Cerca in tutto il gestionale");
  await campo.waitFor({ timeout: 5000 });
  await campo.fill("Panda");
  await page.waitForTimeout(600);
  return { fullPage: false }; // finestra sopra la pagina: si cattura solo la parte visibile
};
// Apre la verifica del primo ripiano con dei pezzi: uno scaffale fisso può svuotarsi col tempo
const apriPrimoRipiano = async (page) => {
  await page.goto(BASE + "/inventario/1", { waitUntil: "networkidle" });
  await page.waitForTimeout(800);
  await page.getByRole("link", { name: /Verifica/ }).first().click();
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(800);
};
const aggiungiAlCarrello = async (page) => {
  await page.goto(BASE + "/negozio/" + ANNUNCIO, { waitUntil: "networkidle" });
  const b = page.getByRole("button", { name: "Aggiungi al carrello" });
  if (await b.count()) await b.click();
  await page.goto(BASE + "/negozio/carrello", { waitUntil: "networkidle" });
};
// Scansiona un pezzo scrivendo il codice (la fotocamera non c'è nel browser di cattura)
const scansionaPezzo = async (page) => {
  await page.getByPlaceholder(/R-002301/).fill(PEZZO_SCARTO);
  await page.getByRole("button", { name: "Invia" }).click();
  await page.waitForTimeout(800);
};
const scegliScarto = async (page) => {
  await scansionaPezzo(page);
  await page.getByRole("button", { name: /Scarta/ }).first().click();
  await page.waitForTimeout(400);
  await page.getByRole("button", { name: "Rotto o danneggiato" }).click();
  await page.waitForTimeout(400);
};
const mettiNeiRottami = async (page) => {
  await scegliScarto(page);
  await page.getByRole("button", { name: /Metti nei rottami/ }).click();
  await page.waitForTimeout(800);
  await page.goto(BASE + "/rottami", { waitUntil: "networkidle" });
  await page.waitForTimeout(800);
};
const apriFormularioRicevuto = async (page) => {
  await page.getByRole("button", { name: /Registra formulario ricevuto/ }).click();
  await page.waitForTimeout(600);
};
const apriAnteprimaAnnuncio = async (page) => {
  await page.getByRole("button", { name: "Pubblica", exact: true }).first().click();
  await page.waitForTimeout(800);
};
const vaiAgliAnnunci = async (page) => {
  await page.getByText(/^Annunci ·/).first().scrollIntoViewIfNeeded();
  await page.evaluate(() => window.scrollBy(0, -80));
  await page.waitForTimeout(400);
  return { fullPage: false };
};
const pubblicaSuEbay = async (page) => {
  await page.goto(BASE + "/pubblicazione", { waitUntil: "networkidle" });
  await page.waitForTimeout(800);
  const b = page.getByRole("button", { name: /^Pubblica su eBay/ }).first();
  await b.click();
  await page.waitForTimeout(3000); // il ponte simulato risponde dopo qualche istante
  await page.goto(BASE + "/ebay-simulato/" + ANNUNCIO_EBAY, { waitUntil: "networkidle" });
  await page.waitForTimeout(800);
};
const apriEbay = async (page) => {
  const riga = page.getByRole("button", { name: /eBay/ }).first();
  await riga.click();
  await page.waitForTimeout(600);
  await riga.evaluate((el) => window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 24));
  await page.waitForTimeout(400);
  return { fullPage: false }; // solo la scheda eBay aperta
};
const scriviTarga = async (page) => {
  const digita = page.getByRole("button", { name: /Digita la targa/ });
  if (await digita.count()) await digita.first().click();
  await page.getByPlaceholder(/AB123CD/).first().fill("GB512XR");
  const cerca = page.getByRole("button", { name: /Cerca dati veicolo/ });
  if (await cerca.count()) await cerca.first().click();
  await page.waitForTimeout(1500);
};

const PEZZO_SCARTO = process.env.PEZZO_SCARTO || "R-002314"; // un pezzo disponibile a scaffale, non usato nelle altre schermate
const ANNUNCIO = "A-000005"; // annuncio con 3 pezzi uguali nei dati demo
const ANNUNCIO_EBAY = "A-000001";

const PIANO = [
  ["comune", PC, "accettazione", [["ricerca", "/", apriRicerca]]],
  ["accettazione", PC, "accettazione", [
    ["01-oggi", "/"],
    ["02-veicoli", "/veicoli"],
    ["03-nuovo", "/veicoli/nuovo", scriviTarga],
    ["04-pratica-da-registrare", "/veicoli/V-000115"],
    ["05-pratica-completa", "/veicoli/V-000116"],
    ["07-certificato", "/certificato/V-000116"],
    ["08-ambiente", "/ambiente"],
    ["09-formulari", "/ambiente/formulari"],
    ["10-registro", "/registro"],
    ["11-periodo", "/ambiente/periodo?mese=2026-10"],
    ["12-formulario-ricevuto", "/ambiente/formulari", apriFormularioRicevuto],
    ["13-soggetti", "/ambiente/soggetti"],
  ]],
  ["smontatore", TELEFONO, "smontatore", [
    ["01-oggi", "/"],
    ["02-campo", "/campo"],
    ["03-bonifica", "/veicoli/V-000116/bonifica"],
    ["04-campo-veicolo", "/campo/V-000118"],
    ["05-cataloga", "/campo/V-000118/nuovo"],
    ["06-etichetta", "/etichetta/R-002302"],
    ["07-scansione", "/scansione"],
    ["08-ricambi", "/ricambi"],
  ]],
  ["magazziniere", TELEFONO, "magazziniere", [
    ["01-oggi", "/"],
    ["02-inventario", "/inventario"],
    ["03-magazzino1", "/inventario/1"],
    ["04-aggiungi", "/inventario/1/nuovo"],
    ["05-conta", "/inventario/1", apriPrimoRipiano],
    ["06-scansione", "/scansione"],
    ["07-ubicazioni", "/magazzino"],
    ["08-etichette-scaffale", "/etichette-scaffale"],
    ["09-scansione-pezzo", "/scansione", scansionaPezzo],
    ["10-scarta", "/scansione", scegliScarto],
    ["11-rottami", "/scansione", mettiNeiRottami],
  ]],
  ["vendite", PC, "vendite", [
    ["01-oggi", "/"],
    ["02-banco", "/vendite"],
    ["03-documenti", "/vendite/documenti"],
    ["04-scontrino", "/documento/DC-2026-0001"],
    ["05-preventivo", "/documento/P-2026-0001"],
    ["06-negozio", "/negozio"],
    ["07-negozio-pezzo", "/negozio/" + ANNUNCIO],
    ["08-carrello", "/negozio/carrello", aggiungiAlCarrello],
    ["09-ricambio", "/ricambi/R-002302"],
    ["10-esaurito", "/negozio/A-000004"],
  ]],
  ["responsabile", PC, "responsabile", [
    ["01-oggi", "/"],
    ["02-pubblicazione", "/pubblicazione"],
    ["03-regole", "/regole"],
    ["04-listini", "/listini"],
    ["05-ubicazioni", "/magazzino"],
    ["06-ricambi", "/ricambi"],
    ["07-collegamenti", "/impostazioni/collegamenti"],
    ["08-anteprima-annuncio", "/pubblicazione", apriAnteprimaAnnuncio],
    ["09-annunci", "/pubblicazione", vaiAgliAnnunci],
    ["10-ebay-simulato", "/pubblicazione", pubblicaSuEbay],
    ["11-collegamenti-ebay", "/impostazioni/collegamenti", apriEbay],
  ]],
  ["consulente", PC, "consulente", [
    ["01-oggi", "/"],
  ]],
];

async function scegliRuolo(page, ruolo) {
  // Il selettore del ruolo è nella barra laterale (PC) o nella testata (telefono)
  const sels = page.locator(`select:has(option[value="${ruolo}"])`);
  for (let i = 0; i < (await sels.count()); i++) {
    try {
      await sels.nth(i).selectOption(ruolo, { force: true, timeout: 3000 });
      return;
    } catch {}
  }
  throw new Error(`Selettore del ruolo «${ruolo}» non trovato`);
}

(async () => {
  const solo = process.argv[2];
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  let fatti = 0;
  for (const [prefisso, vista, ruolo, pagine] of PIANO) {
    if (solo && solo !== prefisso) continue;
    const telefono = vista === TELEFONO;
    const ctx = await browser.newContext({ viewport: vista, deviceScaleFactor: 2, locale: "it-IT", isMobile: telefono, hasTouch: telefono });
    const page = await ctx.newPage();
    await page.goto(BASE + "/", { waitUntil: "networkidle" });
    await page.waitForTimeout(1200);
    await scegliRuolo(page, ruolo);
    await page.waitForTimeout(600);
    for (const [nome, percorso, prima] of pagine) {
      await page.goto(BASE + percorso, { waitUntil: "networkidle" });
      await page.waitForTimeout(1200);
      const opzioni = (prima && (await prima(page))) || {};
      await page.waitForTimeout(600);
      const file = path.join(OUT, `${prefisso}-${nome}`);
      // Pagina intera, ma tagliata a un'altezza leggibile: elenchi lunghi (registro, etichette) non diventano strisce.
      // Si allunga la finestra invece di usare fullPage: così barra laterale e barra in basso restano al loro posto.
      if (opzioni.fullPage ?? true) {
        await page.evaluate(() => window.scrollTo(0, 0));
        const alta = await page.evaluate(() => document.documentElement.scrollHeight);
        const massimo = telefono ? MAX_TELEFONO : MAX_PC;
        await page.setViewportSize({ width: vista.width, height: Math.max(vista.height, Math.min(alta, massimo)) });
        await page.waitForTimeout(500);
      }
      await page.screenshot({ path: file + ".png" });
      await page.setViewportSize(vista);
      const testo = await page.evaluate(() => (document.querySelector("main") || document.body).innerText);
      fs.writeFileSync(file + ".txt", testo);
      fatti++;
      console.log("ok", `${prefisso}-${nome}`);
    }
    await ctx.close();
  }
  await browser.close();
  console.log(`\n${fatti} schermate in ${OUT}`);
})().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
