# Pubblica su eBay e annunci con più pezzi: piano

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** l'annuncio diventa una cosa a sé che raggruppa i pezzi uguali, va sul negozio e su eBay con un tocco, resta in piedi a zero pezzi e tiene una sola giacenza su tutti i canali. eBay è simulato oppure sandbox.

**Architecture:**
- La logica (raggruppamento, quantità, testo, richiesta a eBay) sta in moduli puri in `src/lib`, testati con `node --test`.
- Lo store Zustand ottiene l'elenco `annunci`, condiviso via `/api/demo-state`, e le azioni che lo usano. `Part.listing` sparisce: lo stato online si ricava dall'annuncio.
- Il "ponte eBay" è un insieme di route sotto `/api/ebay/` con due implementazioni della stessa interfaccia, simulata e sandbox.
- Un esecutore nell'app manda al ponte gli annunci "da riallineare" e importa le vendite.

**Tech Stack:** Next.js 16.4.6 (App Router, `page.tsx` + `view.tsx`), TypeScript, Zustand persist + sync `/api/demo-state`, Tailwind v4, `node --test` (Node 26, type stripping), API REST eBay (Inventory, Account, Media, Taxonomy, Fulfillment) e Trading API XML per `SetUserPreferences`.

**Spec:** `docs/superpowers/specs/2026-11-18-pubblica-ebay-design.md`

## Global Constraints
- **Moduli puri** (`annunci.ts`, `annuncio-testo.ts`, `ebay/richiesta.ts`, `ebay/simulato.ts`): solo `import type` da altri moduli. I dati del catalogo (`typeById`, `PLATFORMS`) si passano come parametri, perché i test girano con `node --test` senza risolvere import senza estensione. I test importano con estensione `.ts` (es. `from "./annunci.ts"`).
- **Prima di scrivere una route**, leggere `node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/route.md` (Next 16 diverso dalle versioni note, vedi `AGENTS.md`). Seguire il modello di `src/app/api/collegamenti/route.ts`: `await connection()`, `Cache-Control: no-store`, blocco delle richieste da altri siti (`altroSito`).
- **Commissione online:** prezzo su negozio ed eBay = `onlinePrice(annuncio.price)` da `src/lib/pricing.ts` (+8%). Al banco il prezzo base.
- **Chiave di raggruppamento:** stesso `typeId`, codice originale **verificato** normalizzato (maiuscolo, senza spazi, punti e trattini), stesso `side`, stessa `condition`, stessa spedibilità. Senza codice verificato nessuna chiave.
- **Quantità** = pezzi dell'annuncio in stato `"disponibile"`. **Prossimo a partire** = `createdAt` più vecchio tra i disponibili.
- **Titolo eBay** ≤ 80 caratteri.
- **Categoria eBay Italia:** albero `101`, marketplace `EBAY_IT`, valuta `EUR`, `Content-Language: it-IT`.
- **Spedizione per eBay:** `"ritiro"` se il pezzo non è spedibile; `"voluminoso"` se è spedibile ma il tipo ha `shippable: false`; altrimenti `"corriere"`.
- **GPSR:** anno del veicolo d'origine `< 2024` → esente; `2024` o senza anno → da confermare dall'operatore; `> 2024` → produttore dalla tabella marca, oppure da confermare.
- **Credenziali e token eBay** solo sul server, cifrati con `cifra`/`decifra` (`src/lib/cifratura.ts`), mai nel browser.
- **Testi dell'interfaccia** in italiano semplice; componenti da `src/components/ui.tsx`.
- **Nuova chiave dei dati demo:** `STORE_SCHEMA = "gestionale-demolizione-demo-v12"`.
- **Commit solo dei file del compito** (`git add` con percorsi esatti): nella cartella ci sono modifiche di altri lavori non salvate. Si committa solo se Alessandro l'ha chiesto per questa esecuzione.

## Review Focus
1. **Vendita eBay mentre l'ultimo pezzo è appena andato al banco:** l'ordine eBay si crea comunque, segnato "da gestire: mancano N pezzi", e nessun pezzo venduto due volte. Test in Task 5: `importa vendita con più pezzi di quelli disponibili`.
2. **Annuncio a zero:** su eBay si manda quantità 0 con l'annuncio ancora attivo, non un ritiro; sul negozio la pagina resta con "Esaurito". Test in Task 8: `a zero pezzi la richiesta resta attiva con quantità 0`.
3. **Pezzo reso:** torna in bozza, non conta nella quantità, e quando ridiventa disponibile riattiva da solo il suo annuncio senza crearne un altro. Test in Task 2: `un pezzo reso non conta finché non torna disponibile`.
4. **Errore di eBay:** l'annuncio resta "da riallineare" con l'errore in chiaro e riparte al giro successivo. Test in Task 8: `prezzo che finisce in ,13 dà errore simulato`. Test in Task 9: `dopo un errore l'annuncio resta da riallineare`.
5. **Codici originali scritti in modi diversi** ("50 510.123-a" e "50510123A") devono unirsi; nomi lunghi o accentati (Citroën) devono restare entro 80 caratteri. Test in Task 2 e Task 3.

---

### Task 1: Spedizione sì o no, pezzo per pezzo

**Files:**
- Modify: `src/lib/types.ts` (interfaccia `Part`)
- Create: `src/lib/spedizione.ts`
- Create: `src/lib/spedizione.test.ts`
- Create: `src/components/ShippingChoice.tsx`
- Modify: `src/app/(app)/campo/[id]/nuovo/view.tsx`, `src/app/(app)/inventario/[mag]/nuovo/view.tsx`, `src/app/(app)/inventario/conta/view.tsx` (campo nel form e in `addPart`)
- Modify: `src/app/(app)/ricambi/[id]/view.tsx:221`, `src/components/PartDetailSheet.tsx:97`, `src/lib/logic.ts:87`, `src/app/negozio/[id]/view.tsx:87`, `src/app/negozio/carrello/view.tsx:27` (da `t.shippable` a `isShippable`)

**Interfaces:**
- Produces: `Part.spedibile?: boolean`; `isShippable(p: Pick<Part, "spedibile">, typeShippable: boolean): boolean`; `asksShipping(typeShippable: boolean): boolean`; componente `<ShippingChoice value={boolean} onChange={(v: boolean) => void} />`.

- [ ] **Step 1: Write the failing test** in `src/lib/spedizione.test.ts`

```ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { asksShipping, isShippable } from "./spedizione.ts";

test("i tipi spedibili restano sempre spedibili", () => {
  assert.equal(isShippable({}, true), true);
  assert.equal(isShippable({ spedibile: false }, true), true);
  assert.equal(asksShipping(true), false);
});

test("i tipi ingombranti sono solo ritiro finché non si sceglie di spedirli", () => {
  assert.equal(isShippable({}, false), false);
  assert.equal(isShippable({ spedibile: true }, false), true);
  assert.equal(asksShipping(false), true);
});
```

- [ ] **Step 2:** Run `node --test src/lib/spedizione.test.ts`. Expected: FAIL, modulo mancante.
- [ ] **Step 3: Implement `isShippable` and `asksShipping`** in `src/lib/spedizione.ts`, con solo `import type`. Aggiungere `spedibile?: boolean` a `Part`, con il commento "solo per i tipi non spedibili di serie: scelto alla creazione".
- [ ] **Step 4:** Run `node --test src/lib/spedizione.test.ts`. Expected: PASS.
- [ ] **Step 5: `ShippingChoice`.** Due pulsanti grandi, "Sì, con corriere" e "No, solo ritiro in sede", con la domanda "Si può spedire?". Nei tre form compare solo se `asksShipping(t.shippable)`; valore iniziale `false`; passato ad `addPart` come `spedibile` solo per quei tipi.
- [ ] **Step 6: Scheda ricambio.** La riga "Spedizione" usa `isShippable(p, t.shippable)`. Per i tipi ingombranti offre `ShippingChoice`, che salva con `updatePart(id, { spedibile }, "Spedizione modificata", "…")`.
- [ ] **Step 7: Sostituire `t.shippable` con `isShippable(p, t.shippable)`** dove si vende (file elencati sopra). `warehouseFor(...)` resta su `t.shippable`.
- [ ] **Step 8:** Run `npx tsc --noEmit -p . && npm test`. Expected: nessun errore, tutti i test passano.
- [ ] **Step 9: Commit** `feat: spedizione sì o no per i pezzi ingombranti`

---

### Task 2: Modello puro degli annunci

**Files:**
- Modify: `src/lib/types.ts` (nuovi tipi)
- Create: `src/lib/annunci.ts`
- Create: `src/lib/annunci.test.ts`

**Interfaces:**
- Consumes: `Part`, `Condition`, `ListingStatus` da `types.ts`; `isShippable` (Task 1) come parametro già calcolato.
- Produces (in `types.ts`):

```ts
export type StatoNegozio = "online" | "esaurito" | "ritirato";
export type StatoEbay = "non pubblicato" | "in pubblicazione" | "online" | "esaurito" | "chiuso da eBay" | "ritirato" | "errore";
export interface VeicoloCompat { marca: string; modello: string; anno?: number; anni?: string; motore?: string }
export interface Produttore { ragioneSociale: string; indirizzo: string; citta: string; cap: string; paese: string; email?: string; sito?: string }
export type Gpsr = { tipo: "esente" } | { tipo: "produttore"; produttore: Produttore } | { tipo: "da confermare" };
export interface AnnuncioEbay {
  stato: StatoEbay; daRiallineare: boolean;
  listingId?: string; url?: string; categoria?: { id: string; nome: string };
  quantitaInviata?: number; prezzoInviato?: number; errore?: string; avvisi?: string[]; aggiornatoAt?: string;
}
export interface Annuncio {
  id: string; // A-000001
  chiave?: string;
  typeId: string; side?: string; condition: Condition; oem?: string; spedibile: boolean;
  price: number; // prezzo base dell'autodemolizione
  titolo: string; descrizione: string; testoModificato: boolean;
  caratteristiche: Record<string, string>;
  gpsr: Gpsr;
  negozio?: { stato: StatoNegozio };
  ebay?: AnnuncioEbay;
  createdAt: string; esauritoDa?: string;
}
```

  `Part` ottiene `annuncioId?: string`. In questo task `listing` resta: lo toglie il Task 4.
- Produces (in `annunci.ts`):
  - `normalizeOem(oem: string): string`
  - `groupKey(p: Part, shippable: boolean): string | undefined`. Formato `${typeId}|${oem}|${side ?? "-"}|${condition}|${shippable ? "S" : "R"}`.
  - `partsOf(a: Annuncio, parts: Part[]): Part[]`
  - `quantityOf(a: Annuncio, parts: Part[]): number`
  - `nextToShip(a: Annuncio, parts: Part[], n?: number): Part[]` (di serie `n = 1`)
  - `isWithdrawn(a: Annuncio): boolean`: negozio `"ritirato"` ed eBay assente o `"ritirato"`.
  - `negozioStato(a: Annuncio, qty: number): StatoNegozio | undefined`: lascia `"ritirato"` com'è, altrimenti `qty > 0 ? "online" : "esaurito"`.
  - `type Placement = { kind: "nuovo" } | { kind: "unisci"; annuncioId: string } | { kind: "prezzo diverso"; annuncioId: string; prezzoAnnuncio: number } | { kind: "annuncio ritirato"; annuncioId: string }`
  - `placementFor(p: Part, key: string | undefined, annunci: Annuncio[]): Placement`
  - `listingOf(p: Part, annunci: Annuncio[]): ListingStatus`:
    - `"pubblicato"` se il pezzo ha `annuncioId`, è `disponibile` o `riservato`, e l'annuncio è su almeno un canale non ritirato;
    - `"ritirato"` se ha `annuncioId` ma non è pubblicato;
    - altrimenti `"non pubblicato"`.

- [ ] **Step 1: Write the failing tests** in `src/lib/annunci.test.ts`. Helper `part(over)` e `annuncio(over)` con valori di base. Test:
  - `codici scritti in modi diversi danno la stessa chiave`: `normalizeOem("50 510.123-a") === "50510123A"`; `groupKey` di due pezzi con quei codici è uguale.
  - `senza codice verificato nessuna chiave`: `oemVerified: false` → `undefined`.
  - `lato, condizione o spedibilità diversi danno chiavi diverse`.
  - `la quantità conta solo i disponibili`: pezzi in stato disponibile, disponibile, riservato e venduto → 2.
  - `parte per primo il pezzo entrato prima`: `nextToShip(a, parts, 2)` ordina per `createdAt` crescente.
  - `un pezzo reso non conta finché non torna disponibile`: pezzo con `annuncioId` in `"bozza"` → quantità 0 e `listingOf` = `"ritirato"`. Lo stesso pezzo `"disponibile"` → quantità 1 e `"pubblicato"`.
  - `placementFor`, quattro casi:
    - nessun annuncio → `nuovo`;
    - stesso prezzo → `unisci`;
    - prezzo 95 contro 90 → `{ kind: "prezzo diverso", prezzoAnnuncio: 90 }`;
    - annuncio ritirato → `annuncio ritirato`.
  - `senza chiave il pezzo fa sempre un annuncio nuovo`.
  - `negozioStato`: 0 → esaurito; 2 → online; ritirato resta ritirato.
