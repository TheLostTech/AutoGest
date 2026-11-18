# Login, ruoli e più aziende: piano di lavoro

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Login vero con Better Auth su una piattaforma con più aziende a dati separati, super admin con ingresso di assistenza, ruoli combinabili, accesso nome+PIN sui dispositivi condivisi, negozio pubblico che non espone più l'archivio.

**Architecture:** Better Auth (plugin `organization`, `admin`, `twoFactor` e un plugin nostro `pinDispositivo`) su SQLite in `DATA_DIR/piattaforma.sqlite`. I dati operativi restano file JSON, uno per azienda in `DATA_DIR/aziende/<id>/`. Un solo controllo sul server (`accessoDaRichiesta`) ricava utente, azienda e ruoli dalla sessione e lo usa ogni API; `proxy.ts` fa solo il rinvio ottimistico alla pagina di accesso.

**Tech Stack:** Next.js 16.4.6 App Router (Turbopack), React 19, Zustand 5, better-auth 1.7.x, better-sqlite3, test con `node --test` (type stripping), Node 26.

**Spec:** `docs/superpowers/specs/2026-11-18-login-ruoli-design.md`

## Global Constraints
- Next 16 non è quello che conosci: prima di scrivere route, `proxy.ts` o `instrumentation.ts` leggi la guida in `node_modules/next/dist/docs/` (es. `01-app/03-api-reference/03-file-conventions/proxy.md`). `middleware.ts` è deprecato: si usa `src/proxy.ts`.
- Mai `pkill`/`killall`: sulla porta 3210 gira il server di Alessandro con i suoi dati. Le prove si fanno su una porta nuova (es. 3240) con `DATI_DIR` puntata a una cartella di prova, controllando prima che la cartella non sia quella vera.
- I moduli testati con `node --test` hanno solo `import type` verso il progetto (i test importano con estensione `.ts`); niente `@/` nei moduli testati.
- L'azienda si ricava **sempre dalla sessione**, mai da un parametro della richiesta. Ogni route API della gestione chiama `accessoDaRichiesta` per prima cosa; `proxy.ts` non basta.
- Testi dell'interfaccia in italiano semplice, nello stile visivo esistente (componenti in `src/components/ui`).
- Ruoli dell'azienda: esattamente `accettazione`, `smontatore`, `magazziniere`, `responsabile`, `vendite`, `consulente` (`Role` in `src/lib/types.ts`); più ruoli per membro salvati separati da virgola.
- Ruolo di piattaforma del super admin: `superadmin`. Codice dal telefono (TOTP) obbligatorio prima di entrare in un'azienda.
- PIN: 4 cifre. 5 errori su un nome → nome bloccato 15 minuti. 20 errori in 15 minuti su un dispositivo → dispositivo bloccato fino a sblocco del responsabile.
- Sessione da PIN: scade dopo 5 minuti senza richieste e comunque dopo 10 ore. Ingresso di assistenza: scade dopo 2 ore.
- Richiesta scritta: PDF, JPEG o PNG, massimo 10 MB, in `aziende/<id>/richieste/`; obbligatoria per creare un utente e per cambiarne i ruoli.
- Cookie `Secure` solo se la richiesta arriva in HTTPS (tunnel), non su `localhost`.
- Azienda del negozio pubblico: variabile `NEGOZIO_AZIENDA` (id dell'azienda); se manca, l'azienda demo.
- Primo super admin dalle variabili `SUPERADMIN_EMAIL`, `SUPERADMIN_PASSWORD`, `SUPERADMIN_NOME`; la password non va mai nel codice.
- Credenziali di prova (utenti demo, PIN, password) solo in `src/lib/accesso/demo-utenti.ts`, mai mostrate nell'interfaccia né ripetute nei messaggi.
- Lavoro su un ramo in un worktree (`login-ruoli`): nella cartella principale lavorano altre sessioni (es. `src/components/Hydrator.tsx` ha modifiche non salvate di un'altra sessione).

## Review Focus
1. Foto di un'azienda chiesta con la sessione di un'altra (`/api/foto/<nome>`) → 404, mai il file. Test nel Task 3.
2. Super admin con ingresso di assistenza scaduto, o senza codice dal telefono attivo → 403 su ogni API dell'azienda. Test nel Task 2.
3. Sessione da PIN ferma da più di 5 minuti, o iniziata più di 10 ore fa → 401 anche se il cookie è valido. Test nel Task 2.
4. Azienda nuova: il primo dispositivo che la apre non deve riempirla con i dati demo del proprio browser. Test nel Task 5 (`devePubblicareStatoLocale`).
5. Ordine dal negozio mentre un dispositivo scrive: entrambe le scritture restano (stesso blocco per azienda). Test nel Task 3 (`aggiornaStato` in serie).

---

### Task 1: Better Auth, database della piattaforma e ruoli

**Files:**
- Modify: `package.json` (dipendenze `better-auth`, `better-sqlite3`, dev `@types/better-sqlite3`; script `test` che includa `src/lib/accesso/*.test.ts`)
- Create: `src/lib/accesso/ruoli.ts`, `src/lib/accesso/ruoli.test.ts`
- Create: `src/lib/auth/permessi.ts`, `src/lib/auth/server.ts`, `src/lib/auth/client.ts`, `src/app/api/auth/[...all]/route.ts`
- Modify: `src/lib/server-data.ts` (costante `DB_FILE`)

**Interfaces:**
- Produces (`src/lib/accesso/ruoli.ts`, puro): `RUOLI: readonly Role[]` nell'ordine sopra; `RUOLO_LABEL: Record<Role, string>` (stesse etichette di `ROLE_USER[r].label` oggi); `ruoliDaStringa(s: string | null | undefined): Role[]` (divide sulla virgola, toglie spazi, scarta valori sconosciuti, toglie doppioni, ordina come `RUOLI`); `ruoliAStringa(r: Role[]): string`.
- Produces (`src/lib/auth/permessi.ts`): `acAzienda`, `ruoliAzienda` (i sei ruoli per il plugin `organization`, ognuno con i permessi base di `member`); `acPiattaforma`, `ruoliPiattaforma` (`superadmin` con tutti i permessi di serie del plugin `admin`, `user` senza permessi).
- Produces (`src/lib/auth/server.ts`): `auth` = `betterAuth({ database: new Database(DB_FILE), emailAndPassword: { enabled: true, disableSignUp: true }, plugins: [organization({ ac: acAzienda, roles: ruoliAzienda, allowUserToCreateOrganization: false }), admin({ ac: acPiattaforma, roles: ruoliPiattaforma, adminRoles: ["superadmin"], defaultRole: "user" }), twoFactor({ issuer: "AutoLost" }), nextCookies()] })`, con `advanced.useSecureCookies` deciso per richiesta (vedi Global Constraints) e `trustedOrigins` dalla variabile `INDIRIZZO_GESTIONALE` se presente. Il Task 6 aggiunge il plugin `pinDispositivo` prima di `nextCookies()`.
- Produces (`src/lib/auth/client.ts`): `authClient` con `organizationClient`, `adminClient`, `twoFactorClient`.
- Produces (`src/lib/server-data.ts`): `DB_FILE = path.join(DATA_DIR, "piattaforma.sqlite")`.

- [ ] **Step 1: Test di `ruoli.ts`**
```ts
test("ruoliDaStringa pulisce e ordina", () => {
  assert.deepEqual(ruoliDaStringa(" accettazione,smontatore ,smontatore"), ["accettazione", "smontatore"]);
  assert.deepEqual(ruoliDaStringa("smontatore,owner,boh"), ["smontatore"]);
  assert.deepEqual(ruoliDaStringa(null), []);
  assert.deepEqual(ruoliDaStringa("vendite,accettazione"), ["accettazione", "vendite"]);
});
test("ruoliAStringa è l'inverso", () => assert.equal(ruoliAStringa(["smontatore", "accettazione"]), "accettazione,smontatore"));
test("RUOLI ha i sei ruoli", () => assert.equal(RUOLI.length, 6));
```
- [ ] **Step 2:** `npm test` → FAIL (modulo mancante). **Step 3:** scrivi `ruoli.ts`. **Step 4:** `npm test` → PASS.
- [ ] **Step 5:** installa le dipendenze, scrivi `permessi.ts`, `server.ts`, `client.ts`, la route `api/auth/[...all]` (`toNextJsHandler(auth)`). Verifica la versione installata e i nomi esatti delle API nei sorgenti in `node_modules/better-auth` (non a memoria).
- [ ] **Step 6:** crea le tabelle su una cartella di prova: `DATI_DIR=/tmp/<cartella-prova> npx auth@latest migrate --config src/lib/auth/server.ts -y` (se la CLI non risolve `@/`, usa `getMigrations` di `better-auth/db` da `instrumentation.ts` come nel Task 9 e verifica lì). Atteso: file `piattaforma.sqlite` con tabelle `user`, `session`, `organization`, `member`, `twoFactor`.
- [ ] **Step 7:** `npx tsc --noEmit` pulito, `npm test` verde. Commit `feat: Better Auth con aziende, super admin e ruoli`.

### Task 2: Regola d'accesso unica

**Files:**
- Create: `src/lib/accesso/regole.ts`, `src/lib/accesso/regole.test.ts`
- Create: `src/lib/accesso/server.ts`
- Create: `src/lib/auth/assistenza.ts` — plugin minimo `assistenzaPlugin` con la tabella `assistenza { userId, organizationId, motivo, inizio, scade, fine? }` e i campi di sessione facoltativi `tipoAccesso` e `dispositivoId` (li usa il Task 6); in `server.ts` va prima di `nextCookies()`

**Interfaces:**
- Consumes: `auth`, `ruoliDaStringa`, `RUOLI`.
- Produces (`regole.ts`, puro): costanti `PIN_INATTIVITA_MS = 300_000`, `PIN_TURNO_MS = 36_000_000`, `ASSISTENZA_MS = 7_200_000`.
  Tipi `SessioneVista = { userId: string; nome: string; ruoloPiattaforma: string | null; dueFattori: boolean; aziendaAttiva: string | null; tipo: "password" | "pin"; creata: number; ultimaAttivita: number; dispositivo?: { id: string; nome: string } }`, `AssistenzaVista = { id: string; organizationId: string; motivo: string; scade: number; fine?: number }`, `AziendaVista = { id: string; nome: string; demo: boolean }`.
  `decidiAccesso(i: { sessione: SessioneVista | null; azienda: AziendaVista | null; ruoliMembro: string | null; assistenza: AssistenzaVista | null; ora: number }): Accesso | Negato`
  `Accesso = { utente: { id: string; nome: string }; azienda: AziendaVista; ruoli: Role[]; superadmin: boolean; tipo: "password" | "pin"; dispositivo?: { id: string; nome: string }; assistenza?: { id: string; motivo: string; scade: string } }`, `Negato = { negato: 401 | 403; motivo: "nessuna-sessione" | "sessione-scaduta" | "nessuna-azienda" | "non-membro" | "assistenza-scaduta" | "due-fattori" }`.
  Regole in ordine: niente sessione → 401 `nessuna-sessione`; tipo `pin` con `ora - ultimaAttivita > PIN_INATTIVITA_MS` o `ora - creata > PIN_TURNO_MS` → 401 `sessione-scaduta`; niente azienda attiva/azienda inesistente → 403 `nessuna-azienda`; membro con almeno un ruolo valido → accesso con quei ruoli; `superadmin` senza `dueFattori` → 403 `due-fattori`; `superadmin` con assistenza della stessa azienda, senza `fine` e `scade > ora` → accesso con tutti i `RUOLI` e `assistenza`; `superadmin` altrimenti → 403 `assistenza-scaduta`; altrimenti 403 `non-membro`.
- Produces (`server.ts`, solo server): `accessoDaRichiesta(req: Request): Promise<Accesso | Response>` (legge la sessione con `auth.api.getSession({ headers: req.headers })`, carica membro, azienda e ultima assistenza, chiama `decidiAccesso`; con `sessione-scaduta` revoca la sessione; per le sessioni PIN aggiorna `updatedAt` se più vecchio di 60 s; il JSON d'errore è `{ error, motivo }` con lo stato giusto); `soloRuoli(a: Accesso, ...r: Role[]): Response | null` (403 se nessuno dei ruoli); `superadminDaRichiesta(req: Request): Promise<{ utente: { id: string; nome: string } } | Response>` (sessione password, ruolo `superadmin`, due fattori attivi).
  L'azienda è `demo` se `organization.metadata` contiene `{"demo":true}`.

- [ ] **Step 1: Test** (tutti in `regole.test.ts`, con una `base()` che costruisce input validi):
  - membro con `"accettazione,smontatore"` → `ruoli` `["accettazione","smontatore"]`, `superadmin: false`;
  - nessuna sessione → `{ negato: 401, motivo: "nessuna-sessione" }`;
  - PIN fermo da 5 min + 1 ms → 401 `sessione-scaduta`; fermo da 4 min 59 s → accesso;
  - PIN creato 10 h + 1 ms fa ma attivo ora → 401 `sessione-scaduta`;
  - sessione password ferma da 3 ore → accesso (la regola dei 5 minuti vale solo per il PIN);
  - membro con solo `"owner"` → 403 `non-membro`;
  - super admin senza due fattori, con assistenza valida → 403 `due-fattori`;
  - super admin con assistenza valida → `ruoli` uguale a `RUOLI`, `assistenza.motivo` presente;
  - super admin con assistenza scaduta (`scade = ora`) → 403 `assistenza-scaduta`; con `fine` impostata → 403 `assistenza-scaduta`;
  - super admin con assistenza di un'altra azienda → 403 `assistenza-scaduta`;
  - utente non superadmin con assistenza (dati incoerenti) → 403 `non-membro`.
- [ ] **Step 2:** `npm test` → FAIL. **Step 3:** scrivi `regole.ts`, poi `assistenza.ts` e `server.ts`. **Step 4:** `npm test` → PASS, `npx tsc --noEmit` pulito. **Step 5:** commit `feat: regola d'accesso unica per aziende, PIN e assistenza`.

### Task 3: Archivio per azienda e API della gestione protette

**Files:**
- Create: `src/lib/accesso/id-azienda.ts` (+ test), `src/lib/archivio-unione.ts` (+ test), `src/lib/archivio-azienda.ts`, `src/lib/schema.ts`, `src/lib/stato-iniziale.ts` (+ test)
- Modify: `src/lib/server-data.ts`, `src/lib/store.ts` (importa e riesporta `STORE_SCHEMA` da `schema.ts`), `src/app/api/demo-state/route.ts`, `src/app/api/foto/route.ts`, `src/app/api/foto/[name]/route.ts`, `src/app/api/indirizzo/route.ts`, `src/app/api/collegamenti/route.ts`, `src/lib/collegamenti-server.ts`

**Interfaces:**
- Consumes: `accessoDaRichiesta`, `soloRuoli`.
- Produces: `idAziendaValido(id: string): boolean` (`/^[A-Za-z0-9_-]{1,64}$/`). `cartellaAzienda(id: string): string` e `cartellaFotoAzienda(id: string): string` in `server-data.ts` (lanciano errore se l'id non è valido). `PHOTO_DIR` resta solo per la copia dei dati storici (Task 9).
- Produces (`archivio-unione.ts`, puro): `mergeList`, `maxCounters`, `unisciPush(stored: Stored, body: Push): Stored` spostati da `demo-state/route.ts` senza cambiarne il comportamento; tipi `Stored`, `Push`.
- Produces (`schema.ts`, puro): `STORE_SCHEMA` (stesso valore di oggi).
- Produces (`stato-iniziale.ts`, puro): `statoVuoto(base: { listini: unknown[]; warehouses: unknown[] }): Record<string, unknown>` con tutte le liste condivise vuote, `rules: []`, `soggetti: []`, i `listini` e `warehouses` passati, contatori a zero (`docs` con `P, DC, FT, NC` a zero, `annuncio: 0`).
- Produces (`archivio-azienda.ts`, solo server): `leggiStato(aziendaId: string): Promise<Stored>`; `aggiornaStato<T>(aziendaId: string, fn: (s: Stored) => { stored: Stored; risultato: T }): Promise<T>` (un blocco per azienda: le scritture della stessa azienda vanno in fila, quelle di aziende diverse no); `creaStatoAzienda(aziendaId: string, stato: Record<string, unknown>): Promise<void>` (scrive solo se il file non c'è); `aggiungiEventi(aziendaId: string, eventi: { user: string; role: string; device: string; entity: string; entityId: string; action: string; detail?: string }[]): Promise<void>` (assegna `id` `E-<n>` dal contatore `event` e `at`, in fondo a `audit`, nello stesso blocco).
- `/api/demo-state`: GET → `{ schema, version, state, demo }` dell'azienda della sessione; PUT con `replace: true` permesso solo se l'azienda è demo **e** (`responsabile` nei ruoli o super admin in assistenza), altrimenti 403; il resto passa per `aggiornaStato` + `unisciPush`.
- `/api/foto` POST salva in `cartellaFotoAzienda`; `/api/foto/[name]` GET cerca solo nella cartella dell'azienda della sessione (l'eccezione pubblica arriva nel Task 8). `/api/indirizzo` e `/api/collegamenti` dietro `accessoDaRichiesta`; collegamenti modificabili solo da `responsabile` o super admin; `collegamenti.json` per azienda (`load(aziendaId)`, `save(aziendaId, a)`, `leggiValori(aziendaId, id)`).

- [ ] **Step 1: Test**
  - `idAziendaValido`: vero per `"az_1-B"`; falso per `""`, `"../x"`, `"a/b"`, `"a.b"`, 65 caratteri.
  - `unisciPush`: casi già coperti oggi dal comportamento della route (nuovi in cima per `parts`, in fondo per `audit` con chiave id+ora, `whole` sostituito, contatori al massimo, `replace` sostituisce tutto, schema diverso sostituisce tutto) → un test per ciascuno.
  - Due `unisciPush` in serie con modifiche a record diversi (un ordine nuovo, un pezzo modificato) → entrambi presenti (Review Focus 5).
  - `statoVuoto`: `parts`, `vehicles`, `annunci`, `orders`, `audit` vuoti; `counters.order === 0`; `listini` uguale a quello passato.
- [ ] **Step 2:** FAIL. **Step 3:** implementa i moduli e adatta le route. **Step 4:** `npm test` verde, `tsc` pulito.
- [ ] **Step 5: Verifica a mano** su porta di prova con due aziende (create via `auth.api` in uno script o dal Task 9 se già pronto, altrimenti con `auth.api.createOrganization` da una route di prova da non salvare): foto caricata da A, chiesta con la sessione di B → 404 (Review Focus 1); `GET /api/demo-state` senza cookie → 401.
- [ ] **Step 6:** commit `feat: dati separati per azienda e API protette`.

### Task 4: eBay per azienda e collegamento legato alla sessione

**Files:**
- Modify: `src/lib/ebay/archivio.ts`, `src/lib/ebay/server.ts`, `src/lib/ebay/sandbox.ts`, tutte le route in `src/app/api/ebay/*`

**Interfaces:**
- Consumes: `accessoDaRichiesta`, `soloRuoli`, `cartellaAzienda`, `leggiValori(aziendaId, id)`.
- Produces: ogni funzione dell'archivio eBay prende `aziendaId` come primo parametro (`leggiArchivio(aziendaId)`, `aggiornaArchivio(aziendaId, fn)`), file `aziende/<id>/ebay.json`; `scegliPonte(aziendaId)`, `credenzialiSandbox(aziendaId)`; il ponte sandbox riceve `aziendaId` alla creazione.
- Stato OAuth salvato con `{ valore, userId, scade }`; `/api/ebay/collega` (avvio) e `/api/ebay/ritorno` richiedono sessione con `responsabile` o super admin in assistenza; il ritorno accetta lo stato solo se `userId` è quello della sessione corrente, lo consuma solo dopo il confronto riuscito.
- `/api/ebay/vendite`, `/allinea`, `/stato`, `/politiche`: azienda dalla sessione; `politiche` PUT e `collega` DELETE solo `responsabile` o super admin.

- [ ] **Step 1:** aggiorna i test esistenti in `src/lib/ebay/*.test.ts` se cambiano firme di funzioni pure (non dovrebbero: i moduli puri non leggono file). **Step 2:** applica le modifiche. **Step 3:** `npm test` verde (139 + nuovi), `tsc` pulito.
- [ ] **Step 4: Verifica** su porta di prova: con eBay simulato, pubblicare un annuncio dall'azienda demo funziona come prima; `POST /api/ebay/vendite` senza sessione → 401; ritorno OAuth con uno `state` valido ma sessione di un altro utente → rinvio a Collegamenti con codice d'errore `stato`.
- [ ] **Step 5:** commit `feat: eBay per azienda, collegamento legato a chi lo avvia`.

### Task 5: Pagina di accesso, proxy, sessione nel client

**Files:**
- Create: `src/proxy.ts`, `src/app/accesso/page.tsx` (+ view), `src/app/api/sessione/route.ts`, `src/lib/accesso/client.ts`, `src/lib/sync-regole.ts` (+ test)
- Modify: `src/components/Hydrator.tsx`, `src/lib/sync.ts`, `src/lib/store.ts`, `src/components/AppShell.tsx`, `src/app/(app)/view.tsx`, `src/components/PraticaPanel.tsx`

**Interfaces:**
- Consumes: `Accesso`, `accessoDaRichiesta`, `authClient`, `RUOLI`, `RUOLO_LABEL`.
- Produces: `GET /api/sessione` → `Accesso` (200) oppure `{ error, motivo }` (401/403). `useSessione()` in `src/lib/accesso/client.ts` (carica una volta, espone `Accesso | null` e `ricarica()`).
- `proxy.ts`: pagine **pubbliche** = `/accesso`, `/negozio/**`, `/ebay-simulato/**`, `/scopri`, `/news/**`, `/robots.txt`, `/sitemap.xml`, `/api/auth/**`, `/api/negozio/**`, `/api/foto/**` (la route decide da sola), file statici; tutte le altre pagine senza cookie di sessione (`getSessionCookie`) → rinvio a `/accesso?da=<percorso>`. Le API senza cookie lasciate passare: rispondono 401 da sole.
- Store: nuovo stato locale `operatore: { nome: string; dispositivo: string; assistenza: boolean } | null` e `ruoliPermessi: Role[]`; `setRole` accetta solo ruoli in `ruoliPermessi`; `event()` e gli altri punti che oggi usano `ROLE_USER[role].user/device` usano `operatore` (nome + `" (assistenza)"` se in assistenza); `ROLE_USER` sparisce, le etichette vengono da `RUOLO_LABEL`.
- Persistenza locale per azienda: nome della chiave `${STORE_SCHEMA}:${aziendaId}` (Zustand `persist.setOptions({ name })` prima di `rehydrate`); cambiando azienda sullo stesso browser i dati locali dell'altra azienda non si caricano.
- `sync-regole.ts` (puro): `devePubblicareStatoLocale(server: { state: unknown; schema: string; demo: boolean }, schemaLocale: string): boolean` → vero solo se l'azienda è demo e lo stato del server manca o ha schema diverso. `sync.ts` usa questa regola: per le aziende non demo non manda mai lo stato locale intero; se il server ha uno stato con schema diverso mostra l'avviso e resta in sola lettura locale.
- Accesso: email+password; se l'utente ha i due fattori, secondo passo con il codice; dopo l'accesso: super admin → `/piattaforma`, utente con più aziende (non previsto ora) → la prima; altrimenti `/`. Uscita nel menu in basso.
- `AppShell`: menu "Stai usando come" con solo `ruoliPermessi` (nascosto se uno solo); in fondo nome della persona e del dispositivo da `operatore`; fascia fissa "Assistenza in corso · <azienda> · Esci" quando `assistenza` (Esci chiama l'API del Task 7).

- [ ] **Step 1: Test** `devePubblicareStatoLocale`: demo + stato nullo → vero; demo + schema diverso → vero; non demo + stato nullo → falso (Review Focus 4); non demo + schema diverso → falso; demo + stesso schema → falso.
- [ ] **Step 2:** FAIL. **Step 3:** implementa. **Step 4:** `npm test` verde, `tsc` pulito.
- [ ] **Step 5: Verifica nel browser** (porta di prova): `/ricambi` senza accesso → `/accesso`; entra come responsabile demo → vede il gestionale, menu ruoli con i suoi ruoli soltanto; utente con `accettazione,smontatore` vede solo quei due; `/negozio` si apre senza accesso.
- [ ] **Step 6:** commit `feat: pagina di accesso, protezione delle pagine e ruoli dalla sessione`.

### Task 6: Dispositivi dell'azienda e accesso con PIN

**Files:**
- Create: `src/lib/accesso/pin.ts` (+ test), `src/lib/auth/pin-dispositivo.ts`, `src/lib/auth/pin-dispositivo-client.ts`
- Create: vista elenco nomi + PIN dentro `src/app/accesso/`, `src/components/BloccoInattivita.tsx`, pagina impostazioni `src/app/(app)/impostazioni/dispositivi/` (+ voce nel menu per `responsabile`)
- Modify: `src/lib/auth/server.ts`, `src/lib/auth/client.ts`, `src/lib/sync.ts`

**Interfaces:**
- Produces (`pin.ts`, puro): costanti `PIN_ERRORI_UTENTE = 5`, `PIN_BLOCCO_UTENTE_MS = 900_000`, `PIN_ERRORI_DISPOSITIVO = 20`, `PIN_FINESTRA_DISPOSITIVO_MS = 900_000`; `pinValido(pin: string): boolean` (`/^\d{4}$/`); tipi `StatoPinUtente = { errori: number; bloccatoFino: number | null }`, `StatoPinDispositivo = { errori: number[] /* istanti */; bloccato: boolean }`; `dopoTentativo(s: { utente: StatoPinUtente; dispositivo: StatoPinDispositivo }, corretto: boolean, ora: number): { utente: StatoPinUtente; dispositivo: StatoPinDispositivo; esito: "ok" | "sbagliato" | "utente-bloccato" | "dispositivo-bloccato" }` — se il dispositivo è bloccato o il nome è bloccato (prima del controllo) l'esito è il blocco e il PIN non si valuta; corretto → errori dell'utente a zero; sbagliato → +1, al quinto `bloccatoFino = ora + 15 min`; errori del dispositivo contati nella finestra di 15 minuti, al ventesimo `bloccato = true`.
- Produces (plugin `pinDispositivo`, id `pin-dispositivo`): tabelle `dispositivo { organizationId, nome, tokenHash, creatoDa, creato, revocato?, bloccato, erroriPin (JSON) }`, `pinUtente { userId, organizationId, pinHash, errori, bloccatoFino? }`. Endpoint:
  - `POST /pin-dispositivo/registra { nome }` — sessione password con `responsabile` (o super admin in assistenza); crea il dispositivo, cookie `dispositivo` HttpOnly, SameSite=Lax, 400 giorni, valore casuale di 32 byte (in tabella solo l'hash SHA-256).
  - `GET /pin-dispositivo/nomi` — dal cookie: `{ azienda: string; dispositivo: string; bloccato: boolean; nomi: { userId: string; nome: string; bloccato: boolean }[] }` (utenti dell'azienda con PIN, non disattivati).
  - `POST /pin-dispositivo/entra { userId, pin }` — usa `dopoTentativo`; con `ok` crea la sessione (`tipoAccesso: "pin"`, `dispositivoId`, azienda attiva = quella del dispositivo) e imposta il cookie di sessione; ogni blocco scrive un evento nel registro dell'azienda (`aggiungiEventi`).
  - `POST /pin-dispositivo/revoca { dispositivoId }`, `POST /pin-dispositivo/sblocca { dispositivoId }` — responsabile dell'azienda o super admin in assistenza; evento nel registro.
  - `GET /pin-dispositivo/elenco` — dispositivi dell'azienda della sessione per la pagina impostazioni.
  - Hash del PIN con l'hasher delle password di Better Auth (`ctx.context.password.hash/verify`). Verifica i nomi esatti di `internalAdapter.createSession` e di `setSessionCookie` (`better-auth/cookies`) nei sorgenti installati.
- `BloccoInattivita`: con sessione PIN, dopo 5 minuti senza tocchi o tasti, prima prova `pushChanges` (esporta da `sync.ts` una `inviaInSospeso(): Promise<boolean>`), poi esce e torna all'elenco nomi. Le modifiche non inviate restano nella copia locale dell'azienda e partono al prossimo accesso.

- [ ] **Step 1: Test** `pin.ts`: `pinValido("0123")` vero, `"123"`/`"12a4"`/`"12345"` falsi; 4 errori poi PIN giusto → `ok` ed errori a 0; 5 errori → quinto esito `sbagliato` con `bloccatoFino = ora+900000`, sesto tentativo (anche giusto) → `utente-bloccato`; dopo `bloccatoFino` il PIN giusto → `ok`; 20 errori su nomi diversi in 14 minuti → ventesimo porta `dispositivo.bloccato = true` e il tentativo dopo → `dispositivo-bloccato`; 20 errori sparsi in 30 minuti → non bloccato.
- [ ] **Step 2:** FAIL. **Step 3:** implementa modulo, plugin, viste. **Step 4:** `npm test`, `tsc`.
- [ ] **Step 5: Verifica nel browser** (porta di prova): responsabile registra il dispositivo → l'accesso mostra i nomi → nome + PIN entra in meno di 5 secondi; dopo 5 minuti fermo torna ai nomi (per la prova abbassa temporaneamente la costante solo in locale, non salvarla); 5 PIN sbagliati bloccano il nome; il dispositivo revocato torna all'accesso con email.
- [ ] **Step 6:** commit `feat: dispositivi dell'azienda e accesso con nome e PIN`.

### Task 7: Area Piattaforma del super admin

**Files:**
- Create: `src/app/piattaforma/` (layout senza `AppShell` della gestione; pagine: elenco aziende, nuova azienda, scheda azienda con utenti e dispositivi, sicurezza con attivazione del codice dal telefono)
- Create: `src/app/api/piattaforma/aziende/route.ts`, `.../aziende/[id]/utenti/route.ts`, `.../utenti/[userId]/route.ts`, `.../richieste/route.ts` (+ `[file]`), `.../assistenza/route.ts`
- Create: `src/lib/accesso/richieste.ts` (+ test)

**Interfaces:**
- Consumes: `superadminDaRichiesta`, `creaStatoAzienda`, `statoVuoto`, `aggiungiEventi`, `ruoliAStringa`, `ruoliDaStringa`, `auth.api` (`createOrganization` con `userId` del super admin ma senza aggiungerlo come membro — se l'API lo aggiunge per forza come `owner`, rimuovilo subito dopo; `addMember`, `updateMemberRole`, `createUser`, `setUserPassword`, `banUser`, `unbanUser`), tabelle del plugin PIN.
- Produces (`richieste.ts`, puro): `RICHIESTA_MAX_BYTE = 10_485_760`; `tipoRichiesta(primiByte: Uint8Array): "pdf" | "jpeg" | "png" | null` (firma del file, non estensione); `richiestaObbligatoria(azione: "crea" | "ruoli" | "pin" | "password" | "disattiva"): boolean` (vero solo per `crea` e `ruoli`).
- API (tutte `superadminDaRichiesta`): aziende GET (nome, utenti, ultimo accesso) / POST `{ nome }` → crea organizzazione + `creaStatoAzienda(id, statoVuoto(...))`; utenti GET / POST `{ nome, ruoli: Role[], email?, password?, pin?, richiesta: { fileId?, estremi: string } }` (almeno un ruolo; almeno uno tra email+password e PIN; utenti solo PIN con email interna `<id>@pin.invalid` e nessuna password); PATCH utente `{ ruoli?, pin?, password?, attivo?, richiesta? }`; richieste POST multipart → salva in `aziende/<id>/richieste/<casuale>.<ext>`, restituisce `fileId`; GET file per il super admin. Ogni modifica → `aggiungiEventi` nell'azienda (utente "Alessandro (assistenza)" o il nome del super admin, ruolo `"sistema"`, dispositivo "Piattaforma").
- Assistenza: POST `{ aziendaId, motivo }` (motivo 3–300 caratteri) → riga `assistenza` con `scade = ora + ASSISTENZA_MS`, azienda attiva della sessione = quella, evento "Ingresso assistenza" con il motivo; DELETE → `fine = ora`, azienda attiva nulla, evento "Uscita assistenza".
- Sicurezza: pagina che usa `twoFactor.enable` (QR con la libreria `qrcode` già presente, codici di riserva mostrati una volta). Finché non è attivo, "Entra per assistenza" è disattivato con la spiegazione.

- [ ] **Step 1: Test** `richieste.ts`: `%PDF` → `pdf`; `FF D8 FF` → `jpeg`; `89 50 4E 47` → `png`; testo → `null`; `richiestaObbligatoria("crea")` e `("ruoli")` veri, `("pin")` falso.
- [ ] **Step 2:** FAIL. **Step 3:** implementa API e pagine. **Step 4:** `npm test`, `tsc`.
- [ ] **Step 5: Verifica nel browser:** super admin attiva il codice dal telefono (genera il codice con lo stesso segreto in uno script locale, non con un'app), crea un'azienda nuova (si apre vuota, nessun dato demo), crea un utente con due ruoli allegando un PDF di prova, entra per assistenza con un motivo → il registro dell'azienda mostra ingresso e motivo; esce → evento di uscita; utente disattivato → la sua sessione aperta riceve 401 alla richiesta successiva.
- [ ] **Step 6:** commit `feat: area Piattaforma per aziende, utenti e assistenza`.

### Task 8: Negozio pubblico senza archivio

**Files:**
- Create: `src/lib/negozio-ordine.ts`, `src/lib/catalogo-pubblico.ts` (+ test), `src/app/api/negozio/catalogo/route.ts`, `src/app/api/negozio/ordine/route.ts`, `src/app/api/negozio/paga/route.ts`
- Modify: `src/lib/store.ts` (`orderFromAnnunci` e `payOrder` delegano al nuovo modulo), `src/components/Hydrator.tsx` (ramo pubblico), `src/app/negozio/**`, `src/app/ebay-simulato/[id]/view.tsx`, `src/app/api/foto/[name]/route.ts`, `src/lib/types.ts` (`Order.tokenNegozio?: string`)

**Interfaces:**
- Produces (`negozio-ordine.ts`, senza `"use client"`, usabile da store e server): `type StatoCondiviso` (le chiavi condivise dello store: `vehicles, parts, annunci, orders, audit, counters` e le altre di `SHARED` in `sync.ts`); `ordineNegozio(st: StatoCondiviso, i: { annuncioIds: string[]; cliente: string; consegna: "corriere" | "ritiro" }, at: string): { ok: true; st: StatoCondiviso; ordineId: string } | { ok: false; error: string; conflicts?: string[] }` e `pagaOrdine(st: StatoCondiviso, ordineId: string, riuscito: boolean, attore: { user: string; role: string; device: string }, at: string): StatoCondiviso` — stessa logica, stessi eventi nel registro e stesso aggiornamento degli annunci (`refreshAnnuncio`, esaurito) di oggi in `store.ts`. Lo store le chiama e il comportamento non cambia (i 139 test esistenti restano verdi).
- Produces (`catalogo-pubblico.ts`, puro): `catalogoPubblico(st: { annunci; parts; vehicles }): { annunci: Annuncio[]; parts: Part[]; vehicles: Vehicle[] }` — annunci con negozio `online` o `esaurito` o con canale eBay; dei pezzi solo quelli di quegli annunci, e dei pezzi e veicoli solo i campi che negozio e pagina eBay simulato leggono (niente note interne, prezzi d'acquisto, dati di chi ha portato il veicolo, targa e telaio). `fotoPubblica(st, nomeFile: string): boolean` — vera se il file è tra le foto di un pezzo restituito da `catalogoPubblico`.
- API (azienda = `NEGOZIO_AZIENDA` o la demo): `GET /api/negozio/catalogo`; `POST /api/negozio/ordine { annuncioIds, nome, consegna }` → con `aggiornaStato` e `ordineNegozio` → `{ ordineId, token, importo }` (token casuale di 16 byte salvato su `Order.tokenNegozio`); `POST /api/negozio/paga { ordineId, token, riuscito }` → 404 se il token non corrisponde. Le due POST accettano solo JSON (come `/api/ebay/vendite`), massimo 2 KB, al massimo 10 annunci.
- `/api/foto/[name]` GET: con sessione valida → cartella dell'azienda della sessione; senza sessione → se `fotoPubblica` nell'azienda del negozio, la serve da lì, altrimenti 404.
- Hydrator: su `/negozio/**` ed `/ebay-simulato/**` niente sessione, niente sincronizzazione, niente copia locale: carica il catalogo nello store (`useStore.setState`) e lo ricarica ogni 30 secondi. Il carrello usa le API del negozio al posto delle azioni dello store.

- [ ] **Step 1: Test** `catalogo-pubblico.ts`: un annuncio online con due pezzi e uno in bozza → solo il primo con i suoi due pezzi; il veicolo restituito non ha `plate` né `vin`; `fotoPubblica` vera per una foto di quei pezzi, falsa per la foto di un pezzo in bozza e per un nome inventato.
- [ ] **Step 2:** FAIL. **Step 3:** implementa. **Step 4:** `npm test` verde (compresi i 139 esistenti), `tsc`.
- [ ] **Step 5: Verifica nel browser** (porta di prova, senza accesso): negozio mostra gli annunci, le foto si vedono, ordine + pagamento simulato funzionano; poi da un dispositivo del gestionale l'ordine compare in Vendite; `GET /api/demo-state` senza accesso → 401; una foto di un pezzo non pubblicato chiesta senza accesso → 404.
- [ ] **Step 6:** commit `feat: negozio pubblico con catalogo e ordini dal server`.

### Task 9: Avvio della piattaforma, dati demo e passaggio dei dati attuali

**Files:**
- Create: `src/instrumentation.ts`, `src/lib/accesso/avvio.ts`, `src/lib/accesso/demo-utenti.ts`
- Modify: `src/lib/store.ts` / `src/lib/sync.ts` ("Ripristina dati demo" solo dove permesso), `docs/INTEGRAZIONI.md` o nuovo `docs/ACCESSO.md`

**Interfaces:**
- Produces: `avviaPiattaforma(): Promise<void>` chiamata una volta da `register()` in `instrumentation.ts` (solo runtime Node): applica le migrazioni (`getMigrations(auth.options).runMigrations()`); se non esiste nessuna azienda crea "Autodemolizione demo" (`slug: "demo"`, `metadata: {"demo":true}`), gli utenti di `demo-utenti.ts` con ruoli e PIN/password, e copia i dati storici (`DATA_DIR/state.json`, `foto/`, `collegamenti.json`, `ebay.json`) in `aziende/<id demo>/` lasciando gli originali; se mancano dati storici scrive lo stato demo con `buildSeed` tramite il primo dispositivo (regola `devePubblicareStatoLocale`); se `SUPERADMIN_EMAIL` è impostata e non c'è un super admin lo crea con ruolo `superadmin`. Mai errori fatali all'avvio: in caso di problema scrive nel log del server e il gestionale risponde 503 sulle API.
- `demo-utenti.ts`: Giulia (accettazione, PIN), Marco (smontatore, PIN), Luca (smontatore + accettazione, PIN), Paolo (magazziniere, PIN), Sara (responsabile, email+password e PIN), Anna (vendite, PIN), Laura (consulente, email+password). Email sul dominio `demo.autodemolizione.test`. Valori di prova scelti qui.
- `ACCESSO.md`: variabili d'ambiente (`DATI_DIR`, `SUPERADMIN_*`, `NEGOZIO_AZIENDA`, `INDIRIZZO_GESTIONALE`, `BETTER_AUTH_SECRET`), come si crea il super admin, dove stanno i dati di ogni azienda, il limite noto (ruoli controllati solo nelle schermate fino al database dei dati).

- [ ] **Step 1:** implementa. **Step 2: Verifica** su cartella di prova copiata dai dati attuali: al primo avvio nasce l'azienda demo con i dati di prima (stessi veicoli e ricambi), gli originali restano; secondo avvio non duplica nulla. **Step 3:** `npm test`, `tsc`. **Step 4:** commit `feat: avvio della piattaforma con azienda demo e passaggio dei dati`.

### Task 10: Prova completa e documenti

- [ ] **Step 1:** su porta di prova e cartella di prova, giro completo nel browser: super admin (codice dal telefono) → nuova azienda → utente con due ruoli → dispositivo registrato → nome+PIN → lavoro → blocco dopo inattività → assistenza con motivo visibile nel registro → negozio pubblico che ordina → ordine visibile nella gestione. Schermata finale in `docs/superpowers/screenshots/2026-11-18-login-ruoli.png`.
- [ ] **Step 2:** aggiorna `docs/ROADMAP.md` (A2, A4, A13 parzialmente fatti, con il limite noto) e la nota di sicurezza in `src/lib/collegamenti-server.ts` (non più "nessun login vero").
- [ ] **Step 3:** `npm test`, `npx tsc --noEmit`, `npm run lint` sui file toccati. Commit `docs: login, ruoli e più aziende`.
