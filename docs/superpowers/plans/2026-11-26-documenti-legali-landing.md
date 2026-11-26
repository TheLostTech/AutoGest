# Documenti legali di Piazzale e «Registrati gratis» — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Le pagine pubbliche `/privacy` e `/condizioni` (con l'accordo sul trattamento dei dati in allegato) hanno i testi veri a nome di LOSTAR S.R.L.S., e la landing porta a `/registrati` con «Registrati gratis» al posto di «Apri la demo».

**Architecture:** I testi stanno come dati puri in `src/lib/legale/` (sezioni con titolo e paragrafi, costruite da `PRODUTTORE`, `LISTINO`, `COMMISSIONE_ONLINE`, `GIORNI_PROVA` e dalle versioni di `consensi.ts`), così i test controllano che ci sia tutto quello che la legge chiede; un solo componente li mostra nelle due pagine. La landing cambia solo costanti, testi e link.

**Tech Stack:** Next 16 (App Router, `cacheComponents`, pagine statiche), Tailwind, test `node --test`.

**Spec:** `docs/superpowers/specs/2026-11-25-prova-15-giorni-supabase-design.md` — sezioni «Privacy e documenti a norma, sotto Lostar Technology» e «5. Landing e accesso». Modello di forma: l'informativa del sito Lostar (`https://lostartechnology.com/privacy`, aggiornata il 30/09/2026: titolare, dati, finalità e basi, conservazione, destinatari, diritti, cookie, modifiche).

## Global Constraints

