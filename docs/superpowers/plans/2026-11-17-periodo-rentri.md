# Periodo RENTRI, formulari ricevuti e accesso consulente — piano

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** sostituire Ecomatico: registro rifiuti completo generato dagli eventi, formulari ricevuti dalla ditta che ritira, chiusura mensile del periodo con controlli e trasmissione (simulata) da parte della consulente.

**Architecture:** la logica dei periodi e dei controlli è un modulo puro (`src/lib/periodo.ts`, senza import a runtime) testato con `node --test`. Lo store Zustand ottiene i campi nuovi dei movimenti, un'anagrafica soggetti e le azioni per completare le bozze, rettificare, annullare e trasmettere; il periodo trasmesso si ricava dai movimenti (nessuna collezione nuova per i periodi). Le pagine sono client component come il resto dell'app.

**Tech Stack:** Next.js 16.4.6 (App Router, `page.tsx` + `view.tsx`), TypeScript, Zustand persist + sync `/api/demo-state`, Tailwind v4, `node --test` (Node 26, type stripping).

**Spec:** `docs/superpowers/specs/2026-11-17-periodo-rentri-design.md`

## Global Constraints
- Periodo = mese di calendario, ora locale (Europe/Rome sul dispositivo).
- Scadenza trasmissione = fine del mese successivo (23:59:59.999 dell'ultimo giorno).
- Numerazione del registro per anno solare, progressiva.
- Una registrazione numerata non si modifica mai (manuale RENTRI §3.2.1): si corregge solo con una registrazione nuova di **rettifica** (`rettificaDi`) o **annullamento** (`annullaDi`).
- Bozza = registrazione a cui manca un dato obbligatorio: nessun numero; scadenza 2 giorni lavorativi (lun–ven) dall'operazione.
- Causali: `"*T"` carico ricevuto da terzi, `"NP"` carico nuovo produttore, `"I"` scarico interno, `"aT"` scarico a terzi, più `"RETT"` e `"ANN"` interne al gestionale.
- Carico veicolo: `vfu: true` con `certificato: { numero, data }` dalla pratica (`dossier.number`, `presaInCarico.at`).
- Trasmissione RENTRI **simulata**; testo in UI: "trasmissione simulata".
- Formato numero formulario `AAAAA 00000 AA` solo come avviso, mai bloccante.
- Copy dell'interfaccia in italiano semplice, senza gergo tecnico; nomi dati demo con "Demo" (niente dati reali del cliente dalle foto).
- `STORE_SCHEMA` passa a `gestionale-demolizione-demo-v11` (la forma dei movimenti cambia).
- Sync: `soggetti` si aggiunge alle collezioni WHOLE in `src/lib/sync.ts` e `src/app/api/demo-state/route.ts`.

## Review Focus
1. Movimento alle 23:30 del 31 ottobre (ora italiana, 22:30 UTC) → appartiene a ottobre, non a novembre. Test in Task 1.
2. Tentare di modificare una registrazione numerata → impossibile; si offre solo Rettifica/Annulla. Una bozza completata il venerdì sera ha scadenza martedì. Test `isDraft`, `workingDaysAfter` in Task 1.
3. "Trasmetti" sul mese corrente, su un mese vuoto o con bozze aperte → non permesso. Test `canTransmit` in Task 1.
4. Peso scritto come `0`, `-5`, `abc`, `1.234,5` → solo numeri > 0 accettati (`1.234,5` = 1234.5). Test `parseKg` in Task 1.
5. Dicembre → scadenza 31 gennaio dell'anno dopo. Test `deadlineOf` in Task 1.

---

### Task 1: logica pura dei periodi e dei controlli

**Files:**
- Create: `src/lib/periodo.ts`, `src/lib/periodo.test.ts`
- Modify: `package.json` (script `"test": "node --test src/lib/*.test.ts"`), `tsconfig.json` (`"exclude": ["node_modules", "**/*.test.ts"]`)

**Interfaces:**
- Consumes: `import type { WasteMove, Fir } from "./types"` (solo tipi: il file non importa nulla a runtime).
- Produces:
  - `monthKey(iso: string): string` → `"2026-10"` (ora locale)
  - `monthLabel(key: string): string` → `"ottobre 2026"`
  - `deadlineOf(key: string): string` (ISO)
  - `parseKg(raw: string): number | null`
  - `isDraft(m: WasteMove): boolean` (`numero === undefined`)
  - `missingFields(m: WasteMove): ("cf-produttore" | "certificato" | "peso")[]` — per `*T` con `vfu`: cf del produttore, `certificato.numero`, `pesoPesa === true`; per gli altri: solo kg > 0
  - `workingDaysAfter(iso: string, n: number): string` (fine del giorno lavorativo n-esimo, lun–ven)
  - `type IssueCode = "bozza" | "esito-mancante" | "respinto" | "kg-diversi" | "fir-formato" | "oltre-limite"`
  - `interface Issue { code: IssueCode; text: string; blocking: boolean }` (solo `bozza` è bloccante)
  - `moveIssues(m: WasteMove, fir?: Fir): Issue[]`
  - `firNumberLooksValid(n: string): boolean` (`/^[A-Z]{5}\s?\d{5}\s?[A-Z]{2}$/`)
  - `type PeriodStatus = "aperto" | "da trasmettere" | "trasmesso"`
  - `interface Period { key: string; label: string; deadline: string; status: PeriodStatus; moves: WasteMove[]; drafts: number; warnings: number; ricevuta?: string }`
  - `periodsOf(moves: WasteMove[], firs: Fir[], now?: Date): Period[]` (in ordine dal più vecchio; il mese di una registrazione è quello di `registeredAt`, per le bozze quello di `at`)
  - `canTransmit(p: Period): boolean` (`da trasmettere`, almeno una registrazione, nessuna bozza)
  - `monthStock(moves: WasteMove[], key: string, limits: { code: string; limitKg: number }[]): { code: string; carichi: number; scarichi: number; giacenza: number; limitKg: number; over: boolean }[]` (solo registrazioni numerate; rettifiche e annullamenti applicati)
  - `nextRegisterNumber(moves: WasteMove[], atIso: string): number`

- [ ] **Step 1: test che falliscono** in `src/lib/periodo.test.ts` (`node:test`, `node:assert/strict`, `import { … } from "./periodo.ts"`):
  - `monthKey("2026-10-31T22:30:00Z")` === `"2026-10"` (con `process.env.TZ = "Europe/Rome"` in testa al file); `monthKey("2026-11-01T00:30:00+01:00")` === `"2026-11"`
  - `deadlineOf("2026-10")` inizia con `"2026-11-30"` in ora locale (`new Date(d).getDate() === 30`, mese 10); `deadlineOf("2026-12")` → 31 gennaio 2027
  - `parseKg("0")`, `parseKg("-5")`, `parseKg("abc")`, `parseKg("")` === `null`; `parseKg("1.234,5")` === `1234.5`; `parseKg("38,5")` === `38.5`; `parseKg("5000")` === `5000`
  - `missingFields`: `*T` vfu senza `produttore.cf` → contiene `"cf-produttore"`; senza `certificato` → `"certificato"`; con `pesoPesa: false` → `"peso"`; `NP` con kg 12 → `[]`
  - `workingDaysAfter("2026-11-13T18:00:00+01:00", 2)` (venerdì) → martedì 17 novembre; da lunedì → mercoledì
  - `moveIssues`: bozza → `"bozza"` bloccante; scarico `aT` con fir senza `esito` → `"esito-mancante"` non bloccante; fir `esito: "respinto"` → `"respinto"`; `kgAccettati` 4850 su 5000 → `"kg-diversi"`; numero `"F-000012"` → `"fir-formato"`; `"JNMPC 00262 JC"` → nessun `fir-formato`; scarico `I` → nessun problema
  - `periodsOf` con movimenti di settembre (tutti trasmessi), ottobre (uno da trasmettere) e del mese di `now` → stati `trasmesso`, `da trasmettere`, `aperto`
  - `canTransmit`: falso per `aperto`; falso con una bozza del mese; vero senza bozze; falso per periodo senza registrazioni
  - `monthStock`: carico 1000, rettifica a 950 (`RETT` che richiama il carico), annullamento di un altro carico → giacenza 950
  - `nextRegisterNumber`: con numeri 1..3 nel 2026 e 9 nel 2025 → per una data 2026 restituisce 4; per il 2027 restituisce 1
- [ ] **Step 2:** `npm test` → FAIL (modulo mancante).
- [ ] **Step 3:** implementa `src/lib/periodo.ts` con le firme sopra. Mese con `getFullYear()/getMonth()` locali. `parseKg`: togli i punti delle migliaia, virgola → punto, `Number`, accetta solo finito > 0.
- [ ] **Step 4:** `npm test` → PASS; `npx tsc --noEmit` pulito.
- [ ] **Step 5:** commit `Periodo RENTRI: logica pura dei periodi e dei controlli, con test`.

### Task 2: modello dati, anagrafica soggetti, movimenti completi, dati demo

**Files:**
- Modify: `src/lib/types.ts`, `src/lib/ambiente.ts`, `src/lib/store.ts` (state, `addMoves`, `STORE_SCHEMA`), `src/lib/seed.ts`, `src/lib/sync.ts`, `src/app/api/demo-state/route.ts`

**Interfaces:**
- Produces in `types.ts`:
  - `type Causale = "*T" | "NP" | "I" | "aT" | "RETT" | "ANN"`
  - `type RuoloSoggetto = "impianto" | "destinatario" | "trasportatore" | "intermediario"`
  - `interface Soggetto { id: string; ruolo: RuoloSoggetto; nome: string; cf: string; sede?: string; autorizzazione?: string; albo?: string; operazione?: string }`
  - `WasteMove` aggiunge (tutti facoltativi): `numero, registeredAt, by, causale, statoFisico ("S"|"SP"|"L"|"FP"|"VS"), hp: string[], operazione, vfu: boolean, certificato: { numero: string; data: string }, produttore: { nome: string; cf?: string }, pesoPesa: boolean, caricoRif (id del carico per lo scarico I), fir (id del Fir), rettificaDi, annullaDi, motivo, rentriRicevuta`
  - `Fir` diventa formulario **ricevuto**: aggiunge `numero: string` (es. "JNMPC 00262 JC"), `emessoAt`, `destinatarioId`, `trasportatoreId`, `intermediarioId?`, `targa?`, `conducente?`, `inizioTrasportoAt?`, `rinfusa: boolean`, `annotazioni?`, `esito?: "accettato" | "parziale" | "respinto"`, `kgAccettati?`, `arrivoAt?`. Stati: `"da firmare" | "firmato" | "accettato"` (tolto "trasmesso": lo trasmette chi lo emette).
- Produces in `ambiente.ts`: `Eer` aggiunge `stato` e `hp`; `movesForIntake(v, at)` → `causale "*T"`, `vfu: true`, `certificato` dalla pratica se c'è, `statoFisico "S"`, `hp ["HP14"]`, `operazione "R13"`, `produttore` = `v.conferente` (`nome`, `cf`), `pesoPesa: false`; `movesForBonifica` → scarico `causale "I"` con `caricoRif` al carico del veicolo, carichi `causale "NP"`, stato/hp dal codice. In store, `addMoves` numera solo ciò che non ha `missingFields` (il resto resta bozza).
- Produces in store: `soggetti: Soggetto[]` nello state; `addMoves` assegna `numero = nextRegisterNumber(...)`, `registeredAt`, `by` alle registrazioni complete (Task 1).

- [ ] **Step 1:** tipi e tabella EER (stato fisico e HP per ogni codice: liquidi "L", 16 01 04* `HP14`, batterie `HP8`, ecc.; per i dubbi lascia `hp: []` con commento "da confermare con la consulente").
- [ ] **Step 2:** generazione movimenti dagli eventi come sopra; firma del formulario (Task 3) userà `causale "scarico"` e `fir`.
- [ ] **Step 3:** dati demo: soggetti `Autodemolizione Demo` (impianto, aut. art. 208 "DD 000-00000/2019 (demo)"), `Centro Recuperi Demo S.r.l.` (destinatario R13 e trasportatore, Albo "TO/000000"), `Metalli Demo S.p.A.` (intermediario). Registrazioni: tutto ciò che è prima di ottobre `trasmesso` con ricevuta; ottobre `da trasmettere` con 1 bozza (conferente senza codice fiscale), 1 formulario firmato senza esito e 1 con esito parziale; novembre aperto con 1 bozza di oggi (peso della pesa da inserire). Due formulari di ottobre con numeri nel formato `AAAAA 00000 AA`. `STORE_SCHEMA` → v11.
- [ ] **Step 4:** `soggetti` in WHOLE (sync client e route).
- [ ] **Step 5:** `npx tsc --noEmit`, `npx eslint src`, `npm test` puliti. Verifica in browser (`/ambiente`): giacenze uguali a prima per codice.
- [ ] **Step 6:** commit `Registro rifiuti: movimenti completi, anagrafica soggetti, formulari ricevuti (modello e dati demo)`.

### Task 3: azioni dello store

**Files:** Modify `src/lib/store.ts`

**Interfaces:**
- Consumes: `isDraft`, `missingFields`, `moveIssues`, `periodsOf`, `canTransmit`, `nextRegisterNumber`, `parseKg` (Task 1).
- Produces (tutte registrano un evento di audit):
  - `completeDraft(id: string, patch: { produttoreCf?: string; certificato?: { numero: string; data: string }; kg?: number; pesoPesa?: boolean }): Result` — solo bozze; quando `missingFields` è vuoto assegna `numero`, `registeredAt` (ora), `by`.
  - `transmitPeriod(key: string): Result<string>` — solo se `canTransmit`; segna `trasmesso`, `rentriAt`, `rentriRicevuta` (`RENTRI-SIM-<key>-<6 caratteri>`).
  - `rectifyMove(id: string, nuoviKg: number, motivo: string): Result<string>` — registrazione nuova `causale "RETT"`, `rettificaDi`, kg corretti, data di oggi.
  - `cancelMove(id: string, motivo: string): Result<string>` — registrazione nuova `causale "ANN"`, `annullaDi`.
  - `receiveFir(f: { numero; emessoAt; eer; kg; destinatarioId; trasportatoreId; intermediarioId?; targa?; conducente?; inizioTrasportoAt?; rinfusa; annotazioni? }): string` — stato `da firmare`.
  - `signFir(id: string): Result` — `firmato` + scarico nel registro (`causale "aT"`, `fir: id`, `operazione` del destinatario, kg del formulario), numerato subito.
  - `setFirOutcome(id: string, esito: "accettato" | "parziale" | "respinto", kgAccettati: number, arrivoAt: string): Result` — stato `accettato`.
  - `saveSoggetto(s: Soggetto): void`
  - Rimossi: `transmitRentri`, `createFir`, `advanceFir` (sostituiti).
- [ ] **Step 1:** implementa le azioni; aggiorna i chiamanti esistenti (`/ambiente`, `/ambiente/formulari`) quanto basta per compilare (UI completa nei Task 5–6).
- [ ] **Step 2:** `npx tsc --noEmit`, `npx eslint src`, `npm test`.
- [ ] **Step 3:** commit `Registro rifiuti: bozze, trasmissione del periodo, rettifiche e annullamenti, formulari ricevuti`.

### Task 4: ruolo Consulente ambientale

**Files:** Modify `src/lib/types.ts` (`Role` + `"consulente"`), `src/lib/store.ts` (`ROLE_USER.consulente = { user: "Laura (consulente ambientale)", device: "PC studio", label: "Consulente ambientale" }`), `src/components/AppShell.tsx` (area Ambiente: `consulente` su Registro, Periodo, Formulari, Soggetti; `MOBILE_TABS.consulente`), `src/app/(app)/view.tsx` (`PRIMARY.consulente = { href: "/ambiente/periodo", label: "Periodo da trasmettere" }`, statistiche: movimenti del mese, problemi aperti, prossima scadenza).
- [ ] **Step 1:** aggiungi il ruolo; il compilatore indica ogni `Record<Role, …>` da completare.
- [ ] **Step 2:** `npx tsc --noEmit`; in browser, scegliendo "Consulente ambientale" si vedono solo Oggi e Ambiente.
- [ ] **Step 3:** commit `Ruolo consulente ambientale`.

### Task 5: pagina "Periodo da trasmettere"

**Files:** Create `src/app/(app)/ambiente/periodo/page.tsx` (come gli altri: `export const instant = false; export { default } from "./view";`), `src/app/(app)/ambiente/periodo/view.tsx`

**Interfaces:** Consumes `periodsOf`, `monthStock`, `moveIssues`, `canTransmit`, `parseKg`, `monthLabel` (Task 1); `completeDraft`, `transmitPeriod`, `rectifyMove`, `cancelMove` (Task 3); `EER` (limiti).

- [ ] **Step 1:** in alto: scelta del mese (`?mese=YYYY-MM`, di serie il più vecchio "da trasmettere", altrimenti il corrente), stato, scadenza ("entro il 30 novembre", gialla negli ultimi 7 giorni, rossa se passata), contatori bozze/avvisi.
- [ ] **Step 2:** totali per codice (`monthStock`) con "oltre il limite" evidenziato.
- [ ] **Step 3:** elenco registrazioni: n° registro, data, causale, codice, kg, produttore e certificato di rottamazione o formulario, problemi come etichette; bozze: completamento dei dati mancanti (codice fiscale, certificato, peso della pesa con `parseKg`); registrate: "Rettifica" (kg corretti + motivo) e "Annulla" (motivo), mai modifica.
- [ ] **Step 4:** "Trasmetti il periodo al RENTRI" attivo solo con `canTransmit`, mostra la ricevuta; "Scarica riepilogo" (CSV: numero, data registrazione, data operazione, causale, codice, stato, HP, kg, VFU, certificato, produttore, cf, formulario, destinatario, operazione, rettifica/annullamento di).
- [ ] **Step 5:** browser: ottobre demo mostra 1 bozza e 2 avvisi; completare la bozza → numero assegnato; trasmettere → ottobre "trasmesso"; rettifica di un carico di ottobre → registrazione nuova in novembre e giacenza aggiornata; 375 px senza scorrimento orizzontale.
- [ ] **Step 6:** commit `Pagina Periodo da trasmettere`.

### Task 6: formulari ricevuti e anagrafica soggetti

**Files:** Modify `src/app/(app)/ambiente/formulari/view.tsx`; Create `src/app/(app)/ambiente/soggetti/page.tsx`, `src/app/(app)/ambiente/soggetti/view.tsx`; Modify `src/components/AppShell.tsx` (voce "Soggetti").

- [ ] **Step 1:** "Registra formulario ricevuto": numero (avviso se `!firNumberLooksValid`), data di emissione, codice rifiuto, kg (`parseKg`), alla rinfusa, destinatario/trasportatore/intermediario dall'anagrafica (destinatario e trasportatore preselezionati se ce n'è uno solo), targa, conducente, inizio trasporto, annotazioni.
- [ ] **Step 2:** elenco con azioni per stato: "Firma" (→ scarico nel registro), poi "Esito del destinatario" (accettato / in parte / respinto, kg accettati, data di arrivo).
- [ ] **Step 3:** pagina Soggetti: elenco per ruolo, aggiungi/modifica (nome, codice fiscale, sede, autorizzazione, n° Albo, operazione).
- [ ] **Step 4:** browser: formulario nuovo → firma → scarico nel registro col numero del formulario → esito parziale → avviso "kg diversi" nel periodo.
- [ ] **Step 5:** commit `Formulari ricevuti e anagrafica soggetti`.