- [ ] **Step 2:** Run `node --test src/lib/annunci.test.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** in `src/lib/annunci.ts` le firme sopra, aggiungendo i tipi a `types.ts`. `placementFor` cerca un annuncio con `a.chiave === key`; un pezzo senza prezzo dà sempre `nuovo`.
- [ ] **Step 4:** Run `node --test src/lib/annunci.test.ts`. Expected: PASS.
- [ ] **Step 5: Commit** `feat: modello degli annunci con più pezzi`

---

### Task 3: Testo dell'annuncio scritto in automatico

**Files:**
- Create: `src/lib/annuncio-testo.ts`
- Create: `src/lib/annuncio-testo.test.ts`

**Interfaces:**
- Consumes: `Annuncio`, `Part`, `Vehicle`, `VeicoloCompat`, `Gpsr`, `Produttore` (Task 2); `CONDITIONS` e `PLATFORMS` passati come parametri.
- Produces:
  - `buildTitle(t: { tipo: string; lato?: string; marca?: string; modello?: string; versione?: string; anni?: string; oem?: string }): string`
  - `buildDescription(d: { condizione: string; spiegazione: string; difetti?: string; km?: number; veicolo?: string; oem?: string; spedibile: boolean; quanti: number }): string`
  - `compatVehicles(parts: Part[], vehicles: Vehicle[], platforms: { id: string; make: string; model: string; years: string }[]): VeicoloCompat[]`
  - `aspectsFor(d: { marca?: string; oem?: string; lato?: string; tipo: string }): Record<string, string>`: chiavi "Marca", "Numero ricambio produttore", "Posizionamento sul veicolo", "Tipo".
  - `gpsrFor(anno: number | undefined, marca: string | undefined): Gpsr`
  - `PRODUTTORI: Record<string, Produttore>`: tabella marca → produttore, compilata da chi costruisce dai siti ufficiali delle case. Le marche non in tabella danno "da confermare".
  - `EBAY_CATEGORY_QUERY: Record<string, string>`: `typeId` → parole per cercare la categoria (es. `faro: "faro anteriore auto"`), una voce per ogni `PART_TYPES`.
  - `generateText(input: { tipo: string; lato?: string; marca?: string; modello?: string; versione?: string; anno?: number; oem?: string; condizione: string; spiegazione: string; difetti?: string; km?: number; spedibile: boolean; quanti: number }): { titolo: string; descrizione: string }`

- [ ] **Step 1: Write the failing tests:**
  - `il titolo completo sta in 80 caratteri`: `buildTitle({ tipo: "Faro anteriore", lato: "dx", marca: "Alfa Romeo", modello: "Giulietta", versione: "1.4 T-Jet 120 CV", anni: "2014", oem: "50510123" })` = `"Faro anteriore dx Alfa Romeo Giulietta 1.4 T-Jet 120 CV 2014 OE 50510123 usato"`.
  - `se è troppo lungo toglie prima la versione, poi gli anni, e tiene il codice`: con versione di 40 caratteri il risultato non contiene la versione, contiene "OE 50510123" e ha `length <= 80`. Con anche il modello lunghissimo la lunghezza resta `<= 80` e finisce con "usato".
  - `nomi accentati entro 80 caratteri`: marca "Citroën", modello "C4 Grand Picasso" → `length <= 80` e contiene "Citroën".
  - `con più pezzi la descrizione non dà km e difetti del singolo`: `quanti: 3` → niente "km", contiene "Disponibili 3 pezzi uguali". `quanti: 1` con `km: 120000` → contiene "120.000 km".
  - `solo ritiro scritto nella descrizione`: `spedibile: false` → contiene "Solo ritiro in sede".
  - `compatibilità senza doppioni`: due pezzi dallo stesso veicolo, più una piattaforma verificata con lo stesso modello → un veicolo d'origine e una voce piattaforma con `anni`.
  - `gpsr`: `gpsrFor(2014, "Fiat")` → esente; `gpsrFor(2024, "Fiat")` → da confermare; `gpsrFor(undefined, "Fiat")` → da confermare; `gpsrFor(2025, "MarcaSconosciuta")` → da confermare.
  - `ogni tipo di pezzo ha le parole per la categoria`: ogni id passato nel test, preso da `PART_TYPES`, ha una voce in `EBAY_CATEGORY_QUERY`.
- [ ] **Step 2:** Run `node --test src/lib/annuncio-testo.test.ts`. Expected: FAIL.
- [ ] **Step 3: Implement.** Il titolo si accorcia in quest'ordine: senza versione, poi senza anni, poi modello troncato a parola intera. "OE <codice>" e "usato" restano sempre. La descrizione elenca: condizione con la spiegazione, difetti, km del veicolo d'origine, veicolo d'origine, codice originale, la riga "Pezzo controllato e catalogato con codice univoco", e spedizione con corriere oppure solo ritiro in sede. Con `quanti > 1` aggiunge "Disponibili N pezzi uguali: le foto mostrano il pezzo che riceverai".
- [ ] **Step 4:** Run `node --test src/lib/annuncio-testo.test.ts`. Expected: PASS.
- [ ] **Step 5: Commit** `feat: testo automatico degli annunci`

---

### Task 4: Store, gli annunci al posto di `Part.listing`

**Files:**
- Modify: `src/lib/types.ts` (togliere `listing` da `Part`; `ListingStatus` resta come tipo calcolato)
- Modify: `src/lib/store.ts` (stato `annunci`, `counters.annuncio`, `STORE_SCHEMA` v12, tutte le righe con `listing`)
- Modify: `src/lib/sync.ts:6` (aggiungere `"annunci"` a `PREPEND`)
- Modify: `src/lib/seed.ts:206,214` (annunci al posto di `listing`)
- Modify: tutti i lettori di `listing`:
  - `src/app/(app)/view.tsx:76`
  - `src/app/(app)/pubblicazione/view.tsx:14,18`
  - `src/app/(app)/ricambi/[id]/view.tsx:56,291`
  - `src/app/(app)/scansione/view.tsx:165`
  - `src/components/PartRow.tsx:22`
  - `src/components/PartDetailSheet.tsx:169`
  - `src/components/Lifecycle.tsx:20,59`
  - `src/lib/agenda.ts:201`
  - `src/app/negozio/*`, temporaneamente: il Task 7 li rifà

**Interfaces:**
- Consumes: `listingOf`, `groupKey`, `quantityOf`, `negozioStato` (Task 2); `generateText`, `gpsrFor`, `aspectsFor` (Task 3); `isShippable` (Task 1).
- Produces:
  - stato `annunci: Annuncio[]`;
  - hook `useListing(p: Part): ListingStatus`, che legge `annunci` dallo store e chiama `listingOf`;
  - `buildAnnuncio(seed: Part[], vehicles: Vehicle[], id: string, at: string): Annuncio`, esportata da `store.ts` e usata anche dal seed. Prezzo, testo, caratteristiche e GPSR vengono dal primo pezzo; `negozio: { stato: "online" }`; niente `ebay`.

- [ ] **Step 1: Struttura dello stato.**
  - `annunci` entra in `State`, `initial()`, `reset` e nella persistenza.
  - `Counters.annuncio: number`.
  - `STORE_SCHEMA = "gestionale-demolizione-demo-v12"`.
  - In `sync.ts` aggiungere `"annunci"` a `PREPEND`.
- [ ] **Step 2: Seed.** Al posto di `listing: published ? …`, i pezzi `published` si raggruppano con `groupKey`. Ogni gruppo, e ogni pezzo senza chiave, diventa un annuncio `buildAnnuncio(...)` con `annuncioId` sui pezzi. L'evento di registro diventa "Annuncio A-… pubblicato sul negozio".
- [ ] **Step 3: Togliere `listing` da `Part` e sistemare tutti i punti** che il compilatore segnala.
  - Le azioni dello store che scrivevano `listing` smettono di farlo: oggi la quantità e lo stato si ricavano.
    - `updatePart`: la riga `unpriced`.
    - `scrapPart` e `unscrapPart`: `prev` diventa `Pick<Part, "status" | "location">`.
    - `setPartStatus`, `payOrder`, `returnOrder`.
  - `createOrder` per i canali non banco controlla `listingOf(p, annunci) === "pubblicato"`.
  - `agenda.ts:201` conta i pezzi `disponibile` senza `annuncioId`.
  - `ListingChip` riceve `useListing(p)`.
- [ ] **Step 4:** Run `npx tsc --noEmit -p . && npm test`. Expected: nessun errore, tutti i test passano.
- [ ] **Step 5: Prova nel browser.**
  - Avviare il server dalla scheda terminale "dev server" (`npm run dev -- -p 3210`) e aprire l'anteprima "gestionale".
  - Dopo "Ripristina dati demo": la home mostra un numero sotto "Online sul negozio", la scheda di un pezzo pubblicato mostra "online", nessun errore in console.
- [ ] **Step 6: Commit** `refactor: lo stato online dei pezzi viene dall'annuncio`

---

### Task 5: Store, pubblicare, unire, prezzo, ritirare, vendere

**Files:**
- Modify: `src/lib/annunci.ts` (funzioni pure per le vendite)
- Modify: `src/lib/annunci.test.ts`
- Modify: `src/lib/store.ts` (azioni nuove; `publish`/`unpublish` sostituite)
- Modify: `src/lib/types.ts` (`Order`)
- Create: `src/lib/ebay/contratto.ts` (solo tipi, vedi Task 8 per il contenuto completo: qui si crea il file con tutto il blocco di tipi)

**Interfaces:**
- Consumes: tutto quanto prodotto dai Task 2–4.
- Produces: `src/lib/ebay/contratto.ts` con i tipi elencati nel Task 8 (`ModoEbay`, `SpedizioneEbay`, `RichiestaAllinea`, `EsitoAllinea`, `VenditaEbay`, `StatoPonte`, `Ponte`).
- Produces (puri, in `annunci.ts`):
  - `pickForSale(a: Annuncio, parts: Part[], quantita: number): { partIds: string[]; mancano: number }`
- Produces (`Order`): `ebayOrderId?: string`, `daGestire?: string`; `Channel` resta `"marketplace"` per eBay.
- Produces (azioni dello store; `Result` come oggi):
  - `publishAnnuncio(partId: string, bozza: { titolo: string; descrizione: string; testoModificato: boolean; caratteristiche: Record<string, string>; gpsr: Gpsr; canali: { negozio: boolean; ebay: boolean } }): Result<string>`: crea l'annuncio (id `A-${pad(n)}`) con chiave, `ebay: { stato: "in pubblicazione", daRiallineare: true }` se `canali.ebay`.
  - `placePart(partId: string): void`: chiamata da `setPartStatus` e `updatePart` quando il pezzo diventa `disponibile` e passa `publishChecks`; chiama `placementFor` e, se `unisci`, mette `annuncioId` e ricalcola.
  - `resolvePrice(partId: string, scelta: "annuncio" | "pezzo"): void`
  - `setAnnuncioPrice(annuncioId: string, price: number): void`: aggiorna `price` dell'annuncio e di tutti i suoi pezzi.
  - `withdrawAnnuncio(annuncioId: string, canale: "negozio" | "ebay" | "tutti"): void`
  - `republishAnnuncio(annuncioId: string, canali: { negozio: boolean; ebay: boolean }): void`
  - `editAnnuncioText(annuncioId: string, titolo: string, descrizione: string): void`: `testoModificato: true`.
  - `regenerateText(annuncioId: string): void`: `testoModificato: false`.
  - `orderFromAnnunci(channel: "negozio", annuncioIds: string[], customer: string, actor?: …, delivery?: "corriere" | "ritiro"): Result<string>`
  - `importEbaySale(v: VenditaEbay): Result<string>`: ordine `marketplace` già `"pagato"`, con `ebayOrderId`. Ignora le vendite con un `ebayOrderId` già importato.
  - Interna `touchAnnuncio(id)`, dopo ogni cambiamento che tocca quantità o dati:
    - ricalcola `negozio.stato` con `negozioStato`;
    - imposta `esauritoDa` (alla prima volta a zero; si cancella quando torna sopra zero);
    - se l'annuncio ha `ebay` non ritirato, mette `ebay.daRiallineare = true`;
    - se `testoModificato` è falso, rigenera titolo e descrizione con `quanti` aggiornato.
  - **Cambio di chiave** in `updatePart`, se l'annuncio ha più di un pezzo: il pezzo perde `annuncioId`, poi `placePart`. Con un solo pezzo si aggiornano i campi dell'annuncio.

- [ ] **Step 1: Write the failing tests** in `annunci.test.ts`:
  - `una vendita eBay prende i pezzi entrati per primi`: 3 disponibili, `pickForSale(a, parts, 2)` → i due `createdAt` più vecchi, `mancano: 0`.
  - `importa vendita con più pezzi di quelli disponibili`: 1 disponibile, quantità 3 → 1 pezzo, `mancano: 2`.
- [ ] **Step 2:** Run `node --test src/lib/annunci.test.ts`. Expected: FAIL sui due test nuovi.
- [ ] **Step 3: Implement `pickForSale`** con `nextToShip`.
- [ ] **Step 4:** Run `node --test src/lib/annunci.test.ts`. Expected: PASS.
- [ ] **Step 5: Implement the store actions** sopra.
  - `importEbaySale` con `mancano > 0` imposta `daGestire = "mancano N pezzi"`. L'ordine si crea anche con zero pezzi, con `amount = prezzoUnitario × quantita`.
  - `orderFromAnnunci` sceglie il prossimo a partire **nello stesso `set`** che controlla la disponibilità, come `createOrder`.
  - Ogni azione scrive un evento nel registro: "Annuncio creato", "Pezzo aggiunto all'annuncio", "Prezzo dell'annuncio cambiato", "Annuncio ritirato da …", "Annuncio esaurito", "Vendita eBay importata".
  - `agenda.ts`:
    - una voce per gli ordini con `daGestire`;
    - la voce "Porta online" conta i pezzi disponibili senza `annuncioId`, compresi quelli con prezzo diverso o con l'annuncio ritirato.
- [ ] **Step 6:** Run `npx tsc --noEmit -p . && npm test`. Expected: nessun errore, tutti i test passano.
- [ ] **Step 7: Commit** `feat: azioni degli annunci, unione automatica e vendite eBay`

---

### Task 6: Pagina Pubblicazione e scheda ricambio

**Files:**
- Modify: `src/app/(app)/pubblicazione/view.tsx`
- Create: `src/components/AnnuncioPreview.tsx`
- Modify: `src/app/(app)/ricambi/[id]/view.tsx`

**Interfaces:**
- Consumes: azioni del Task 5; `generateText`, `aspectsFor`, `gpsrFor`, `compatVehicles` (Task 3); `onlinePrice`, `ONLINE_FEE_PCT`.

- [ ] **Step 1: Coda.** Elenca i pezzi `bozza` o `disponibile` senza `annuncioId`, con i controlli di oggi.
  - Per "prezzo diverso" mostra "Prezzo diverso dall'annuncio A-…: 95 € contro 90 €" con i pulsanti "Tieni 90 €" e "Usa 95 € per tutti", che chiamano `resolvePrice`.
  - Per "annuncio ritirato" mostra il pulsante "Ripubblica l'annuncio A-…".
  - "Pubblica" apre `AnnuncioPreview`.
  - Il pulsante in alto "Pubblica i N pronti" pubblica con testo generato e canali di serie.
- [ ] **Step 2: `AnnuncioPreview`.** Contiene:
  - titolo con il contatore dei caratteri (massimo 80) e descrizione, modificabili, più il pulsante "Riscrivi in automatico";
  - categoria (le parole di `EBAY_CATEGORY_QUERY`, o il nome dato da eBay se c'è) e caratteristiche, con quelle mancanti evidenziate;
  - veicoli compatibili, con quelli non riconosciuti da eBay evidenziati (dagli `avvisi`);
  - foto del prossimo a partire;
  - "Prezzo 90 € · online 97,20 € (+8%)";
  - GPSR: se "da confermare", la casella "Pezzo messo in commercio prima del 13/12/2024" oppure i campi del produttore;
  - le caselle Negozio ed eBay (eBay selezionata se il collegamento è attivo), poi "Pubblica".
- [ ] **Step 3: Elenco annunci** (pannello sotto la coda), per ogni annuncio:
  - codice, titolo, quantità;
  - chip negozio (online, esaurito, ritirato) e chip eBay (stato, link "Vedi su eBay", "da riallineare", errore in rosso);
  - azioni: modifica testo, ritira (negozio, eBay, tutti), ripubblica, e "Simula vendita su eBay" quando il modo è Simulato (la collega il Task 9).
- [ ] **Step 4: Scheda ricambio.**
  - Riga "Annuncio A-000123 · 3 disponibili · negozio online · eBay online", con i link a Pubblicazione e a eBay.
  - Salvando un prezzo su un pezzo che ha `annuncioId` e quantità maggiore di 1, la scheda chiede prima "Cambia il prezzo di tutti e N i pezzi dell'annuncio A-…" e poi chiama `setAnnuncioPrice`.
  - Il pulsante "Pubblica/Ritira" della scheda (riga 291) porta alla Pubblicazione o ritira l'annuncio.
- [ ] **Step 5: Verifica nel browser.**
  - Due pezzi uguali (stesso tipo, codice verificato, lato, condizione, spedibilità e prezzo) diventano un annuncio con quantità 2.
  - Un terzo con prezzo diverso compare in coda con l'avviso.
  - Nessun errore in console.
- [ ] **Step 6: Commit** `feat: anteprima e pubblicazione degli annunci`

---

### Task 7: Negozio online per annunci

**Files:**
- Modify: `src/lib/config.ts` (`BRAND.telefono`, valore dimostrativo)
- Modify: `src/lib/cart.ts` (`ids` diventano codici annuncio)
- Modify: `src/app/negozio/view.tsx`
- Modify: `src/app/negozio/[id]/view.tsx`
- Modify: `src/app/negozio/carrello/view.tsx`

**Interfaces:**
- Consumes: `quantityOf`, `nextToShip`, `orderFromAnnunci`, `onlinePrice`.

- [ ] **Step 1: Elenco.** Mostra gli annunci con `negozio.stato === "online"` e quantità maggiore di 0, con "N disponibili" quando sono più di 1. In fondo la sezione "Esauriti" con gli annunci `esaurito`. Foto e testi vengono dal prossimo a partire o, se esaurito, dall'ultimo pezzo dell'annuncio.
- [ ] **Step 2: Pagina dell'annuncio.** `/negozio/A-…` mostra titolo, descrizione, foto, prezzo con `onlinePrice`, quantità e spedizione con `isShippable`. Se esaurito: "Esaurito: chiamaci per questo pezzo o per altri dello stesso veicolo", il telefono e il modulo "Avvisami quando torna", che risponde solo "Ti avviseremo" (simulato). `/negozio/R-…` porta all'annuncio del pezzo con `router.replace`, oppure dice "Non disponibile".
- [ ] **Step 3: Carrello e ordine** con codici annuncio, `orderFromAnnunci("negozio", …)`, una sola unità per annuncio. Il messaggio di conflitto resta come oggi.
- [ ] **Step 4: Verifica nel browser.** Un annuncio da 2 pezzi a 95 € si vede a 102,60 € con "2 disponibili". Un ordine ne riserva uno e la pagina passa a "1 disponibile". Vendendo l'ultimo, l'annuncio finisce tra gli Esauriti con il telefono.
- [ ] **Step 5: Commit** `feat: negozio online per annunci con esauriti`

---

### Task 8: Ponte eBay, contratto, modo simulato e Collegamenti

**Files:**
- Create: `src/lib/ebay/richiesta.ts`
- Create: `src/lib/ebay/richiesta.test.ts`
- Create: `src/lib/ebay/simulato.ts`
- Create: `src/lib/ebay/simulato.test.ts`
- Create: `src/lib/ebay/server.ts` (sceglie il ponte, legge le credenziali)
- Create: `src/app/api/ebay/allinea/route.ts`, `src/app/api/ebay/vendite/route.ts`, `src/app/api/ebay/stato/route.ts`
- Create: `src/app/ebay-simulato/[id]/page.tsx`, `src/app/ebay-simulato/[id]/view.tsx`
- Modify: `src/lib/collegamenti.ts` (voce `ebay` in `SERVIZI`, gruppo `"consumo"`)
- Modify: `src/app/api/collegamenti/route.ts` (esportare `leggiValori(id: string): Promise<Record<string, string | string[]>>` con i segreti decifrati, solo per il server)

**Interfaces:**
- Consumes (`contratto.ts`, creato nel Task 5):

```ts
export type ModoEbay = "Simulato" | "Sandbox";
export type SpedizioneEbay = "corriere" | "voluminoso" | "ritiro";
export interface RichiestaAllinea {
  sku: string; attivo: boolean; quantita: number; prezzo: number;
  titolo: string; descrizione: string; categoriaQuery: string; categoriaId?: string;
  condizione: Condition; caratteristiche: Record<string, string>; foto: string[];
  compatibilita: VeicoloCompat[]; spedizione: SpedizioneEbay; gpsr: Gpsr;
}
export interface EsitoAllinea { stato: StatoEbay; listingId?: string; url?: string; categoria?: { id: string; nome: string }; avvisi: string[]; errore?: string }
export interface VenditaEbay { orderId: string; sku: string; quantita: number; prezzoUnitario: number; acquirente: string; at: string }
export interface StatoPonte { modo: ModoEbay; collegato: boolean; esauritoAttivo?: boolean; politiche?: Record<"pagamento" | "reso" | SpedizioneEbay, { id: string; nome: string } | undefined>; errore?: string }
export interface Ponte { allinea(r: RichiestaAllinea): Promise<EsitoAllinea>; vendite(da: string): Promise<VenditaEbay[]>; stato(): Promise<StatoPonte> }
```

- Produces:
  - `richiestaPer(a: Annuncio, parts: Part[], typeShippable: boolean): RichiestaAllinea` (pura):
    - `prezzo = onlinePrice(a.price)`;
    - `attivo = a.ebay?.stato !== "ritirato"`;
    - foto = quelle di `nextToShip`, oppure dell'ultimo pezzo se a zero;
    - `categoriaId = a.ebay?.categoria?.id`.
  - `creaPonteSimulato(): Ponte`.
  - Route:
    - `POST /api/ebay/allinea` (body `RichiestaAllinea` → `EsitoAllinea`);
    - `GET /api/ebay/vendite?da=<iso>` → `{ vendite: VenditaEbay[] }`;
    - `GET /api/ebay/stato` → `StatoPonte`.
  - Voce di Collegamenti `ebay`, campi:
    - `ambiente`: scelta `["Simulato", "Sandbox"]`;
    - `appId`: testo, "App ID (Client ID)";
    - `certId`: segreto, "Cert ID (Client Secret)";
    - `ruName`: testo, "RuName (nome dell'indirizzo di ritorno)", facoltativo per Simulato.
  - `server.ts`: Sandbox solo se `ambiente === "Sandbox"` e ci sono App ID, Cert ID e RuName; altrimenti `creaPonteSimulato()`.

- [ ] **Step 1: Write the failing tests:**
  - `richiesta.test.ts`:
    - `prezzo online con l'8%`: annuncio con `price: 95` → `prezzo: 102.6`.
    - `a zero pezzi la richiesta resta attiva con quantità 0`.
    - `annuncio ritirato su eBay → attivo false`.
    - `spedizione`: porta spedibile → `"voluminoso"`; porta non spedibile → `"ritiro"`; alternatore → `"corriere"`.
  - `simulato.test.ts`:
    - `pubblica con numero e link finti`: `allinea` con quantità 2 → `stato: "online"`, `listingId: "SIM-A-000001"`, `url: "/ebay-simulato/A-000001"`.
    - `quantità 0 → esaurito`; `attivo false → ritirato`.
    - `prezzo che finisce in ,13 dà errore simulato`: `prezzo: 102.13` → `stato: "errore"` e un `errore` non vuoto.
    - `vendite` restituisce `[]`.
- [ ] **Step 2:** Run `node --test src/lib/ebay/richiesta.test.ts src/lib/ebay/simulato.test.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** `richiesta.ts` e `simulato.ts` (con una breve attesa simulata).
- [ ] **Step 4:** Run gli stessi test. Expected: PASS.
- [ ] **Step 5: Route, `server.ts` e `leggiValori`.** Leggere prima la guida delle route. Le route rispondono `no-store` e rifiutano le richieste da altri siti. La validazione di `RichiestaAllinea` accetta solo i campi del contratto, con tipi giusti, e risponde 400 altrimenti.
- [ ] **Step 6: Voce eBay in Collegamenti** con la nota "Simulato finché non scegli Sandbox e inserisci le chiavi del Developers Program". Pagina `/ebay-simulato/[id]` (client, legge l'annuncio dallo store): titolo, foto, prezzo online, "Quantità disponibile: N", o "Esaurito: nascosto dalle ricerche di eBay" a zero; in alto il banner "Annuncio eBay simulato".
- [ ] **Step 7:** Run `npx tsc --noEmit -p . && npm test`, poi `curl -s -X POST localhost:3210/api/ebay/allinea -H 'content-type: application/json' -d '{}'`. Expected: 400.
- [ ] **Step 8: Commit** `feat: ponte eBay simulato e voce in Collegamenti`

---

### Task 9: Riallineamento e vendite eBay nell'app

**Files:**
- Create: `src/lib/ebay-sync.ts` (client)
- Create: `src/lib/ebay-sync.test.ts`
- Modify: `src/components/AppShell.tsx` (monta l'esecutore)
- Modify: `src/app/(app)/pubblicazione/view.tsx` ("Simula vendita su eBay", "Controlla vendite eBay", indicatore "N da riallineare")
- Modify: `src/app/(app)/vendite/view.tsx` (canale "eBay", numero d'ordine eBay, "da gestire" in evidenza)

**Interfaces:**
- Consumes: `richiestaPer`, `RichiestaAllinea`, `EsitoAllinea`, `VenditaEbay` (Task 8); `importEbaySale` (Task 5).
- Modify: `src/lib/store.ts` (azione `setEbayResult`)
- Produces:
  - azione dello store `setEbayResult(annuncioId: string, esito: EsitoAllinea, inviato: { quantita: number; prezzo: number }): void`, che usa `applyEsito` e registra nel registro attività "Pubblicato su eBay", "Errore eBay" o "Ritirato da eBay";
  - `nextToSync(annunci: Annuncio[]): Annuncio | undefined` (pura): il primo con `ebay?.daRiallineare`, cominciando dai non in errore.
  - `applyEsito(a: Annuncio, esito: EsitoAllinea, inviato: { quantita: number; prezzo: number }, at: string): AnnuncioEbay` (pura):
    - in errore `daRiallineare` resta `true` e l'errore si salva;
    - altrimenti `daRiallineare: false` e si azzera l'errore.
  - `useEbaySync(): void`. Un giro alla volta: subito quando un annuncio diventa da riallineare, all'avvio e ogni 60 s finché ne restano. Le vendite si controllano ogni 5 minuti solo se `/api/ebay/stato` dice Sandbox e collegato.
  - `simulateEbaySale(annuncioId: string, quantita: number): Result<string>`: costruisce una `VenditaEbay` finta (`orderId: "SIM-ORD-…"`) e chiama `importEbaySale`.

- [ ] **Step 1: Write the failing tests:**
  - `sceglie prima gli annunci senza errore`.
  - `dopo un errore l'annuncio resta da riallineare`: `applyEsito` con `stato: "errore"` → `daRiallineare: true`, `errore` salvato.
  - `esito buono azzera errore e segno`, e salva `quantitaInviata` e `prezzoInviato`.
- [ ] **Step 2:** Run `node --test src/lib/ebay-sync.test.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** `nextToSync` e `applyEsito`, poi l'azione `setEbayResult`.
- [ ] **Step 4:** Run `node --test src/lib/ebay-sync.test.ts`. Expected: PASS.
- [ ] **Step 5: Implement `useEbaySync` e i pulsanti.** Il primo esito positivo su un annuncio in "in pubblicazione" lo porta a "online" (o "esaurito"). "Simula vendita su eBay" chiede la quantità (1 di serie, massimo la quantità disponibile + 1, per provare il caso "da gestire").
- [ ] **Step 6: Verifica nel browser** in modo Simulato:
  1. un annuncio da 2 pezzi pubblicato anche su eBay → "eBay online", link alla pagina simulata con "Quantità disponibile: 2";
  2. vendita al banco di un pezzo → la pagina simulata dice 1;
  3. "Simula vendita su eBay" con 1 → il pezzo giusto (il più vecchio) è venduto, l'annuncio diventa esaurito su eBay e sul negozio;
  4. nuovo pezzo uguale messo disponibile → torna online con quantità 1;
  5. prezzo 90,86 €, che con l'8% fa 98,13 € → "errore" in rosso e "da riallineare", poi correggendo il prezzo l'errore sparisce.
- [ ] **Step 7: Commit** `feat: riallineamento e vendite eBay`

---

### Task 10: Ponte sandbox (API vere di eBay, ambiente di prova)

**Files:**
- Create: `src/lib/ebay/archivio.ts` (file `ebay.json` nella cartella dati: token cifrati, ultimo controllo vendite, URL foto caricate, categorie trovate, politiche scelte, esaurito attivo)
- Create: `src/lib/ebay/sandbox.ts`
- Create: `src/lib/ebay/sandbox.test.ts` (solo per i costruttori di payload, puri)
- Create: `src/app/api/ebay/collega/route.ts`, `src/app/api/ebay/ritorno/route.ts`, `src/app/api/ebay/politiche/route.ts`
- Modify: `src/lib/ebay/server.ts`
- Modify: `src/app/(app)/impostazioni/collegamenti/view.tsx` (sotto la voce eBay: "Collega account eBay", stato del collegamento, scelta delle 5 politiche e del magazzino, stato "esaurito")

**Interfaces:**
- Consumes: `Ponte`, `RichiestaAllinea`, `EsitoAllinea`, `VenditaEbay`, `StatoPonte` (Task 8); `cifra`/`decifra`; `leggiValori("ebay")`.
- Produces:
  - `creaPonteSandbox(cred: { appId: string; certId: string; ruName: string }): Ponte`;
  - costruttori puri:
    - `inventoryItemBody(r: RichiestaAllinea, fotoEps: string[]): object`;
    - `offerBody(r: RichiestaAllinea, categoriaId: string, politiche: { pagamento: string; reso: string; spedizione: string }, location: string): object`;
    - `compatibilityBody(r: RichiestaAllinea): object`;
    - `conditionFor(c: Condition): string`.
- Costanti sandbox:
  - API `https://api.sandbox.ebay.com`;
  - Media `https://apim.sandbox.ebay.com/commerce/media/v1_beta`;
  - consenso `https://auth.sandbox.ebay.com/oauth2/authorize`;
  - token `https://api.sandbox.ebay.com/identity/v1/oauth2/token`;
  - Trading `https://api.sandbox.ebay.com/ws/api.dll` con `X-EBAY-API-SITEID: 101`.
- Scope utente: `https://api.ebay.com/oauth/api_scope`, `…/sell.inventory`, `…/sell.account`, `…/sell.fulfillment`. Taxonomy con token applicazione (client credentials, scope `https://api.ebay.com/oauth/api_scope`).

- [ ] **Step 1: Write the failing tests** in `sandbox.test.ts`:
  - `offerta a prezzo fisso, eBay Italia, senza scadenza`: `offerBody(...)` ha:
    - `format: "FIXED_PRICE"`, `marketplaceId: "EBAY_IT"`, `listingDuration: "GTC"`;
    - `pricingSummary.price` = `{ value: "102.60", currency: "EUR" }`;
    - `availableQuantity` = `r.quantita`;
    - `listingPolicies.fulfillmentPolicyId` uguale alla politica passata;
    - `merchantLocationKey`.
  - `quantità zero resta nell'articolo`: `inventoryItemBody` con `quantita: 0` → `availability.shipToLocationAvailability.quantity === 0`.
  - `condizioni`: A, B e C → `"USED_EXCELLENT"`; D → `"FOR_PARTS_OR_NOT_WORKING"`. La lettera e la spiegazione vanno in `conditionDescription`.
  - `GPSR esente senza produttore`, mentre con `tipo: "produttore"` c'è `product.regulatory.manufacturer.companyName`.
  - `compatibilità per proprietà`: ogni veicolo diventa `compatibilityProperties` con `make`, `model`, `year` (e `engine` se c'è); con `anni: "2009–2012"` diventa un veicolo per ogni anno.
- [ ] **Step 2:** Run `node --test src/lib/ebay/sandbox.test.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** i costruttori. Verificare nella documentazione eBay la forma esatta dei campi; quella dei test è vincolante.
- [ ] **Step 4:** Run `node --test src/lib/ebay/sandbox.test.ts`. Expected: PASS.
- [ ] **Step 5: OAuth e collegamento.**
  - `GET /api/ebay/collega` reindirizza al consenso eBay con `client_id`, `redirect_uri=<RuName>`, `response_type=code` e gli scope.
  - `GET /api/ebay/ritorno?code=…`, nell'ordine:
    1. scambia il codice e salva i token cifrati con la scadenza;
    2. attiva "esaurito" con `SetUserPreferences` (`OutOfStockControlPreference` true);
    3. legge le politiche (`/sell/account/v1/fulfillment_policy|payment_policy|return_policy?marketplace_id=EBAY_IT`) e i magazzini (`/sell/inventory/v1/location`);
    4. se mancano, li crea con valori di base: "Corriere", "Corriere voluminoso", "Solo ritiro in sede" (ritiro di persona), reso 14 giorni, magazzino "Sede";
    5. riporta a `/impostazioni/collegamenti?ebay=ok`, oppure `?ebay=errore` con il messaggio.
  - Il token si rinnova con il refresh token quando mancano meno di 5 minuti.
  - `PUT /api/ebay/politiche` salva le scelte.
- [ ] **Step 6: `allinea` in sandbox**, nell'ordine:
  1. categoria: `categoriaId` se c'è, altrimenti `getCategorySuggestions` (albero 101) con `categoriaQuery`, salvata in archivio per quella query;
  2. caratteristiche obbligatorie da `getItemAspectsForCategory`: quelle mancanti diventano `avvisi`;
  3. foto caricate con `createImageFromFile` una volta per file (dalla cartella foto o da `public/`);
  4. `PUT inventory_item/{sku}`;
  5. compatibilità tradotta con `getCompatibilityPropertyValues`: i veicoli non trovati diventano `avvisi`, poi `PUT product_compatibility`;
  6. offerta trovata con `GET offer?sku=`, creata o aggiornata;
  7. `publishOffer` se non pubblicata, oppure se l'annuncio risulta chiuso;
  8. `withdrawOffer` se `attivo` è falso.
  - **Annuncio chiuso da eBay** (circa 90 giorni a zero): se l'offerta risulta non più pubblicata ma l'annuncio non è stato ritirato da noi, con quantità 0 il ponte restituisce `"chiuso da eBay"` senza ripubblicare; con quantità maggiore di 0 ripubblica.

  Stato restituito: online, esaurito, ritirato o errore, con il link `https://www.sandbox.ebay.it/itm/<listingId>`. Gli errori di eBay si traducono in frasi semplici: messaggio di eBay + "cosa fare".
- [ ] **Step 7: `vendite(da)`** con `GET /sell/fulfillment/v1/order?filter=creationdate:[da..]`. Una `VenditaEbay` per ogni riga d'ordine con SKU che inizia con `A-`. Salva l'ultimo controllo.
- [ ] **Step 8:** Run `npx tsc --noEmit -p . && npm test`. Expected: nessun errore, tutti i test passano. Senza chiavi sandbox il gestionale resta in Simulato: ripetere velocemente il punto 1 della verifica del Task 9.
- [ ] **Step 9: Commit** `feat: ponte eBay sandbox con OAuth, politiche e vendite`

---

### Task 11: Verifica finale

- [ ] **Step 1:** Run `npx tsc --noEmit -p . && npm test && npx eslint src`. Expected: nessun errore.
- [ ] **Step 2:** In Simulato, ripetere per intero le verifiche dei Task 6, 7 e 9 dopo "Ripristina dati demo", e fare uno screenshot di Pubblicazione con un annuncio da 2 pezzi online su negozio ed eBay.
- [ ] **Step 3:** Aggiornare `docs/INTEGRAZIONI.md`, sezione eBay: cosa è costruito, e come Alessandro fa la prova in sandbox (crea l'account sviluppatore, crea le chiavi Sandbox, imposta l'indirizzo di ritorno sul tunnel, inserisce i dati in Collegamenti, tocca "Collega account eBay").
- [ ] **Step 4: Commit** `docs: istruzioni per la prova eBay in sandbox`
