# Registrazione libera, prova di 15 giorni ed email — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chiunque si registra da `/registrati` senza codice invito, conferma l'email (mandata da Lostar Technology), usa il gestionale 15 giorni con tutti i moduli accesi; al 16° giorno il gestionale si blocca con il riquadro di pagamento a moduli.

**Architecture:** Le regole restano pure in `src/lib/abbonamento.ts` (stato `nuovo` + campo `fineProva`); la registrazione esistente (`api/registrazione`) perde l'invito e guadagna telefono, consensi e BotID; la conferma usa il meccanismo di verifica email di Better Auth con un nostro invio via Resend e un controllo all'accesso solo per i titolari non confermati; un lavoro pianificato giornaliero manda gli avvisi di fine prova.

**Tech Stack:** Next 16 (App Router, `cacheComponents`), Better Auth 1.7 (`emailVerification`), Resend (API HTTP), Vercel BotID (`botid`), Vercel Schedules, deposito del piano 1, test `node --test`.

**Spec:** `docs/superpowers/specs/2026-11-25-prova-15-giorni-supabase-design.md` — sezioni "Come funziona" 3 (registrazione libera) e 4 (prova di 15 giorni), "Decisioni di Alessandro del 25/11/2026" (Stripe di prova, email a nome di Lostar Technology, registrazioni su Supabase, consensi). I testi legali e il pulsante della landing sono nel piano 3; le foto sul dispositivo in un piano a parte.

## Global Constraints

- Leggere `node_modules/next/dist/docs/` prima di scrivere route o config (vedi `AGENTS.md`); niente `export const dynamic`.
- Prova: **15 giorni dalla conferma dell'email**, tutti i moduli accesi (`ORDINE_MODULI`). Al blocco: scritture rifiutate con 402, letture sì, eBay continua, negozio chiuso (come nel design del 22/11).
- Stripe solo con chiavi di prova ("soldi falsi"), come oggi.
- Mittente delle email: `Lostar Technology <noreply@lostartechnology.com>` (variabile `EMAIL_MITTENTE`); **nessuna parola "Supabase"** in email, pagine o link; i link puntano al gestionale.
- Piede di ogni email, testo esatto: `LOSTAR S.R.L.S. · Corso Massimo d'Azeglio 60, 10126 Torino (TO) · P. IVA e C.F. 13018890015 · REA TO-1333294` più il motivo ("Ricevi questa email perché ti sei registrato a Piazzale.") e il link all'informativa (`/privacy`, la pagina la scrive il piano 3). Versione testo semplice oltre all'HTML.
- Link di conferma valido **48 ore**, si può richiedere di nuovo da `/accesso`.
- Un'email già usata non registra una seconda azienda (messaggio generico di oggi).
- Consensi salvati con data e ora, indirizzo IP e versione dei testi (`VERSIONE_CONDIZIONI`, `VERSIONE_PRIVACY` come stringhe data, es. `"2026-11-26"`); il consenso commerciale è facoltativo e di serie **non** spuntato.
- Niente segreti nel browser, nei log o nelle risposte. Messaggi in italiano semplice.
- Gli accessi dei dipendenti creati dal titolare (email non verificata) devono continuare a entrare: il controllo della conferma vale **solo** per il titolare di un'azienda registrata con la prova non ancora partita.

## Review Focus

1. **Titolare che prova ad accedere prima di confermare:** messaggio chiaro con "rimanda l'email", mai un errore generico, mai un accesso. → test nel Task 5.
2. **Link di conferma aperto due volte, scaduto o su un altro dispositivo:** la prova parte una volta sola e la data di fine non si sposta. → test nel Task 5.
3. **Dipendenti e super admin:** continuano a entrare come oggi (nessun effetto del controllo di conferma). → test nel Task 5.
4. **Ultimo giorno di prova a cavallo della mezzanotte e con l'orologio di prova spostato:** il blocco scatta all'istante giusto, mai prima. → test nel Task 2.
5. **Email non partita** (Resend giù o chiave mancante): la registrazione non lascia un'azienda fantasma senza modo di confermarla; si può rimandare. → test nel Task 4/5.