### Task 7: scadenze in Da fare e pagina Registro

**Files:** Modify `src/lib/agenda.ts` (togli `TERMS.rentri` e la voce dei 2 giorni; per ogni periodo "da trasmettere": titolo `Periodo di ottobre 2026 da trasmettere al RENTRI`, dettaglio `N movimenti · M da sistemare`, `due = deadlineOf(key)`, ruoli `consulente`, `responsabile`, `accettazione`, link `/ambiente/periodo?mese=…`; formulari "da firmare" per `accettazione`/`responsabile`; bozze: "Completa la registrazione di <targa>" con `due = workingDaysAfter(at, 2)` per `accettazione`/`responsabile`), `src/app/(app)/ambiente/view.tsx` (il pulsante "Trasmetti" diventa un link al periodo; colonne n° registro e formulario).
- [ ] **Step 1:** implementa; `npx tsc --noEmit`, `npm test`.
- [ ] **Step 2:** browser: in Oggi, da consulente, compare la voce di ottobre con scadenza 30 novembre.
- [ ] **Step 3:** commit `Scadenza mensile del RENTRI nella coda Da fare`.

### Task 8: verifica finale e messa in linea
- [ ] **Step 1:** `npm test`, `npx tsc --noEmit`, `npx eslint src`, `npx next build` puliti.
- [ ] **Step 2:** percorso completo in browser come consulente e come responsabile (dati demo ripristinati).
- [ ] **Step 3:** il server su :3211 serve la presentazione via tunnel: compilare in una copia (`rsync` + `cp -cR node_modules`), poi sostituire il server con `DATI_DIR` sulla cartella dati del progetto; ricompilare anche nel progetto. Il tunnel non si tocca.
- [ ] **Step 4:** commit e push solo su richiesta dell'utente; mai file di altre sessioni.
