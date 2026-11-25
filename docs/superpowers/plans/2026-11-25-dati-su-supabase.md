# Dati su Supabase — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Il gestionale salva utenti, archivi, documenti e file su Supabase quando gira su Vercel, e su disco in locale, dietro un unico passaggio (`deposito`).

**Architecture:** Un modulo `src/lib/deposito/` espone un'interfaccia `Deposito` con due realizzazioni: `disco` (comportamento di oggi, stessi percorsi sotto `DATI_DIR`) e `supabase` (Postgres per i documenti JSON con `SELECT … FOR UPDATE`, spazio file privato per i binari). Better Auth passa da SQLite a Postgres quando c'è `DATABASE_URL`. Tutti i file che oggi toccano il disco passano dal deposito.

**Tech Stack:** Next 16 (App Router, `cacheComponents`), Better Auth 1.7, `pg` (node-postgres), `@supabase/supabase-js` (solo spazio file), test con `node --test` (`npm test`).

**Spec:** `docs/superpowers/specs/2026-11-25-prova-15-giorni-supabase-design.md` (sezioni "Come funziona" 1-2, "Variabili d'ambiente nuove", "Limiti del piano gratuito"). Questo è il primo di tre piani: poi `2026-11-25-prova-15-giorni.md` (registrazione, prova, email) e `2026-11-25-documenti-legali-landing.md`.

## Global Constraints

- Leggere `node_modules/next/dist/docs/` prima di scrivere route o config (vedi `AGENTS.md`); niente `export const dynamic` (incompatibile con `cacheComponents`).
- Corpo delle richieste su Vercel: massimo **4,5 MB**. Le foto e gli allegati in base64 devono stare sotto: limite **3 MB** di file per `api/foto` e `api/allegati`.
- Chiavi di Supabase e `DATABASE_URL` solo sul server: mai in componenti client, mai `NEXT_PUBLIC_`, mai nel codice versionato.
- Nessun indirizzo `supabase.co` deve arrivare al browser: i file si servono sempre dalle route del gestionale.
- Ogni tabella creata dal gestionale ha la sicurezza per riga (RLS) attiva e nessuna policy: si accede solo con la connessione Postgres del server.
- In locale e nei test senza variabili Supabase tutto resta su disco e i 440 test di oggi passano senza modifiche alle loro asserzioni.
- Messaggi all'utente in italiano semplice, come nel resto dell'app.
- Progetti Supabase: produzione `Piazzale` (`vfdccawezxolcblhtavk`); prove `Piazzale prove` (da creare nel Task 7), entrambi nell'organizzazione gratuita `Piazzale`.

## Review Focus

