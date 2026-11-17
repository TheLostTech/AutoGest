// Cattura gli screenshot del manuale operativo (Autodemolizione 4.0).
// Ogni file ha lo stesso nome del segnaposto nel manuale: «[Screenshot · accettazione-01-oggi]» → accettazione-01-oggi.png
//
// Uso (con il gestionale avviato):
//   cd scripts/manuale && npm install && node cattura.js            tutti i ruoli
//   node cattura.js vendite                                          un ruolo solo
//   BASE=http://localhost:3210 OUT=./screenshot node cattura.js      indirizzo e cartella diversi
//
// Usa il Chrome installato sul computer (nessun browser da scaricare).
// Accanto a ogni .png salva un .txt con il testo della pagina, utile per ricontrollare il manuale.
// Consiglio: prima della cattura premere «Ripristina dati demo», così i dati sono quelli di riferimento.

const { chromium } = require("playwright-core");
const fs = require("fs");
const path = require("path");

const BASE = process.env.BASE || "http://localhost:3210";
const OUT = path.resolve(process.env.OUT || path.join(__dirname, "screenshot"));
fs.mkdirSync(OUT, { recursive: true });

const PC = { width: 1440, height: 900 };
const TELEFONO = { width: 390, height: 844 };

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
  await page.goto(BASE + "/negozio/R-002311", { waitUntil: "networkidle" });
  const b = page.getByRole("button", { name: "Aggiungi al carrello" });
  if (await b.count()) await b.click();
  await page.goto(BASE + "/negozio/carrello", { waitUntil: "networkidle" });
};

const PIANO = [
  ["comune", PC, "accettazione", [["ricerca", "/", apriRicerca]]],
  ["accettazione", PC, "accettazione", [
    ["01-oggi", "/"],
    ["02-veicoli", "/veicoli"],
    ["03-nuovo", "/veicoli/nuovo"],
    ["04-pratica-da-registrare", "/veicoli/V-000115"],
    ["05-pratica-completa", "/veicoli/V-000116"],
    ["07-certificato", "/certificato/V-000116"],
    ["08-ambiente", "/ambiente"],
    ["09-formulari", "/ambiente/formulari"],
    ["10-registro", "/registro"],
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
  ]],
  ["vendite", PC, "vendite", [
    ["01-oggi", "/"],
    ["02-banco", "/vendite"],
    ["03-documenti", "/vendite/documenti"],
    ["04-scontrino", "/documento/DC-2026-0001"],
    ["05-preventivo", "/documento/P-2026-0001"],
    ["06-negozio", "/negozio"],
    ["07-negozio-pezzo", "/negozio/R-002311"],
    ["08-carrello", "/negozio/carrello", aggiungiAlCarrello],
    ["09-ricambio", "/ricambi/R-002302"],
  ]],
  ["responsabile", PC, "responsabile", [
    ["01-oggi", "/"],
    ["02-pubblicazione", "/pubblicazione"],
    ["03-regole", "/regole"],
    ["04-listini", "/listini"],
    ["05-ubicazioni", "/magazzino"],
    ["06-ricambi", "/ricambi"],
    ["07-collegamenti", "/impostazioni/collegamenti"],
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
      await page.screenshot({ path: file + ".png", fullPage: opzioni.fullPage ?? true });
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