---

### Task 1: Avvio con un tempo massimo

**Files:**
- Modify: `src/lib/accesso/pronta.ts`, `src/lib/accesso/avvio.ts`, `src/lib/db/schema.ts`
- Test: il test esistente di `riprovaAvvio` (stesso file di prova dove è oggi)

**Interfaces:**
- Produces: un tentativo di avvio che dura più di **60 s** conta come fallito (la richiesta riceve 503 e il prossimo tentativo segue la regola dei 30 s); le istruzioni di schema all'avvio in modalità supabase girano con `SET lock_timeout = '5s'` e `SET statement_timeout = '30s'` sulla connessione che le esegue.

- [ ] **Step 1: Test** `avvio appeso → fallito dopo 60 s`: con orologio e avvio finti (una promessa che non si risolve), dopo 60 s la richiesta in attesa ha la risposta di non pronto e un nuovo tentativo parte solo dopo altri 30 s.
- [ ] **Step 2: `npm test`** — Expected: FAIL.
- [ ] **Step 3: Implementare** la corsa tra avvio e timer in `pronta.ts` e i due `SET` prima di migrazioni/`preparaSchema`/`proteggiTabelle`.
- [ ] **Step 4: `npm test`** — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "Avvio: un tentativo appeso oltre 60 secondi conta come fallito"`

### Task 2: Prova di 15 giorni nelle regole pure

**Files:**
- Modify: `src/lib/abbonamento.ts`, `src/lib/abbonamento.test.ts`
- Modify (adeguare i chiamanti): `src/app/api/demo-state/route.ts`, `src/app/api/abbonamento/stato/route.ts`, `src/components/AppShell.tsx`, `src/components/FasciaAbbonamento.tsx`, `src/lib/negozio-server.ts`, `src/lib/moduli-server.ts`, `src/lib/stripe/server.ts`, `src/lib/abbonamento-server.prova.ts`
- Create: `src/lib/moduli-usati.ts` + `src/lib/moduli-usati.test.ts`

**Interfaces:**
- Produces in `abbonamento.ts`:
  - `Abbonamento` guadagna `fineProva: number | null` (ms; `null` = prova non partita) e `spostamentoProva: number` (ms, di serie 0; solo con chiavi di prova). `ABBONAMENTO_NUOVO(prova, ora)` li mette a `null` e `0`. Documenti salvati prima senza questi campi si leggono come `null`/`0`.
  - `export const GIORNI_PROVA = 15`
  - `export function avviaProva(a: Abbonamento, ora: number): Abbonamento` — se `a.stato === "nuovo"` e `fineProva === null` imposta `fineProva = ora + 15 giorni`; altrimenti restituisce `a` invariato.
  - `export function oraProva(a: Abbonamento, ora: number): number` = `ora + a.spostamentoProva`
  - `export function inProva(a: Abbonamento, ora: number): boolean` — `stato === "nuovo"` e `fineProva !== null` e `oraProva(a, ora) < fineProva`
  - `bloccato(a: Abbonamento, ora: number): boolean` (cambia firma: niente più veicoli) — vero se `scaduto`; oppure `stato === "nuovo"` e (`fineProva === null` oppure `oraProva(a, ora) >= fineProva`).
  - `moduliDaAbbonamento(a, ora)` — in prova tutti gli `ORDINE_MODULI`; `nuovo` fuori prova e `scaduto` solo magazzino; gli altri stati come oggi.
  - `scritturaAzienda(registrata, a, ora, corpo)` e `negozioAperto(registrata, a, ora)` e `statoPerBrowser(registrata, a, ora, stato)` usano `bloccato(a, ora)` / `moduliDaAbbonamento(a, ora)`; spariscono le regole "primo veicolo" (`veicoli.dopo > 1`). `contaVeicoli` resta solo se ancora usata altrove.
  - `contoAllaRovescia(a, ora)` in prova: `{ tono: giorni <= 3 ? "avviso" : "ok", testo: giorni === 0 ? "Prova gratuita: finisce oggi" : \`Prova gratuita: ${tra(giorni)} il gestionale si blocca\`, giorni }` con `giorni = Math.max(0, Math.ceil((fineProva - oraProva) / 86_400_000))`.
  - `fasciaDaMostrare(a, ora)` — vero anche per tutta la prova.
- Produces in `moduli-usati.ts`: `moduliUsati(state: Record<string, unknown> | null): Modulo[]` — sempre `magazzino`; `accettazione` se c'è almeno una pratica/dossier, `ambiente` se c'è almeno un formulario o una registrazione del registro rifiuti, `vendite` se c'è almeno una vendita al banco o un preventivo (leggere `src/lib/types.ts` e `src/lib/moduli.ts` per i nomi esatti dei campi dello stato).

- [ ] **Step 1: Test in `abbonamento.test.ts`:** `avviaProva` imposta `ora + 15*86_400_000` una volta sola (seconda chiamata invariata); `bloccato` è falso a `fineProva - 1` e vero a `fineProva` (anche con `spostamentoProva = 7 giorni` che porta oltre); `nuovo` con `fineProva === null` è bloccato; in prova `moduliDaAbbonamento` dà tutti e quattro i moduli; `contoAllaRovescia` dà "Prova gratuita: tra 3 giorni il gestionale si blocca" con tono `"avviso"` a 3 giorni e `"ok"` a 4; un documento senza `fineProva` letto come `null`. Test in `moduli-usati.test.ts` per i quattro casi.
- [ ] **Step 2: `npm test`** — Expected: FAIL.
- [ ] **Step 3: Implementare** e adeguare i chiamanti (ogni chiamata di `bloccato`/`negozioAperto`/`scritturaAzienda`/`statoPerBrowser`/`moduliDaAbbonamento` passa `Date.now()`); aggiornare i test esistenti che provavano la regola del primo veicolo dicendolo nel resoconto (il cambio di regola è voluto dallo spec).
- [ ] **Step 4: `npm test`, `npm run prova:accesso`, `npx tsc --noEmit -p .`** — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "Prova di 15 giorni con tutti i moduli al posto del blocco al primo veicolo"`

### Task 3: Registrazione libera, telefono, consensi, BotID

**Files:**
- Modify: `src/lib/accesso/registrazione.ts` (+ test), `src/app/api/registrazione/route.ts`, `src/app/registrati/view.tsx`, `src/app/registrati/page.tsx`, `src/lib/deposito/tipi.ts`, `src/lib/deposito/disco.ts`, `src/lib/deposito/supabase.ts` (nuovo tipo di documento), `package.json` (`botid`), `next.config.ts` (se BotID lo richiede), `src/app/accesso/view.tsx` (link "Non hai un account? Registrati gratis")
- Create: `src/lib/consensi.ts` (+ test)

**Interfaces:**
- Produces:
  - `TipoDocumento` guadagna `"registrazione"` (su disco `aziende/<id>/registrazione.json`, permessi `0o600`).
  - `DatiRegistrazione = { azienda; nome; email; password; telefono: string | null; condizioni: true; commerciale: boolean }` — niente `invito`. Telefono facoltativo: se presente, solo cifre, spazi, `+`, da 6 a 20 caratteri, altrimenti errore `"Scrivi un numero di telefono valido o lascia vuoto."`.
  - In `consensi.ts`: `VERSIONE_CONDIZIONI = "2026-11-26"`, `VERSIONE_PRIVACY = "2026-11-26"`, `type Consenso = { versione: string; ora: string /* ISO */; ip: string | null }`, `type SchedaRegistrazione = { titolare: string; email: string; telefono: string | null; azienda: string; registrata: string; confermata: string | null; condizioni: Consenso; privacy: Consenso; commerciale: Consenso | null }`, `schedaRegistrazione(d: DatiRegistrazione, ip: string | null, ora: number): SchedaRegistrazione`.
  - La route: niente invito; BotID (`checkBotId()` dal pacchetto `botid`, client con `initBotId` per il percorso `/api/registrazione`: leggere la documentazione del pacchetto installato) → se robot 403 `"Registrazione non riuscita."`; scrive `registrazione` con `creaDocumento`; abbonamento `ABBONAMENTO_NUOVO` con `fineProva: null`; **non** fa entrare il titolare (entra dopo la conferma, Task 5) e risponde `{ ok: true, conferma: true }`.
  - Il modulo: campi azienda, nome e cognome, email, telefono (facoltativo), password; casella obbligatoria "Accetto le condizioni del servizio e l'accordo sul trattamento dei dati" (link `/condizioni`); frase "Ho letto l'informativa privacy" (link `/privacy`); casella facoltativa non spuntata "Acconsento a essere contattato da Lostar Technology per proposte commerciali su Piazzale". Dopo l'invio: "Controlla la posta: ti abbiamo mandato il link per attivare la prova."

- [ ] **Step 1: Test** in `registrazione.test.ts` (o il file di test esistente): registrazione senza `invito` valida; telefono vuoto → `null`; telefono `"abc"` → l'errore esatto; `commerciale` assente → `false`. In `consensi.test.ts`: `schedaRegistrazione` con commerciale `false` → `commerciale: null`; versioni e IP riportati.
- [ ] **Step 2: `npm test`** — Expected: FAIL.
- [ ] **Step 3: Implementare.** I codici invito e la pagina Inviti restano nel codice ma non servono più.
- [ ] **Step 4: `npm test`, `npx tsc --noEmit -p .`, eslint** — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "Registrazione libera: niente invito, telefono, consensi salvati, controllo dei robot"`

### Task 4: Invio delle email a nome di Lostar Technology

**Files:**
- Create: `src/lib/email/invia.ts`, `src/lib/email/modelli.ts`, `src/lib/email/modelli.test.ts`
- Modify: `src/lib/config.ts` (dati legali di `PRODUTTORE`), `src/lib/auth/server.ts` (`baseURL`)

**Interfaces:**
- Produces:
  - `PRODUTTORE` in `config.ts` guadagna `ragioneSociale: "LOSTAR S.R.L.S."`, `sede: "Corso Massimo d'Azeglio 60, 10126 Torino (TO)"`, `piva: "13018890015"`, `rea: "TO-1333294"`, `pec: "gustipreziosisrls@pec.cgn.it"`.
  - `type Email = { a: string; oggetto: string; testo: string; html: string }`
  - `inviaEmail(e: Email): Promise<void>` — con `RESEND_API_KEY` chiama `POST https://api.resend.com/emails` (fetch, niente SDK) con `from: process.env.EMAIL_MITTENTE`; errore HTTP → lancia `Error("Email non inviata")` (il dettaglio solo nel log, senza chiave). Senza chiave: fuori produzione scrive nel log del server `"[email] a <indirizzo>: <oggetto>"` e il testo (serve alle prove in locale); in produzione lancia `Error("Invio email non configurato")`.
  - In `modelli.ts`: `emailConferma(nome: string, link: string): Email`, `emailProvaInScadenza(nome: string, giorni: number, link: string): Email`, `emailProvaFinita(nome: string, link: string): Email` — oggetto, saluto, un pulsante/link, il piede esatto dei Global Constraints, versione testo e HTML semplice (tabelle e stili in linea, nessuna immagine esterna).
  - `auth/server.ts`: `baseURL` = `process.env.BETTER_AUTH_URL` se c'è, altrimenti su Vercel `https://${VERCEL_BRANCH_URL ?? VERCEL_URL}`, altrimenti quello di oggi (dedotto dalla richiesta). Toglie l'avviso "Base URL is not set" online.

- [ ] **Step 1: Test in `modelli.test.ts`:** ogni modello contiene il link, il piede esatto (ragione sociale, sede, P. IVA, REA), il motivo e `/privacy` sia in `testo` sia in `html`; nessuno contiene "supabase" (maiuscole e minuscole); l'HTML scappa i caratteri di `nome` (`<` → `&lt;`). Test di `inviaEmail` con `fetch` finto: corpo e intestazione `Authorization: Bearer …` giusti; senza chiave fuori produzione non chiama `fetch`.
- [ ] **Step 2: `npm test`** — Expected: FAIL.
- [ ] **Step 3: Implementare.**
- [ ] **Step 4: `npm test`, `npx tsc --noEmit -p .`** — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "Email a nome di Lostar Technology con i dati di legge"`

### Task 5: Conferma dell'email e partenza della prova

**Files:**
- Modify: `src/lib/auth/server.ts` (`emailVerification`), `src/lib/auth/percorsi-auth.ts` (+ test), `src/app/accesso/view.tsx`, `src/app/accesso/page.tsx`, `src/app/api/registrazione/route.ts`
- Create: `src/lib/auth/conferma-titolare.ts` (plugin o hook) + prova in `src/lib/accesso/server.prova.ts`

**Interfaces:**
- Consumes: `avviaProva` (Task 2), `emailConferma` / `inviaEmail` (Task 4), documento `registrazione` (Task 3).
- Produces:
  - Better Auth `emailVerification: { sendVerificationEmail: ({ user, url }) => inviaEmail(emailConferma(user.name, url)), expiresIn: 48 * 3600, autoSignInAfterVerification: true, afterEmailVerification }` (verificare i nomi esatti nella versione installata in `node_modules/better-auth`). **Non** usare `requireEmailVerification` (bloccherebbe i dipendenti).
  - `afterEmailVerification(user)`: per ogni azienda registrata di cui l'utente è `responsabile` con abbonamento `nuovo` e `fineProva === null`: `aggiornaAbbonamento(id, a => avviaProva(a, Date.now()))`, scrive `confermata` nella scheda `registrazione`, voce di registro "Email confermata: prova di 15 giorni iniziata".
  - La route di registrazione, dopo aver creato tutto, chiama `auth.api.sendVerificationEmail({ body: { email, callbackURL: "/" } })`; se l'invio fallisce la registrazione **resta** (l'utente può rimandare) e risponde `{ ok: true, conferma: true, inviata: false }`.
  - Hook "before" su `/sign-in/email`: se l'utente ha `emailVerified === false` ed è `responsabile` di un'azienda registrata con abbonamento `nuovo` e `fineProva === null` → `APIError("FORBIDDEN", { message: "Conferma prima la tua email: ti abbiamo mandato un link. Non lo trovi? Rimandalo da qui.", code: "EMAIL_DA_CONFERMARE" })`. Nessun altro utente è toccato.
  - `percorsi-auth.ts`: permessi `POST /send-verification-email` e `GET /verify-email`.
  - `/accesso`: con codice `EMAIL_DA_CONFERMARE` mostra il messaggio e il pulsante "Rimanda l'email" (chiama `send-verification-email` con l'email scritta); con `?confermata=1` mostra "Email confermata: la prova di 15 giorni è iniziata." Il limite di Better Auth sulle richieste vale anche per il rimando.

- [ ] **Step 1: Prove in `server.prova.ts`** (database e deposito di prova come gli altri casi del file): titolare registrato non confermato → l'accesso risponde 403 con `EMAIL_DA_CONFERMARE`; dopo la verifica (chiamata dell'endpoint con il token preso dall'email finta catturata da `inviaEmail` in modalità senza chiave) → l'abbonamento ha `fineProva` = ora + 15 giorni (tolleranza 5 s) e l'accesso riesce; seconda apertura dello stesso link non sposta `fineProva`; un dipendente con email non verificata creato da `creaMembro` entra; il super admin entra come oggi.
- [ ] **Step 2: `npm run prova:accesso`** — Expected: FAIL.
- [ ] **Step 3: Implementare.**
- [ ] **Step 4: `npm test`, `npm run prova:accesso`, `npx tsc --noEmit -p .`** — Expected: PASS.
- [ ] **Step 5: Prova in locale nel browser** (copia isolata, `DATI_DIR` nuova, porta libera; vedi memoria "prove su dati separati"): registrazione → link nel log del server → apertura → si entra su "Oggi" con la fascia "Prova gratuita: tra 15 giorni…".
- [ ] **Step 6: Commit** — `git commit -m "Conferma dell'email: la prova parte al click e il titolare entra solo dopo"`

### Task 6: Riquadro di pagamento, fascia e strumenti di prova

**Files:**
- Modify: `src/components/RiquadroPagamento.tsx`, `src/components/FasciaAbbonamento.tsx`, `src/components/StrumentiProva.tsx`, `src/lib/use-abbonamento.ts`
- Create: `src/app/api/abbonamento/prova/sposta/route.ts` (+ prova nel file di prova dell'abbonamento)

**Interfaces:**
- Consumes: `moduliUsati`, `contoAllaRovescia`, `inProva`, `oraProva` (Task 2).
- Produces:
  - `RiquadroPagamento` al blocco di fine prova parte con spuntati `moduliUsati(stato)` (magazzino sempre, non si toglie); il cliente può togliere o aggiungere gli altri.
  - `FasciaAbbonamento` mostra la riga di `contoAllaRovescia` in prova con il pulsante "Scegli i moduli" verso la pagina Abbonamento; tono `"avviso"` più evidente negli ultimi 3 giorni.
  - `POST /api/abbonamento/prova/sposta` con `{ passo: "giorno" | "settimana" }`: solo chiavi di prova, solo titolare con sessione email e password (stessa regola degli altri strumenti di prova, 403 altrimenti), solo in stato `nuovo` con prova partita; aggiunge 1 o 7 giorni a `spostamentoProva`; risponde con l'abbonamento aggiornato.
  - `StrumentiProva` durante la prova mostra "+1 giorno" e "+1 settimana" che chiamano questa route; dopo il pagamento restano gli strumenti di oggi sull'orologio di Stripe.

- [ ] **Step 1: Prove:** `sposta` con chiave live → 403; con sessione PIN → 403; `"settimana"` tre volte dopo la conferma → `bloccato` vero (15 giorni superati con 21); stato attivo → 409.
- [ ] **Step 2: `npm test` / `npm run prova:accesso`** — Expected: FAIL.
- [ ] **Step 3: Implementare.**
- [ ] **Step 4: Eseguire i test e `npx tsc --noEmit -p .`** — Expected: PASS.
- [ ] **Step 5: Prova in locale nel browser** (copia isolata): fascia di prova visibile; tre volte "+1 settimana" → riquadro di pagamento a tutto schermo con i moduli usati già spuntati.
- [ ] **Step 6: Commit** — `git commit -m "Fascia della prova, riquadro con i moduli usati e strumenti per far scorrere la prova"`

### Task 7: Avvisi di fine prova ogni giorno

**Files:**
- Create: `src/app/api/pianificato/prova/route.ts`, `src/lib/avvisi-prova.ts` (+ test)
- Modify: `vercel.json` o `vercel.ts` (pianificazione giornaliera; leggere la skill `vercel:vercel-schedules`), `src/lib/abbonamento.ts` (campo `avvisi`)

**Interfaces:**
- Produces:
  - `Abbonamento` guadagna `avvisi: { scadenza?: string; finita?: string }` (date ISO dell'invio; di serie `{}`).
  - `avvisoDaMandare(a: Abbonamento, ora: number): "scadenza" | "finita" | null` — `"scadenza"` se in prova con 3 giorni o meno e `avvisi.scadenza` assente; `"finita"` se `nuovo`, prova partita e finita e `avvisi.finita` assente; altrimenti `null`.
  - La route (una volta al giorno alle 9:00 ora di Roma; protetta da `CRON_SECRET` o dal meccanismo di Vercel Schedules, 401 altrimenti) scorre le aziende registrate, manda l'email giusta al titolare (`emailProvaInScadenza` / `emailProvaFinita`, link alla pagina Abbonamento) e segna `avvisi` dentro `aggiornaAbbonamento` **prima** di inviare, così due esecuzioni insieme non mandano due email.

- [ ] **Step 1: Test** di `avvisoDaMandare` per i casi: prova a 4 giorni → `null`; a 3 → `"scadenza"`; già mandato → `null`; prova finita → `"finita"`; pagato → `null`. Prova della route con 401 senza segreto.
- [ ] **Step 2–4: FAIL → implementare → PASS** (`npm test`, `npx tsc --noEmit -p .`).
- [ ] **Step 5: Commit** — `git commit -m "Avvisi di fine prova: tre giorni prima e alla fine, una volta sola"`

### Task 8: Vista `registrazioni` per il pannello di Supabase

**Files:**
- Modify: `src/lib/db/schema.ts` (+ test), `docs/SUPABASE.md`

**Interfaces:**
- Produces: in modalità supabase, `create or replace view registrazioni with (security_invoker = true) as …` con colonne `azienda`, `titolare`, `email`, `telefono`, `registrata`, `confermata`, `fine_prova`, `giorni_rimasti`, `stato`, `moduli_pagati`, `consenso_commerciale`, costruita da `organization`, `documento` (tipi `registrazione` e `abbonamento`, campi jsonb). `proteggiTabelle` copre anche le viste (`relkind in ('r','v')`): nessun privilegio per `anon`/`authenticated`.

- [ ] **Step 1: Test** del SQL della vista (contiene `security_invoker`, tutte le colonne) e di `proteggiTabelle` con una vista nell'elenco.
- [ ] **Step 2–4: FAIL → implementare → PASS.** Poi eseguire `preparaSchema` sul progetto "Piazzale prove" con le variabili `PROVA_*` di `.env.local` (senza stamparle) e controllare che `select * from registrazioni` funzioni con la connessione del server e che `anon` non possa leggerla.
- [ ] **Step 5: Commit** — `git commit -m "Vista registrazioni per guardare le prove dal pannello di Supabase"`

### Task 9: Prova completa sull'anteprima di Vercel

**Files:**
- Modify: `docs/PAGAMENTI.md` (prova di 15 giorni al posto del primo veicolo), `docs/SUPABASE.md` (variabili nuove)

- [ ] **Step 1: Variabili delle anteprime del ramo** (solo Preview, ramo `registrazione-pagamento`): `RESEND_API_KEY` e `EMAIL_MITTENTE` (Alessandro: chiave del suo account Resend; il dominio `lostartechnology.com` deve risultare verificato per l'invio), `BETTER_AUTH_URL` non serve (si usa `VERCEL_BRANCH_URL`), `CRON_SECRET` generato, `STRIPE_SECRET_KEY` di prova se Alessandro la fornisce. Valori copiati con comandi che non li mostrano.
- [ ] **Step 2: Spingere il ramo** e attendere l'anteprima READY.
- [ ] **Step 3: Prova nel browser integrato** con un'email vera di Alessandro (la sceglie lui): registrazione → email arrivata da Lostar Technology, senza la parola Supabase, con il piede di legge → link → si entra con la fascia di prova → un veicolo con una foto → nuovo deploy (redeploy) → veicolo e foto ancora lì → "+1 settimana" tre volte → riquadro di pagamento con i moduli usati spuntati. Con la chiave Stripe di prova: pagamento con la 4242 → gestionale sbloccato.
- [ ] **Step 4: Controllare** nella vista `registrazioni` di "Piazzale prove" la riga della prova.
- [ ] **Step 5: Commit della documentazione** — `git commit -m "Documentazione: prova di 15 giorni, email e variabili nuove"`

## Decisioni prese durante il lavoro

- La prova è lo stato «nuovo» con il campo `fineProva` (niente stato «prova» nuovo): meno cambi nella lettura da Stripe.
- Niente `requireEmailVerification` di Better Auth: i dipendenti creati dal titolare hanno l'email non verificata. Si ferma solo il titolare con la prova non partita.
- La conferma chiede la password scelta alla registrazione (pagina `/conferma`, `POST /api/conferma`); `/api/auth/verify-email` non è raggiungibile dal browser. Così né chi rifà una registrazione in sospeso né chi registra con l'email di altri può far confermare il proprio account al vero titolare.
- Una registrazione mai confermata con la stessa email si sostituisce (azienda, utente e documenti tolti), solo se l'utente non ha confermato, non è super admin ed è l'unico membro di aziende tutte in attesa. Resta accettato che il vero proprietario possa confermare una registrazione fatta da altri con la sua email (l'email dice di ignorarla).
- BotID solo su Vercel; in produzione fuori da Vercel si rifiuta salvo `PIAZZALE_SENZA_BOTID=1` (solo negli script di prova e di presentazione). Limite di 3 registrazioni all'ora per indirizzo, contato dopo il controllo dei campi.
- Telefono facoltativo, ma con almeno 6 cifre.
- `moduliUsati` conta solo l'uso vero di un modulo: il carico d'ingresso automatico (*T) e la pratica «da registrare» non spuntano Ambiente o Accettazione.
- Durante la prova la pagina Abbonamento mostra già «Scegli i moduli» con il pagamento.
- Avvisi di fine prova: il segno si mette prima dell'invio (meglio un avviso perso che uno al giorno).
- Vista `registrazioni`: giorni rimasti mai sotto 0; si ricrea a ogni avvio dentro un savepoint.
- Avvio: una sola istanza alla volta prepara il database (`pg_advisory_xact_lock`), dopo il «tuple concurrently deleted» visto sull'anteprima.
- Email di conferma (revisione finale): nessun testo scritto da chi registra; al massimo 5 in 24 ore e una al minuto per email, con il conto che passa alla registrazione che sostituisce; un invio fallito non conta; nome del titolare senza numeri, indirizzi o punti tra parole.

## Cose rimandate

- Prima delle chiavi Stripe vere: un abbonamento con `prova: true` pagato con la carta di prova resterebbe attivo per sempre, e `spostamentoProva` conterebbe ancora (vedi `docs/PAGAMENTI.md`). Finché non c'è la regola, in produzione nessuna chiave Stripe.
- Un'azienda in prova mai pagante con abbonamento `incomplete_expired`/`canceled` va a «scaduto» e perde la prova (da rivedere con i pagamenti veri, per esempio SEPA).
- Nessun recupero di `fineProva` per aziende registrate prima del piano: online non ce ne sono; in locale risultano in attesa e chi si registra con quella email le sostituisce.
- `runMigrations` di Better Auth fuori dal lock e senza `lock_timeout`.
- Il blocco a fine prova si decide nel browser con l'ora del dispositivo (un tablet con l'orologio avanti si blocca prima): far restituire `bloccato` o l'ora dal server.
- Sul sito vero, con un dominio, l'indirizzo `<progetto>.vercel.app` non è tra le origini fidate: impostare `BETTER_AUTH_URL` e `INDIRIZZO_GESTIONALE`.
- La vista `registrazioni` si elimina e ricrea a ogni avvio (si potrebbe confrontare prima la definizione).
- Avvisi di fine prova: `findMany` senza limite, giro in sequenza senza `maxDuration`.
- Gli strumenti di prova restano visibili a prova finita (voluto); 409 «La prova gratuita non è in corso» con chiavi scambiate.
- Errore all'avvio della prova al click → JSON 500 di Better Auth; due conferme insieme possono togliere la sessione appena aperta; doppio controllo della password per un titolare in attesa; utente sostituito tra il controllo e la verifica → 500 invece di 400.
- `/registrati` mostra «Rimanda l'email» anche quando l'invio è riuscito; meta charset e title nell'HTML delle email.
- Fuori da Vercel l'unica difesa dai robot è il limite per indirizzo, che è in memoria per istanza.
- Da ricontrollare in produzione: sull'anteprima il pulsante dell'email ha aperto `/conferma` senza il codice (probabile protezione di Vercel in un altro browser); l'indirizzo copiato funzionava.
- Conto delle email di conferma per email in un posto suo (oggi sta sulla scheda e passa alla registrazione che sostituisce; una sostituzione fallita a metà lo azzera). Ogni registrazione costa BotID e il limite per indirizzo.
- Chi conosce un'email può esaurire le 5 email di conferma del giorno: il vero proprietario aspetta il giorno dopo (accettato).