1. **Due salvataggi insieme della stessa azienda da due server diversi** (due tablet): nessuno dei due deve andare perso. → test di concorrenza nel Task 1 (contratto) e nel Task 5 (Postgres).
2. **Foto o PDF troppo grandi dal telefono:** risposta 413 con il messaggio del gestionale, non l'errore grezzo di Vercel. → test nel Task 3.
3. **Variabili a metà su Vercel** (c'è `SUPABASE_URL` ma manca `DATABASE_URL`, o il contrario): errore chiaro all'avvio, mai scrittura silenziosa sul disco di sola lettura. → test di `sceltaDeposito` nel Task 1.
4. **Nomi di file o id azienda costruiti male** (`../`, barre, id non valido): rifiutati prima di toccare disco o spazio file. → test nel Task 1 (contratto, vale per entrambe le realizzazioni).
5. **Un file di un'altra azienda con lo stesso nome:** non si legge mai. → test nel Task 1 (contratto).

---

### Task 1: Interfaccia `Deposito`, realizzazione su disco e test di contratto

**Files:**
- Create: `src/lib/deposito/tipi.ts`, `src/lib/deposito/disco.ts`, `src/lib/deposito/index.ts`
- Create: `src/lib/deposito/contratto.ts` (test riusabili per ogni realizzazione), `src/lib/deposito/disco.test.ts`, `src/lib/deposito/scelta.test.ts`
- Modify: `package.json` (aggiungere `src/lib/deposito/*.test.ts` allo script `test`)

**Interfaces:**
- Produces (in `tipi.ts`):
  - `type TipoDocumento = "archivio" | "abbonamento" | "collegamenti" | "ebay" | "richieste"`
  - `type CartellaFile = "foto" | "allegati" | "visure" | "richieste"`
  - `interface Modifica<T, R> { dati: T; risultato: R; nonScrivere?: boolean }`
  - `class DocumentoIlleggibile extends Error` (con `tipo: TipoDocumento`, `aziendaId: string`)
  - `interface Deposito {`
    - `leggiDocumento<T>(aziendaId: string, tipo: TipoDocumento): Promise<T | null>`
    - `aggiornaDocumento<T, R>(aziendaId: string, tipo: TipoDocumento, fn: (prima: T | null) => Modifica<T, R> | Promise<Modifica<T, R>>): Promise<R>` — lettura e scrittura atomiche per (azienda, tipo); le chiamate sulla stessa coppia vanno in fila
    - `creaDocumento<T>(aziendaId: string, tipo: TipoDocumento, dati: T): Promise<boolean>` — `false` se c'era già
    - `salvaFile(aziendaId: string, cartella: CartellaFile, nome: string, dati: Uint8Array, opz?: { soloSeNuovo?: boolean }): Promise<boolean>` — `false` se `soloSeNuovo` e il file c'era
    - `leggiFile(aziendaId: string, cartella: CartellaFile, nome: string): Promise<Buffer | null>`
    - `togliAzienda(aziendaId: string): Promise<void>` — documenti e file dell'azienda
    - `aggiornaContoAccount<R>(chiave: string, fn: (prima: StatoAccount | undefined) => { stato: StatoAccount; risultato: R }): Promise<R>` (tipo `StatoAccount` da `src/lib/accesso/tentativi-account.ts`)
  - `}`
- Produces (in `index.ts`): `deposito(): Deposito` (istanza unica sulla `globalThis`) e `sceltaDeposito(env: Record<string, string | undefined>): "disco" | "supabase"`, che lancia `Error("Configurazione Supabase incompleta: servono SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY e DATABASE_URL")` se ne è impostata solo una parte.
- Produces (in `contratto.ts`): `provaContratto(nome: string, crea: () => Promise<Deposito>, pulisci: () => Promise<void>): void`, che registra i test di contratto con `node:test`.

- [ ] **Step 1: Scrivere i test di contratto in `contratto.ts`**, chiamati da `disco.test.ts` con una `DATI_DIR` temporanea (`mkdtemp`). Test e asserzioni:
  - `documento assente → null`: `leggiDocumento("az1…", "abbonamento")` è `null` (usare id validi per `idAziendaValido`).
  - `aggiorna e rilegge`: `aggiornaDocumento` con `fn = p => ({ dati: { n: (p?.n ?? 0) + 1 }, risultato: "ok" })` restituisce `"ok"` e poi `leggiDocumento` dà `{ n: 1 }`.
  - `nonScrivere non scrive`: con `nonScrivere: true` il documento resta `null`.
  - `venti aggiornamenti in parallelo`: 20 chiamate `aggiornaDocumento` lanciate insieme sullo stesso (azienda, tipo) → valore finale `{ n: 20 }`.
  - `fn asincrona`: un `fn` che fa `await` prima di restituire funziona come quello sincrono.
  - `creaDocumento una volta sola`: prima `true`, seconda `false`, il dato resta il primo.
  - `file: salva e rilegge` byte per byte; `soloSeNuovo` la seconda volta dà `false` e non sovrascrive.
  - `file di un'altra azienda`: salvato per A, `leggiFile(B, stessa cartella, stesso nome)` è `null`.
  - `nomi non validi rifiutati`: `salvaFile(A, "foto", "../x.jpg", …)`, `"a/b.jpg"`, `""` lanciano; `leggiDocumento("../x", "archivio")` lancia.
  - `togliAzienda`: dopo, documenti e file di A sono `null`; quelli di B restano.
  - `conto account`: `aggiornaContoAccount("u:1", p => ({ stato: { errori: [...(p?.errori ?? []), 1], bloccatoFino: null, inVolo: new Map([["g", 5]]) }, risultato: p === undefined }))` dà `true` la prima volta e `false` la seconda; la `Map` `inVolo` torna una `Map`.
- [ ] **Step 2: Scrivere `scelta.test.ts`:** nessuna variabile → `"disco"`; tutte e tre → `"supabase"`; solo `SUPABASE_URL` → lancia con il messaggio indicato sopra; solo `DATABASE_URL` → lancia.
- [ ] **Step 3: Eseguire `npm test`** — Expected: FAIL, moduli `deposito` inesistenti.
- [ ] **Step 4: Scrivere `tipi.ts`, `index.ts` e `disco.ts`.** Su disco i percorsi sono quelli di oggi, così i dati locali esistenti restano leggibili:

  | Tipo / cartella | Percorso sotto `cartellaAzienda(id)` |
  |---|---|
  | `archivio` | `state.json` |
  | `abbonamento` | `abbonamento.json` |
  | `collegamenti` | `collegamenti.json` (permessi `0o600`) |
  | `ebay` | `ebay.json` (`0o600`) |
  | `richieste` | `richieste/registro.json` |
  | file `foto` / `allegati` / `visure` / `richieste` | `foto/`, `allegati/`, la cartella di oggi in `visura-server.ts`, `richieste/` |

  Scrittura con file temporaneo e rinomina; `creaDocumento` e `soloSeNuovo` con `creaUnaVolta` / flag `wx`; la fila per (azienda, tipo) con `inFilaPer` di `src/lib/fila.ts`. Un JSON illeggibile lancia `DocumentoIlleggibile` e non si sovrascrive mai. Nomi di file validi: `/^[A-Za-z0-9._-]{1,128}$/` senza `..`. I conti account su disco restano in memoria (una `Map` sulla `globalThis`), come oggi.
- [ ] **Step 5: Eseguire `npm test`** — Expected: PASS (440 di prima + i nuovi).
- [ ] **Step 6: Commit** — `git commit -m "Deposito: interfaccia unica e realizzazione su disco"`

### Task 2: I documenti JSON passano dal deposito

**Files:**
- Modify: `src/lib/archivio-azienda.ts`, `src/lib/archivio-file.ts`, `src/lib/abbonamento-server.ts`, `src/lib/collegamenti-server.ts`, `src/lib/collegamenti-file.ts`, `src/lib/ebay/archivio.ts`, `src/lib/piattaforma/richieste-file.ts` (solo il registro)

**Interfaces:**
- Consumes: `deposito()`, `DocumentoIlleggibile` (Task 1).
- Produces: le funzioni esportate oggi da questi file mantengono **nome, firma e comportamento** (`leggiStato`, `aggiornaStato`, `creaStatoAzienda`, `aggiungiEventi`, `leggiAbbonamento`, `aggiornaAbbonamento`, `leggiArchivio`, `aggiornaArchivio`, `elencoRichieste`, `aggiungiRichiesta`, e le letture/scritture dei collegamenti). `ArchivioIlleggibile` e `CollegamentiIlleggibili` restano esportate e diventano sottoclassi di `DocumentoIlleggibile` (chi fa `instanceof` continua a funzionare).

- [ ] **Step 1: Aggiungere a `disco.test.ts` un test** `archivio illeggibile → ArchivioIlleggibile`: scritto a mano un `state.json` non valido, `leggiStato(id)` lancia un errore `instanceof ArchivioIlleggibile` e il file resta com'era.
- [ ] **Step 2: Eseguire `npm test`** — Expected: FAIL sul nuovo test (oggi la classe non deriva da `DocumentoIlleggibile` o il percorso non passa dal deposito).
- [ ] **Step 3: Riscrivere i file elencati** come sottili strati sopra `deposito()`: `aggiornaStato(id, fn)` diventa `aggiornaDocumento<Stored, T>(id, "archivio", prima => { const r = fn(prima ?? VUOTO); return { dati: r.stored, risultato: r.risultato, nonScrivere: r.nonScrivere }; })` con `VUOTO` uguale al valore che oggi `leggiStatoDaFile` dà per file assente. Tolte le code locali (`blocchi`) ora duplicate dalla fila del deposito.
- [ ] **Step 4: Eseguire `npm test` e `npm run prova:accesso`** — Expected: PASS, nessuna asserzione dei test esistenti cambiata.
- [ ] **Step 5: Commit** — `git commit -m "Archivio, abbonamento, collegamenti, eBay e richieste passano dal deposito"`

### Task 3: I file binari passano dal deposito, limite di 3 MB

**Files:**
- Modify: `src/app/api/foto/route.ts`, `src/app/api/foto/[name]/route.ts`, `src/app/api/allegati/route.ts`, `src/app/api/allegati/[name]/route.ts`, `src/lib/visura-server.ts`, `src/lib/piattaforma/richieste-file.ts` (file), `src/lib/ebay/sandbox.ts` (lettura delle foto per eBay, riga ~474), `src/app/api/registrazione/route.ts` (annullamento: `togliAzienda` al posto di `rm`)
- Create: `src/lib/limiti-file.ts` + `src/lib/limiti-file.test.ts`

**Interfaces:**
- Consumes: `deposito().salvaFile/leggiFile/togliAzienda` (Task 1).
- Produces: `MAX_FILE_BYTES = 3 * 1024 * 1024` e `controllaDimensione(bytes: number): { ok: true } | { ok: false; messaggio: string }` in `limiti-file.ts`; messaggio esatto per il troppo grande: `"File più grande di 3 MB: riducilo e riprova."`

- [ ] **Step 1: Test in `limiti-file.test.ts`:** `controllaDimensione(0)` → `ok: false` con `"File vuoto."`; `controllaDimensione(3 * 1024 * 1024)` → `ok: true`; `controllaDimensione(3 * 1024 * 1024 + 1)` → `ok: false` con il messaggio dei 3 MB.
- [ ] **Step 2: Eseguire `npm test`** — Expected: FAIL.
- [ ] **Step 3: Scrivere `limiti-file.ts` e usarlo in `api/foto` e `api/allegati`** (413 con `{ error: messaggio }`), poi portare tutte le letture e scritture di file elencate sul deposito. Le route `[name]` rispondono 404 se `leggiFile` dà `null`, con le stesse intestazioni di oggi.
- [ ] **Step 4: Controllare che il gestionale comprima le foto sotto i 3 MB:** cercare dove il client prepara il `data:image/…;base64` (es. `grep -rn "toDataURL\|data:image" src/components src/lib`) e verificare dimensione massima e qualità; se una foto del telefono può superare 3 MB, abbassare lì la dimensione o la qualità.
- [ ] **Step 5: Eseguire `npm test` e `npx tsc --noEmit -p .`** — Expected: PASS, nessun errore nuovo.
- [ ] **Step 6: Verifica nel browser** su copia isolata (vedi memoria "prove su dati separati": clonare nella scratchpad, `DATI_DIR` nuova, porta libera): caricare una foto a un veicolo e un PDF a una pratica, ricaricare la pagina, vederli.
- [ ] **Step 7: Commit** — `git commit -m "Foto, allegati, visure e richieste passano dal deposito; limite 3 MB"`

### Task 4: Postgres per Better Auth, segreti dalle variabili, avvio in cloud

**Files:**
- Create: `src/lib/db/pool.ts`, `src/lib/db/schema.ts` (+ `schema.test.ts`), `src/lib/db/supabase-ca.crt`
- Modify: `src/lib/auth/server.ts`, `src/lib/auth/segreto.ts`, `src/lib/cifratura.ts`, `src/lib/accesso/avvio.ts`, `src/lib/server-data.ts` (solo commento: non più "unico punto da sostituire"), `package.json` (dipendenze `pg`, `@types/pg`)

**Interfaces:**
- Consumes: `sceltaDeposito` (Task 1).
- Produces:
  - `pool(): Pool` in `db/pool.ts` — un `pg.Pool` unico sulla `globalThis`, da `DATABASE_URL`, `max: 3`. TLS **sempre verificato** (mai `rejectUnauthorized: false`): `ssl: { ca }` con il certificato pubblico di Supabase salvato in `src/lib/db/supabase-ca.crt` (si scarica dal pannello, *Database Settings → SSL Configuration*; è pubblico e si può versionare). Senza TLS solo per `localhost`.
  - `SQL_SCHEMA: string[]` e `preparaSchema(p: Pool): Promise<void>` in `db/schema.ts`, idempotente:
    ```sql
    create table if not exists documento (azienda_id text not null, tipo text not null, dati jsonb, aggiornato timestamptz not null default now(), primary key (azienda_id, tipo));
    create table if not exists conto_account (chiave text primary key, stato jsonb not null, aggiornato timestamptz not null default now());
    alter table documento enable row level security;
    alter table conto_account enable row level security;
    ```
  - In modalità `supabase`: `auth/server.ts` usa `database: pool()` e `rateLimit.storage: "database"`; `segretoAccesso()` lancia `Error("BETTER_AUTH_SECRET mancante")` se la variabile non c'è (niente file); `cifratura.ts` prende la chiave da `CHIAVE_COLLEGAMENTI` (64 caratteri esadecimali) e lancia `Error("CHIAVE_COLLEGAMENTI mancante o non valida")` altrimenti.
  - In modalità `supabase` `avviaPiattaforma()` esegue le migrazioni di Better Auth, `preparaSchema`, il super admin dalle variabili; **non** crea l'azienda demo, non copia dati storici, non scrive file.

- [ ] **Step 1: Test in `schema.test.ts`:** ogni istruzione di `SQL_SCHEMA` contiene `if not exists` o è un `enable row level security`; le tabelle `documento` e `conto_account` compaiono entrambe con RLS.
- [ ] **Step 2: Eseguire `npm test`** — Expected: FAIL.
- [ ] **Step 3: Scrivere `db/pool.ts`, `db/schema.ts` e le modifiche elencate.** Leggere prima la documentazione di Better Auth installata su Postgres (`node_modules/better-auth/` — adattatore Kysely con `pg.Pool`) e verificare che `getMigrations` crei anche la tabella del limite delle richieste con `storage: "database"`.
- [ ] **Step 4: Eseguire `npm test` e `npx tsc --noEmit -p .`** — Expected: PASS (in locale si resta su disco e SQLite).
- [ ] **Step 5: Commit** — `git commit -m "Better Auth su Postgres e segreti dalle variabili quando il deposito è Supabase"`

### Task 5: Realizzazione Supabase del deposito

**Files:**
- Create: `src/lib/deposito/supabase.ts`, `src/lib/deposito/supabase.test.ts`
- Modify: `src/lib/deposito/index.ts`, `package.json` (dipendenza `@supabase/supabase-js`)

**Interfaces:**
- Consumes: `pool()`, `preparaSchema` (Task 4); `provaContratto` (Task 1).
- Produces: `creaDepositoSupabase(opz: { pool: Pool; url: string; chiave: string; bucket?: string }): Deposito`, con bucket di serie `"piazzale"` (privato, creato se manca alla prima scrittura).

- [ ] **Step 1: Scrivere `supabase.test.ts`** che chiama `provaContratto("supabase", …)` solo se ci sono `PROVA_DATABASE_URL`, `PROVA_SUPABASE_URL`, `PROVA_SUPABASE_KEY` (altrimenti `test.skip` con il motivo). Ogni esecuzione usa id azienda casuali e `pulisci` li toglie con `togliAzienda`.
- [ ] **Step 2: Eseguire `npm test`** — Expected: i test Supabase risultano saltati; con le variabili del progetto `Piazzale prove` (Task 7) falliscono perché `supabase.ts` non esiste.
- [ ] **Step 3: Scrivere `supabase.ts`.**
  - `aggiornaDocumento`: transazione `begin`; `insert into documento (azienda_id, tipo, dati) values ($1,$2,null) on conflict do nothing`; `select dati … for update`; `fn`; se non `nonScrivere`, `update … set dati=$3, aggiornato=now()`; `commit` (`rollback` su errore).
  - `creaDocumento`: `insert … on conflict do nothing returning 1`.
  - File in `<aziendaId>/<cartella>/<nome>` nel bucket con `upsert: !soloSeNuovo`; `leggiFile` dà `null` su "not found".
  - `togliAzienda`: `delete from documento where azienda_id=$1` più rimozione di tutti i file con prefisso `<aziendaId>/` (elenco paginato).
  - `aggiornaContoAccount`: stessa transazione su `conto_account`, con `inVolo` salvata come oggetto e riletta come `Map`.
  - Stessi controlli su id e nomi del disco (Task 1).
- [ ] **Step 4: Collegare `index.ts`:** con `sceltaDeposito(process.env) === "supabase"` → `creaDepositoSupabase({ pool: pool(), url: SUPABASE_URL, chiave: SUPABASE_SERVICE_ROLE_KEY })`.
- [ ] **Step 5: Eseguire `npm test` con le variabili `PROVA_*`** (dopo il Task 7, Step 1-2) — Expected: tutto il contratto PASS anche per Supabase, compresi i 20 aggiornamenti in parallelo.
- [ ] **Step 6: Commit** — `git commit -m "Deposito su Supabase: documenti in Postgres, file nello spazio privato"`

### Task 6: Tentativi di accesso contati nel deposito

**Files:**
- Modify: `src/lib/auth/tentativi-account.ts`
- Test: `src/lib/auth/tentativi-account.test.ts` (esistente: deve continuare a passare)

**Interfaces:**
- Consumes: `deposito().aggiornaContoAccount` (Task 1); `prenota`, `chiudi` puri da `src/lib/accesso/tentativi-account.ts` (invariati).
- Produces: comportamento invariato dell'hook; `stato.conti` sostituito da chiamate al deposito: in "before" `aggiornaContoAccount(k, s => { const m = new Map(s ? [[k, s]] : []); const r = prenota(m, k, gettone, ora); return { stato: m.get(k)!, risultato: r }; })`, in "after" lo stesso con `chiudi`. Il contatore comune delle email inesistenti resta in memoria per istanza (scelta del piano: protegge solo dalla raffica, il blocco vero è per account).

- [ ] **Step 1: Aggiungere un test** in `tentativi-account.test.ts`: 10 accessi sbagliati sullo stesso account, fatti in parallelo a gruppi di 5, portano al blocco (l'11° risponde `TOO_MANY_REQUESTS`), usando il deposito su disco.
- [ ] **Step 2: Eseguire `npm test`** — Expected: FAIL se il conteggio parallelo perde tentativi, altrimenti verificare che il test eserciti davvero il nuovo percorso (deve fallire prima della modifica).
- [ ] **Step 3: Modificare l'hook** come descritto in Interfaces.
- [ ] **Step 4: Eseguire `npm test`** — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "Tentativi di accesso per account contati nel deposito"`

### Task 7: Progetto di prova, variabili su Vercel e prova su un'anteprima

**Files:**
- Modify: `docs/ACCESSO.md` (tabella variabili: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`, `CHIAVE_COLLEGAMENTI`, `BETTER_AUTH_SECRET` obbligatoria in cloud), `docs/PAGAMENTI.md` (dove stanno ora `abbonamento` e i file)
- Create: `docs/SUPABASE.md` (progetti, cosa sta dove, come leggere le tabelle, limiti del piano gratuito e quando passare a Pro: primi clienti paganti o metà spazio)

- [ ] **Step 1: Creare il progetto `Piazzale prove`** nell'organizzazione gratuita `Piazzale`, dal pannello di Supabase nel browser integrato (Alessandro ha già fatto l'accesso): regione Europa, RLS automatica sulle nuove tabelle, accesso API automatico spento, password del database generata dal pannello.
- [ ] **Step 2: Chiedere ad Alessandro di copiare le chiavi** (chi costruisce non le legge e non le scrive): da ciascun progetto, in *Project Settings*, la stringa di connessione del pooler in modalità transazione (`DATABASE_URL`), l'URL del progetto (`SUPABASE_URL`) e la chiave `service_role` (`SUPABASE_SERVICE_ROLE_KEY`). Per `Piazzale prove`: nel `.env.local` della cartella di lavoro come `PROVA_DATABASE_URL`, `PROVA_SUPABASE_URL`, `PROVA_SUPABASE_KEY`, e su Vercel per l'ambiente **Preview**. Per `Piazzale`: su Vercel per l'ambiente **Production**. Più `BETTER_AUTH_SECRET` e `CHIAVE_COLLEGAMENTI` (generate con `openssl rand -hex 32`), diverse per Preview e Production.
- [ ] **Step 3: Eseguire `npm test` con le variabili `PROVA_*`** — Expected: contratto Supabase PASS (Task 5, Step 5).
- [ ] **Step 4: Spingere il ramo** `registrazione-pagamento` su GitHub (crea l'anteprima di Vercel) e attendere lo stato READY.
- [ ] **Step 5: Prova sull'anteprima** con il browser integrato: accesso del super admin, creazione di un'azienda dalla Piattaforma, un veicolo con una foto, un PDF in una pratica. Poi far ripartire l'anteprima (redeploy) e verificare che azienda, veicolo, foto e PDF ci siano ancora. Controllare con `read_network_requests` che nessuna richiesta del browser vada a `supabase.co`.
- [ ] **Step 6: Controllare nel pannello di Supabase** (`Piazzale prove`) che le tabelle `documento` e `conto_account` abbiano RLS attiva e che il bucket `piazzale` sia privato.
- [ ] **Step 7: Commit della documentazione** — `git commit -m "Documentazione: Supabase, variabili e progetti"`

Su `main` e sulla produzione non si tocca niente in questo piano: l'unione arriva alla fine del piano 3. La riga "spazio usato" nella Piattaforma (spec, "Limiti del piano gratuito") è nel piano 3.