- Leggere `node_modules/next/dist/docs/` prima di scrivere pagine o metadata (vedi `AGENTS.md`); niente `export const dynamic`.
- Titolare e fornitore: **LOSTAR S.R.L.S.**, Corso Massimo d'Azeglio 60, 10126 Torino (TO), P. IVA e C.F. 13018890015, REA TO-1333294; richieste privacy alla PEC `gustipreziosisrls@pec.cgn.it`. Sempre da `PRODUTTORE` in `src/lib/config.ts`, mai riscritti a mano.
- Fornitori nominati (decisione di Alessandro del 26/11/2026: **per nome**): Vercel (hosting e funzioni, Stati Uniti, BotID), Supabase (database e spazio file, server nell'Unione europea, Francoforte), Stripe (pagamenti), Resend (invio email), eBay (solo se l'azienda collega il suo account). **Supabase compare solo in questo elenco** di `/privacy` e dell'accordo: mai in email, link o altre pagine.
- Il servizio è **tra imprese** (autodemolizioni), non per consumatori. Legge italiana, **foro di Torino**.
- Prova gratuita: `GIORNI_PROVA` (15) giorni dalla conferma dell'email, senza carta; alla fine il gestionale si blocca e i dati restano. Abbonamento a moduli mensile o annuale (prezzi da `LISTINO`, IVA esclusa), commissione `COMMISSIONE_ONLINE` (8%) sui pezzi venduti online, niente al banco.
- Solo cookie tecnici (sessione, dispositivo): **niente banner**, una sezione nell'informativa.
- Versioni dei testi: `VERSIONE_CONDIZIONI` e `VERSIONE_PRIVACY` in `src/lib/consensi.ts` sono la data (formato `AAAA-MM-GG`) del giorno in cui si fanno i Task 1 e 2; i consensi dati finora sui segnaposto sono solo prove su «Piazzale prove» (in produzione non c'è nessuna registrazione), quindi se è ancora il 26/11/2026 restano `"2026-11-26"`. Ogni pagina mostra «Versione del …» presa da lì.
- In cima a entrambe le pagine, finché un consulente non li ha riletti, nessun avviso pubblico: la rilettura è un passo prima di aprire la registrazione al pubblico (si scrive nel piano, non nelle pagine).
- Testi in italiano semplice, frasi brevi, niente «ivi», «suddetto», «ai sensi del medesimo».

## Review Focus

1. **Versione mostrata diversa da quella salvata con il consenso:** la pagina deve mostrare esattamente `VERSIONE_*` di `consensi.ts`. → test nel Task 1.
2. **Prezzi o commissione cambiati nel listino:** le condizioni li prendono dal codice, mai scritti a mano. → test nel Task 2.
3. **Link «condizioni» e «informativa» dal modulo di registrazione, dalle email e dai piedi:** portano a pagine che esistono e si aprono senza accesso. → verifica nel Task 3.
4. **Telefono stretto (375 px):** le pagine legali si leggono senza scorrere di lato; i pulsanti della landing non vanno a capo male. → verifica nel Task 3.
5. **«Supabase» fuori dall'elenco dei fornitori:** nessuna altra occorrenza nei testi. → test nel Task 1.

---

### Task 1: Informativa privacy (`/privacy`)

**Files:**
- Create: `src/lib/legale/comune.ts`, `src/lib/legale/privacy.ts`, `src/lib/legale/legale.test.ts`
- Create: `src/components/sito/DocumentoLegale.tsx`, `src/app/privacy/page.tsx`
- Modify: `src/lib/consensi.ts` (nuove versioni, vedi Global Constraints), `package.json` (aggiungere `src/lib/legale/*.test.ts` allo script `test`)

**Interfaces:**
- Produces in `comune.ts`:
  - `type Sezione = { id: string; titolo: string; paragrafi: string[]; elenco?: string[] }`
  - `type Documento = { titolo: string; versione: string; sezioni: Sezione[] }`
  - `type Fornitore = { nome: string; cosa: string; dove: string; garanzia: string; soloSe?: string }`
  - `FORNITORI: Fornitore[]` — Vercel, Supabase, Stripe, Resend, eBay (eBay con `soloSe: "l'azienda collega il suo account eBay"`); `garanzia` per chi tratta fuori UE: «decisione di adeguatezza (EU-US Data Privacy Framework) o clausole contrattuali standard, artt. 44 e seguenti del GDPR».
  - `dataVersione(v: string): string` — `"2026-11-27"` → `"27 novembre 2026"` (fuso Europe/Rome non serve: è una data senza ora).
- Produces in `privacy.ts`: `INFORMATIVA_PRIVACY: Documento` con le sezioni (id): `titolare`, `dati`, `finalita`, `conservazione`, `fornitori`, `trasferimenti`, `diritti`, `cookie`, `modifiche`.
- Produces in `DocumentoLegale.tsx`: `DocumentoLegale({ documento }: { documento: Documento })` — server component: titolo, «Versione del …», indice con ancore `#id`, sezioni; usa `Testata` e `Piede` di `Sito.tsx`.

Contenuto (scelte mie, da far rileggere):
- **Dati:** del titolare che si registra (nome, email, telefono facoltativo, azienda, password solo come impronta), dei dipendenti che accedono (nome, email o PIN, ruoli), dati tecnici (indirizzo IP, dispositivo, registro attività), consensi con data, ora, IP e versione. I dati che l'autodemolizione inserisce sui suoi clienti e veicoli li tratta come **responsabile** (rimando all'accordo in `/condizioni#accordo`).
- **Finalità e basi:** account, prova e abbonamento → contratto e misure precontrattuali (art. 6.1.b); fatture → obbligo di legge (art. 6.1.c); sicurezza, blocco tentativi, BotID → legittimo interesse (art. 6.1.f); proposte commerciali di Lostar su Piazzale → **consenso** (art. 6.1.a), facoltativo, revocabile in ogni momento scrivendo alla PEC. Le email della prova (conferma, scadenza, fine) sono di servizio.
- **Conservazione:** account e dati dell'azienda per tutto il contratto; registrazioni mai confermate e prove finite senza abbonamento **fino a 12 mesi**, poi cancellate; dati di fatturazione e prova dei consensi **10 anni**; contatti commerciali fino alla revoca e comunque non oltre 24 mesi dall'ultimo contatto; log tecnici del fornitore per pochi giorni.
- **Cookie:** solo tecnici (sessione dell'accesso, identificativo del dispositivo, preferenze), nessun cookie pubblicitario o analitico, niente banner; BotID di Vercel analizza segnali tecnici del browser solo sul modulo di registrazione.
- **Diritti:** artt. 15-22, revoca del consenso, reclamo al Garante per la protezione dei dati personali (garanteprivacy.it).

- [ ] **Step 1: Test** in `legale.test.ts`:
  - `INFORMATIVA_PRIVACY.versione === VERSIONE_PRIVACY`; `VERSIONE_PRIVACY` e `VERSIONE_CONDIZIONI` hanno la forma `AAAA-MM-GG`; `dataVersione("2026-11-27") === "27 novembre 2026"`, `dataVersione("2027-01-05") === "5 gennaio 2027"`.
  - Gli id delle sezioni sono, in ordine, `["titolare","dati","finalita","conservazione","fornitori","trasferimenti","diritti","cookie","modifiche"]`.
  - Il testo completo (titoli, paragrafi, elenchi uniti) contiene `PRODUTTORE.ragioneSociale`, `PRODUTTORE.piva`, `PRODUTTORE.pec`, «Garante», «consenso», «12 mesi», «10 anni», «BotID», ognuno dei nomi di `FORNITORI`.
  - «Supabase» (senza distinguere maiuscole) compare solo dentro la sezione `fornitori`; nessun testo contiene `supabase.co`.
- [ ] **Step 2: `npm test`** — Expected: FAIL (moduli mancanti).
- [ ] **Step 3: Implementare** `comune.ts`, `privacy.ts`, le versioni in `consensi.ts`, `DocumentoLegale.tsx` e `src/app/privacy/page.tsx` (metadata: titolo «Informativa privacy · Piazzale», indicizzabile; `/privacy` è già tra i percorsi pubblici).
- [ ] **Step 4: `npm test`** — Expected: PASS. **`npx tsc --noEmit -p .`** — nessun errore.
- [ ] **Step 5: Commit** — `git commit -m "Informativa privacy di Piazzale a nome di LOSTAR S.R.L.S."`

### Task 2: Condizioni del servizio e accordo sul trattamento (`/condizioni`)

**Files:**
- Create: `src/lib/legale/condizioni.ts`
- Modify: `src/lib/legale/legale.test.ts`, `src/app/condizioni/page.tsx` (al posto del segnaposto)

**Interfaces:**
- Consumes: `Documento`, `Sezione`, `FORNITORI`, `DocumentoLegale` (Task 1); `LISTINO`, `euro`, `COMMISSIONE_ONLINE` da `src/lib/listino.ts`; `GIORNI_PROVA` da `src/lib/abbonamento.ts`.
- Produces: `CONDIZIONI: Documento` con le sezioni (id): `parti`, `servizio`, `prova`, `abbonamento`, `commissione`, `disdetta`, `dati`, `responsabilita`, `modifiche`, `legge`, e in fondo l'allegato `accordo` (titolo «Allegato: accordo sul trattamento dei dati per conto del cliente (art. 28 GDPR)»).

Contenuto (scelte mie, da far rileggere):
- **Parti:** LOSTAR S.R.L.S. e l'impresa che si registra; il servizio è per autodemolizioni e altre imprese, **non per consumatori** (non si applica il Codice del consumo).
- **Prova:** `GIORNI_PROVA` giorni dalla conferma dell'email, tutti i moduli, senza carta; alla fine il gestionale si blocca in scrittura, i dati restano e si riapre pagando; nessun addebito automatico.
- **Abbonamento:** per moduli; Magazzino sempre incluso; prezzi mensili e annuali presi da `LISTINO` con `euro(...)`, **IVA esclusa**; pagamento con carta su Stripe, rinnovo automatico alla fine di ogni periodo.
- **Commissione:** `COMMISSIONE_ONLINE` (8%) aggiunta al prezzo dell'autodemolizione sui pezzi venduti online (negozio, eBay, marketplace), fatturata sui pezzi venduti, stornata sui resi; niente al banco.
- **Disdetta:** dalla pagina Abbonamento, vale alla fine del periodo pagato; niente rimborsi per periodi in corso; dopo la fine il gestionale si blocca e i dati restano 12 mesi, poi si cancellano; prima l'azienda può chiederne una copia alla PEC.
- **Responsabilità:** Lostar fa il possibile perché il servizio funzioni ma non garantisce che sia sempre disponibile; l'autodemolizione resta responsabile dei suoi obblighi (registri, RENTRI, formulari, fatture); responsabilità di Lostar limitata a quanto pagato negli ultimi 12 mesi, salvo dolo o colpa grave.
- **Legge e foro:** legge italiana, foro esclusivo di Torino.
- **Accordo (art. 28):** l'autodemolizione è titolare dei dati che inserisce (clienti, proprietari dei veicoli, dipendenti); Lostar è responsabile e li tratta solo per dare il servizio e su istruzione del cliente; riservatezza di chi li tratta; misure di sicurezza (accessi con password e ruoli, cifratura in transito, database con accesso solo dal server, copie del fornitore); sub-responsabili = `FORNITORI`, con avviso di eventuali cambi via email e diritto di opporsi; aiuto per i diritti degli interessati e per le violazioni (avviso senza ingiustificato ritardo); alla fine del contratto restituzione su richiesta e cancellazione entro 12 mesi; controlli su richiesta scritta.

- [ ] **Step 1: Test** in `legale.test.ts`:
  - `CONDIZIONI.versione === VERSIONE_CONDIZIONI`; gli id delle sezioni, in ordine, sono quelli sopra con `accordo` ultimo.
  - Il testo contiene, per ogni modulo di `LISTINO`, `LISTINO[m].nome`, `euro(LISTINO[m].mese)` e `euro(LISTINO[m].anno)`; «IVA esclusa»; `${GIORNI_PROVA} giorni`; `${COMMISSIONE_ONLINE * 100}%`; «consumatori»; «Torino».
  - La sezione `accordo` contiene «art. 28», «titolare», «responsabile» e ogni nome di `FORNITORI`; «Supabase» compare solo nella sezione `accordo`.
- [ ] **Step 2: `npm test`** — Expected: FAIL.
- [ ] **Step 3: Implementare** `condizioni.ts` e la pagina (metadata: «Condizioni del servizio · Piazzale», indicizzabile; ancora `#accordo` per l'allegato).
- [ ] **Step 4: `npm test`** — Expected: PASS. **`npx tsc --noEmit -p .`** — nessun errore.
- [ ] **Step 5: Commit** — `git commit -m "Condizioni del servizio e accordo sul trattamento dei dati"`

### Task 3: Landing «Registrati gratis» e link ai documenti

**Files:**
- Modify: `src/components/sito/Sito.tsx`, `src/app/scopri/page.tsx`, `src/app/news/[slug]/page.tsx`, `src/app/sitemap.ts`, `src/components/AppShell.tsx`, `src/app/registrati/view.tsx`

**Interfaces:**
- Consumes: le pagine dei Task 1 e 2.
- Produces in `Sito.tsx`: `REGISTRAZIONE = "/registrati"` (non più `DEMO`); `DEMO` resta per `/demo` in locale ma nessun pulsante pubblico lo usa.

Cosa cambia:
- I quattro «Apri la demo» (testata, apertura e chiusura di `/scopri`, scheda di una normativa) diventano **«Registrati gratis»** verso `REGISTRAZIONE`. Nell'apertura di `/scopri`, sotto i pulsanti, la riga «15 giorni con tutto incluso, senza carta».
- `ATTIVAZIONE` di `/scopri`: «Ti registri» (crei l'account della tua azienda dal sito e confermi l'email) → «15 giorni con tutto» (tutti i moduli accesi, senza carta, sul tuo piazzale) → «Scegli i moduli» (al mese o all'anno, paghi con carta su Stripe e il gestionale resta aperto).
- `Piede` del sito: link «Privacy» (`/privacy`) e «Condizioni» (`/condizioni`).
- Gestionale (`AppShell.tsx`): accanto a `LostarCredit`, nella barra laterale e nel piede su telefono, i link piccoli «Privacy» e «Condizioni».
- Modulo di registrazione: il link «accordo sul trattamento dei dati» porta a `/condizioni#accordo` (le condizioni restano a `/condizioni`).
- `sitemap.ts`: `/privacy` e `/condizioni` con `changeFrequency: "yearly"`.
- In testata resta «Accedi».

- [ ] **Step 1: `npm test` e `npx tsc --noEmit -p .`** dopo le modifiche — Expected: PASS, nessun errore; `grep -rn "Apri la demo" src/app src/components` non trova pulsanti (solo commenti di `src/app/demo` e `demo-pubblica.ts`).
- [ ] **Step 2: Verifica nel browser** su un server di sviluppo con dati separati (porta libera e `DATI_DIR` nella scratchpad, come da `docs/ACCESSO.md`): `/scopri`, `/news/<una scheda>`, `/privacy`, `/condizioni#accordo`, `/registrati` a 1280 px e a 375 px. Ogni «Registrati gratis» apre `/registrati`; i link dei piedi e del modulo aprono le pagine giuste senza accesso; niente scorrimento laterale a 375 px; nessun errore in console.
- [ ] **Step 3: Commit** — `git commit -m "Landing: «Registrati gratis» al posto della demo, link a privacy e condizioni"`

---

## Prima di aprire la registrazione al pubblico (fuori da questo piano)

- Far rileggere `/privacy`, `/condizioni` e l'accordo a un consulente; ogni cambio di testo sposta `VERSIONE_*`.
- La pulizia automatica che i testi promettono: registrazioni mai confermate e prove finite senza abbonamento cancellate dopo 12 mesi; dati di chi disdice cancellati 12 mesi dopo la fine.
- Le chiavi Stripe vere con la regola per gli abbonamenti pagati in prova (`docs/PAGAMENTI.md`).
- IVA e fattura elettronica da confermare con il commercialista (`docs/PAGAMENTI.md`).
