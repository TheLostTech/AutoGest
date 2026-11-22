# Registrazione su invito e pagamento con Stripe: piano di lavoro

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Obiettivo:**
- il titolare si registra con un codice invito e inserisce il primo veicolo;
- il gestionale si blocca con un riquadro di pagamento;
- paga su Stripe Checkout (sandbox AutoLost demo) al mese o all'anno;
- il server accende i moduli pagati e mostra il conto alla rovescia;
- l'orologio di prova di Stripe fa avanzare il tempo.

**Architettura:**
- Lo stato dell'abbonamento di ogni azienda sta in `DATI_DIR/aziende/<id>/abbonamento.json` e lo scrive solo il server, rileggendo Stripe (`sincronizza`).
- Le regole sono funzioni pure in `src/lib/abbonamento.ts`:
  - stati,
  - moduli accesi,
  - blocco,
  - conto alla rovescia,
  - traduzione da Stripe.
- Le route Next leggono e scrivono, e l'interfaccia legge `/api/abbonamento/stato`.
- `/api/demo-state` impone i moduli del server e rifiuta le scritture con il blocco (402).

**Tecnologie:**
- Next.js 16.4 App Router e React 19;
- Better Auth 1.7 con `piattaforma.sqlite`;
- libreria `stripe` per Node, Zustand 5, Tailwind 4 e test con `node --test`.

**Spec:** [docs/superpowers/specs/2026-11-22-registrazione-pagamento-design.md](../specs/2026-11-22-registrazione-pagamento-design.md). Chi esegue legge spec e piano insieme.

## Vincoli generali

- **Next.js 16.4.** Prima di scrivere route, pagine o `PageProps` si leggono le guide in `node_modules/next/dist/docs/` (AGENTS.md).
- **Test.** I test girano con `npm test`, cioè `node --import ./scripts/alias-ts.mjs --test …` dal ramo `login-ruoli`. Ogni file di test nuovo va aggiunto allo script `test` se non sta in `src/lib/*.test.ts`.
- **Il titolare** è il ruolo `responsabile`. Non si aggiunge un ruolo nuovo.
- **Nomi in Stripe.** L'id del modulo nell'app e il nome in Stripe sono: `magazzino`→`magazzino`, `accettazione`→`pratiche`, `ambiente`→`ambiente`, `vendite`→`banco`. Le lookup key sono `<nomeStripe>_mese` e `<nomeStripe>_anno`, e ogni prodotto ha `metadata.modulo` con l'id dell'app.
- **Prezzi** da `src/lib/listino.ts`: centesimi, IVA esclusa. Magazzino 29990 / 319900, Pratiche 1990 / 21900, Ambiente 4990 / 53900, Banco 4990 / 53900.
- **IVA.** In Checkout c'è l'aliquota fissa "IVA 22%" esclusiva; si raccolgono partita IVA e indirizzo di fatturazione e la lingua è `it`.
- **Chiavi.** `STRIPE_SECRET_KEY` deve cominciare con `sk_test_`. Con `sk_live_` senza `STRIPE_LIVE=1` niente pagamenti, e gli strumenti di prova rispondono 404 fuori dalla prova.
- **Pagamento non riuscito.** Stripe ritenta per 14 giorni, poi annulla l'abbonamento.
- **Codici invito:** validi 30 giorni, si usano una volta sola. A un codice sbagliato, scaduto o usato il messaggio è sempre "Codice invito non valido".
- **Registrazione:**
  - password di almeno 10 caratteri;
  - al massimo 3 registrazioni all'ora per indirizzo, letto da `cf-connecting-ip`;
  - a un'email già usata il messaggio è "Non è stato possibile registrarti con questa email. Se hai già un account, accedi."
- **Testi e righe del registro** sono in italiano e copiati dallo spec: "Azienda registrata", "Abbonamento attivato", "Modulo aggiunto: <Nome>", "Pagamento non riuscito", "Abbonamento disdetto", "Abbonamento scaduto".
- **Aziende senza `registrata`** (la demo e quelle create dal super admin): tutto resta com'è oggi, con gli interruttori dei moduli e senza pagamento.
- **Il ramo `main`** non si tocca. Si lavora sul ramo `registrazione-pagamento`.

## Da controllare in revisione

1. **Due pagamenti per sbaglio.** Due clic su "Paga" o due schede aperte creano due Checkout. Ci si aspetta che `sincronizza` scelga l'abbonamento valido più recente e che il checkout rifiuti un'azienda già `attivo`. Lo prova il test `abbonamentoDaStripe sceglie l'abbonamento attivo tra più abbonamenti` (Task 1).
2. **Avviso di Stripe e pagina di ritorno insieme.** Possono scrivere `abbonamento.json` nello stesso momento. Ci si aspetta che le scritture si mettano in fila per azienda e che rifare la stessa sincronizzazione non cambi nulla. Lo prova il test `aggiornaAbbonamento mette in fila le scritture della stessa azienda` (Task 2).
3. **Un browser che manda `whole.moduli` con tutto acceso per un'azienda registrata.** Ci si aspetta che il server lo ignori. Lo prova il test `scritturaAzienda toglie i moduli mandati dal browser` (Task 2).
4. **Orologio di prova avanzato.** Ci si aspetta che il conto alla rovescia conti dall'ora dell'orologio e non dalla data del Mac. Lo prova il test `contoAllaRovescia usa oraOrologio quando c'è` (Task 1).
5. **Stesso codice invito in due schede.** Ci si aspetta che una sola registrazione passi. Lo prova il test `usaInvito accetta lo stesso codice una volta sola anche in parallelo` (Task 4).

---

### Task 0: Ramo unito `registrazione-pagamento`

**Serve il via di Alessandro prima di cominciare** (lo spec, sezione "Su che ramo si costruisce").

**File:**
- Si uniscono i rami `login-ruoli` e `moduli-a-pagamento`.
- Si aggiungono `src/lib/listino.ts` e `src/lib/listino.test.ts` da `offerta-prezzi`.
- Si modifica `src/lib/moduli-server.ts`.
- Si modificano i conflitti: `src/components/AppShell.tsx`, `src/lib/store.ts`, `src/lib/sync.ts`, `src/app/api/demo-state/route.ts`, `src/app/api/visura/route.ts`.

**Interfacce:**
- Produce: `moduloAttivoSulServer(aziendaId: string, m: Modulo): Promise<boolean>`. Legge `leggiStato(aziendaId)` di `archivio-azienda.ts` e poi `moduliDaArchivio`. Dal Task 2 consulta anche l'abbonamento.

- [ ] **Passo 1. Il listino.** Controlla se il ramo `offerta-prezzi` contiene `src/lib/listino.ts`:
  - se c'è, uniscilo al ramo;
  - se manca, chiedi ad Alessandro di farlo salvare dalla sessione che ci lavora;
  - se non arriva, ricopia `.claude/worktrees/offerta/src/lib/listino.ts` così com'è (esporta `LISTINO`, `prezzo`, `risparmioAnnuale`, `totale`, `euro`, `COMMISSIONE_ONLINE`, `Periodo`) insieme al suo test.
- [ ] **Passo 2. Il ramo.**
  ```bash
  git switch -c registrazione-pagamento login-ruoli
  ```
- [ ] **Passo 3. Unione dei moduli.**
  ```bash
  git merge moduli-a-pagamento
  ```
  Risolvi i conflitti tenendo tutte e due le parti:
  - `moduli` resta in WHOLE nella sincronizzazione per azienda;
  - il gate dei moduli in `AppShell` resta dentro il layout con l'accesso;
  - la guardia 403 della visura usa l'azienda della sessione.
- [ ] **Passo 4.** Cambia `moduloAttivoSulServer` nella firma per azienda e aggiorna chi la chiama, cioè `api/visura/route.ts` con `a.azienda.id`.
- [ ] **Passo 5. Controllo.**
  - Lancia `npm test && npx tsc --noEmit && npm run lint`: tutto deve passare.
  - Avvia `next dev` su una porta nuova con un `DATI_DIR` nuovo ([[prove-su-dati-separati]]): con l'azienda demo i moduli si spengono e si accendono come prima.
- [ ] **Passo 6.** Salva il lavoro nel ramo (`git commit`) con il messaggio "Unisce login, moduli e listino in registrazione-pagamento".

### Task 1: Regole pure dell'abbonamento

**File:**
- Crea: `src/lib/abbonamento.ts` (solo import di tipi)
- Test: `src/lib/abbonamento.test.ts`

**Interfacce:**
- Produce:
  ```ts
  export type StatoAbbonamento = "nuovo" | "attivo" | "in-ritardo" | "disdetto" | "scaduto";
  export type Abbonamento = {
    stato: StatoAbbonamento; periodo: Periodo | null; moduli: Modulo[];
    rinnovo: number | null;            // ms, fine del periodo pagato
    customerId: string | null; subscriptionId: string | null;
    orologioId: string | null; oraOrologio: number | null; // ms, solo in prova
    prova: boolean; pagatoAlmenoUnaVolta: boolean; aggiornato: number;
  };
  export const ABBONAMENTO_NUOVO: (prova: boolean, ora: number) => Abbonamento;
  export function nomeStripe(m: Modulo): "magazzino" | "pratiche" | "ambiente" | "banco";
  export function lookupKey(m: Modulo, p: Periodo): string;          // "pratiche_mese"
  export function moduliDaAbbonamento(a: Abbonamento): Modulo[];       // sempre con "magazzino"
  export function bloccato(a: Abbonamento, veicoli: number): boolean;
  // Forma minima di un abbonamento Stripe, così il test non dipende dalla libreria
  export type SubStripe = { id: string; status: string; cancel_at_period_end: boolean; created: number;
    items: { price: { recurring: { interval: "month" | "year" } | null; product: { metadata: Record<string, string> } | string }; current_period_end: number }[] };
  export function abbonamentoDaStripe(subs: SubStripe[], prima: Abbonamento, ora: number, oraOrologio: number | null): Abbonamento;
  export type Conto = { tono: "ok" | "avviso" | "errore"; testo: string; giorni: number | null };
  export function contoAllaRovescia(a: Abbonamento, oraMac: number): Conto | null;
  export function righeCambio(prima: Abbonamento, dopo: Abbonamento): string[]; // righe del registro
  ```

- [ ] **Passo 1. Scrivi i test che falliscono.**
  - `lookupKey("accettazione","mese") === "pratiche_mese"`, `lookupKey("vendite","anno") === "banco_anno"`.
  - `moduliDaAbbonamento`:
    - con lo stato `nuovo` dà `["magazzino"]`;
    - con lo stato `attivo` e moduli `["magazzino","ambiente"]` dà quei moduli;
    - con lo stato `scaduto` dà `["magazzino"]`;
    - con lo stato `attivo` e moduli `["ambiente"]` aggiunge comunque `magazzino`.
  - `bloccato`:
    - lo stato `nuovo` con 0 veicoli non blocca, con 1 veicolo blocca;
    - lo stato `scaduto` con 0 veicoli blocca;
    - lo stato `in-ritardo` non blocca, e nemmeno `disdetto`.
  - `abbonamentoDaStripe`, un test per riga della tabella dello spec, sezione 5:
    - `active` dà `attivo`, ma con `cancel_at_period_end` dà `disdetto`;
    - `past_due` dà `in-ritardo`;
    - `canceled`, `unpaid` e `incomplete_expired` danno `scaduto`;
    - `incomplete` lascia lo stato di `prima`;
    - nessun abbonamento con `pagatoAlmenoUnaVolta: false` dà `nuovo`, con `true` dà `scaduto`.
  - Altri test su `abbonamentoDaStripe`:
    - i moduli si leggono da `product.metadata.modulo`; un valore sconosciuto si scarta;
    - `rinnovo` è `current_period_end*1000` della prima voce;
    - `periodo` vale `"anno"` se `interval === "year"`, altrimenti `"mese"`;
    - test `abbonamentoDaStripe sceglie l'abbonamento attivo tra più abbonamenti`: tra uno `canceled` più recente e uno `active` vince `active`; tra due `active` vince il più recente.
  - `contoAllaRovescia`, con rinnovo al 22/12/2026 e ora al 22/11/2026:
    - lo stato `attivo` dà `{ tono:"ok", testo:"Si rinnova il 22/12/2026 · tra 30 giorni", giorni:30 }`;
    - lo stesso giorno dà "Si rinnova oggi";
    - lo stato `disdetto` dà "Finisce il 22/12/2026 · tra 30 giorni. Poi il gestionale si blocca, i dati restano." con il tono `avviso`;
    - lo stato `in-ritardo` comincia con "Pagamento non riuscito" e ha il tono `errore`;
    - lo stato `scaduto` e lo stato `nuovo` danno `null`.
  - Test `contoAllaRovescia usa oraOrologio quando c'è`: con `oraOrologio` al 20/12/2026 e la data del Mac al 22/11/2026, il testo è "tra 2 giorni".
  - `righeCambio`:
    - da `nuovo` ad `attivo` dà `["Abbonamento attivato"]`;
    - aggiungere `ambiente` dà `["Modulo aggiunto: Ambiente"]` (il nome viene da `MODULI` di `moduli.ts`);
    - da `attivo` a `in-ritardo` dà `["Pagamento non riuscito"]`;
    - da `attivo` a `disdetto` dà `["Abbonamento disdetto"]`;
    - da qualunque stato a `scaduto` dà `["Abbonamento scaduto"]`;
    - nessun cambio dà `[]`.
- [ ] **Passo 2.** Lancia `npm test`: i test devono FALLIRE, perché il modulo non esiste.
- [ ] **Passo 3. Scrivi `src/lib/abbonamento.ts`.**
  - I giorni sono `Math.ceil((rinnovo - ora)/86_400_000)`, con `ora = oraOrologio ?? oraMac`.
  - Le date sono `dd/mm/yyyy` nel fuso `Europe/Rome`.
  - Nella scelta tra più abbonamenti, `active`, `trialing` e `past_due` battono gli altri; a parità vince `created` più alto.
- [ ] **Passo 4.** Lancia `npm test`: deve PASSARE.
- [ ] **Passo 5.** Salva il lavoro nel ramo con il messaggio "Abbonamento: regole pure (stati, blocco, conto alla rovescia)".

### Task 2: Abbonamento sul server e `/api/demo-state`

**File:**
- Crea: `src/lib/abbonamento-server.ts`.
- Modifica:
  - `src/lib/accesso/regole.ts`: `AziendaVista` riceve `registrata: boolean`;
  - `src/lib/accesso/server.ts`: `aziendaVista` legge `metadata.registrata`;
  - `src/lib/piattaforma/crea.ts`: `creaAzienda(c, nome, slug, demo, extra?: Record<string, unknown>)` unisce `extra` alla metadata;
  - `src/lib/moduli-server.ts`;
  - `src/app/api/demo-state/route.ts`.
- Test:
  - `src/lib/abbonamento.test.ts`, con le funzioni pure nuove;
  - `src/lib/abbonamento-server.prova.ts`, aggiunto allo script `test`.

**Interfacce:**
- Consuma: `Abbonamento`, `bloccato` e `moduliDaAbbonamento` dal Task 1.
- Produce, in `abbonamento.ts` (puro):
  ```ts
  export type Scrittura = { esito: "ok"; corpo: Push } | { esito: "bloccato" };
  export function scritturaAzienda(registrata: boolean, a: Abbonamento | null, veicoliPrima: number, corpo: Push): Scrittura;
  export function statoPerBrowser(registrata: boolean, a: Abbonamento | null, stato: unknown): unknown; // mette moduli = moduliDaAbbonamento
  ```
- Produce, in `abbonamento-server.ts`:
  ```ts
  export function leggiAbbonamento(aziendaId: string): Promise<Abbonamento | null>;
  export function aggiornaAbbonamento(aziendaId: string, fn: (prima: Abbonamento | null) => Abbonamento): Promise<Abbonamento>;
  ```
  La scrittura usa un file temporaneo e la rinomina, con un blocco in memoria per azienda, come `aggiornaStato`.
- Cambia `moduloAttivoSulServer(aziendaId, m)`: per un'azienda registrata decide `moduliDaAbbonamento(await leggiAbbonamento(id) ?? nuovo)`.

- [ ] **Passo 1. Scrivi i test che falliscono.**
  - Test `scritturaAzienda toglie i moduli mandati dal browser`: per un'azienda registrata, `corpo.whole.moduli` sparisce e il resto del corpo resta uguale; per un'azienda non registrata il corpo non cambia.
  - `scritturaAzienda`:
    - un'azienda registrata nello stato `nuovo` con `veicoliPrima` 0 dà `ok`, anche se il corpo aggiunge il primo veicolo;
    - con `veicoliPrima` 1 dà `bloccato`;
    - nello stato `attivo` dà `ok`;
    - un'azienda non registrata dà sempre `ok`.
  - `statoPerBrowser`:
    - per un'azienda registrata con lo stato `attivo` e moduli `["magazzino","vendite"]`, `stato.moduli` contiene quei due accesi e gli altri spenti, nella forma di `StatoModulo[]` di `moduli.ts`;
    - per un'azienda non registrata restituisce lo stato così com'è.
  - In `abbonamento-server.prova.ts`, con un `DATI_DIR` temporaneo:
    - test `aggiornaAbbonamento mette in fila le scritture della stessa azienda`: 20 aggiornamenti in parallelo che aggiungono un numero ciascuno al campo `aggiornato` finiscono tutti, e il file letto alla fine è JSON valido con l'ultimo valore;
    - `leggiAbbonamento` di un'azienda senza file dà `null`.
- [ ] **Passo 2.** Lancia `npm test`: i test devono FALLIRE.
- [ ] **Passo 3. Scrivi le funzioni.**
  - In `regole.ts`, `AziendaVista.registrata`; aggiorna i test di `regole.test.ts` che costruiscono `AziendaVista`.
  - In `demo-state/route.ts`:
    - GET risponde con `{ ...s, state: statoPerBrowser(...), abbonamento: a ?? null }`;
    - PUT, dentro `aggiornaStato`, conta i veicoli di `cur.state.vehicles` e chiama `scritturaAzienda`. Se il risultato è bloccato, risponde 402 con `{ error: "Abbonamento non attivo", motivo: "abbonamento" }` e non scrive nulla.
- [ ] **Passo 4.** Lancia `npm test && npx tsc --noEmit`: deve PASSARE.
- [ ] **Passo 5.** Salva il lavoro nel ramo con il messaggio "Abbonamento: archivio sul server, moduli imposti e blocco delle scritture".

### Task 3: Modifiche in attesa del pagamento sul dispositivo

**File:**
- Modifica: `src/lib/sync-in-sospeso.ts` e `src/lib/sync.ts`.
- Test: `src/lib/sync-in-sospeso.test.ts`.

**Interfacce:**
- Produce:
  - `aggiungiInSospeso(prima, schema, changes, counters, ora, liste, opzioni?: { pagamento?: boolean })`: la coda salvata riceve `pagamento: true`;
  - `corpoDaRiprendere(raw, schema, ora, liste)`: con `raw.pagamento === true` non scarta le voci più vecchie di `IN_SOSPESO_MAX_MS`.
- Produce, in `sync.ts`, `export function inAttesaDiPagamento(): boolean`. La legge il riquadro del Task 7.

- [ ] **Passo 1. Scrivi i test che falliscono.**
  - Una coda con `pagamento: true` e una voce di 3 giorni fa: `corpoDaRiprendere` la tiene.
  - La stessa coda senza `pagamento`: la scarta, come oggi.
  - `aggiungiInSospeso` con `{ pagamento: true }` su una coda senza il flag produce una coda con `pagamento: true`.
  - Una coda già con `pagamento: true` mantiene il flag anche se la chiamata non lo passa.
- [ ] **Passo 2.** Lancia `npm test`: i test devono FALLIRE.
- [ ] **Passo 3. Il flag nella coda.** In `sync-in-sospeso.ts`, `leggiCoda` usa `fresco` solo se `raw.pagamento !== true`.
- [ ] **Passo 4. Il 402 in `sync.ts`.** `gestisciRifiuto` riconosce `e.stato === 402 && e.motivo === "abbonamento"`:
  - salva le differenze con `salvaInSospeso(d, { pagamento: true })`;
  - imposta `attesaPagamento = true` e restituisce `true`.
  - Con `attesaPagamento` attivo, `pushChanges` non parte e le letture continuano.
  - `pull`, quando `res.abbonamento` non è più bloccato (`bloccato(res.abbonamento, veicoli)`), rimette `attesaPagamento = false` e chiama `inviaSalvateInSospeso()`.
  - In `inviaSalvateInSospeso`, un 402 lascia la coda dov'è.
- [ ] **Passo 5. Controllo.**
  - Lancia `npm test && npx tsc --noEmit`: deve PASSARE.
  - Nel browser, con un'azienda registrata nello stato `nuovo`, salva due veicoli:
    - il primo entra;
    - il secondo resta in sospeso con `pagamento: true` (lo mostra `localStorage`);
    - porta a mano `abbonamento.json` ad `attivo`: entro 5 secondi il secondo veicolo arriva sul server.
- [ ] **Passo 6.** Salva il lavoro nel ramo con il messaggio "Sincronizzazione: le modifiche bloccate dal pagamento aspettano senza scadenza".

### Task 4: Codici invito

**File:**
- Crea:
  - `src/lib/auth/inviti.ts`: plugin con lo schema `invito` e niente endpoint, come `assistenzaPlugin`;
  - `src/lib/accesso/inviti-regole.ts` e il suo test;
  - `src/lib/piattaforma/inviti.ts`: funzioni server;
  - `src/app/api/piattaforma/inviti/route.ts`;
  - `src/app/piattaforma/inviti/page.tsx` e `view.tsx`.
- Modifica:
  - `src/lib/auth/server.ts`: aggiunge il plugin;
  - `src/app/piattaforma/comune.tsx`: voce di menu "Inviti".
- Test: `src/lib/accesso/inviti-regole.test.ts` e `src/lib/piattaforma/inviti.prova.ts`, aggiunto allo script `test`.

**Interfacce:**
- Schema `invito`: `codiceHash` (string, unique), `nota` (string), `creatoDa` (userId), `creato` (date), `scade` (date), `usatoDa` (organizationId, facoltativo), `usato` (date, facoltativo).
- Produce:
  ```ts
  // inviti-regole.ts (puro)
  export const INVITO_MS = 30 * 86_400_000;
  export function formatoCodice(s: string): string | null;  // "al7k 2m9q x4tp" -> "AL7K-2M9Q-X4TP"; forma non valida -> null
  export function invitoValido(i: { scade: number; usato?: number | null } | null, ora: number): boolean;
  // piattaforma/inviti.ts (server)
  export function creaInvito(c: Contesto, creatoDa: string, nota: string): Promise<{ codice: string; scade: number }>;
  export function usaInvito(c: Contesto, codice: string, aziendaId: string): Promise<boolean>;
  export function verificaInvito(c: Contesto, codice: string): Promise<boolean>;
  ```

- [ ] **Passo 1. Scrivi i test che falliscono.**
  - `formatoCodice("al7k-2m9q-x4tp")` dà `"AL7K-2M9Q-X4TP"`.
  - Spazi e minuscole si accettano.
  - Una lunghezza sbagliata o un carattere fuori alfabeto dà `null`.
  - `invitoValido`:
    - un invito che scade domani e non è usato vale `true`;
    - un invito scaduto o usato vale `false`;
    - `null` vale `false`.
  - In `inviti.prova.ts`, con il database in una cartella temporanea:
    - test `usaInvito accetta lo stesso codice una volta sola anche in parallelo`: due `usaInvito` in parallelo danno un `true` e un `false`;
    - un codice creato e poi usato non è più valido per `verificaInvito`.
- [ ] **Passo 2.** Lancia `npm test`: i test devono FALLIRE.
- [ ] **Passo 3. Scrivi i codici.**
  - Il codice ha 12 caratteri dell'alfabeto `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`, presi da `randomBytes`, in gruppi da 4 con il trattino.
  - Si salva solo `sha256(codice normalizzato)`.
  - `usaInvito` mette in fila le chiamate con un blocco in memoria: c'è un solo processo Node, come dice ACCESSO.md.
- [ ] **Passo 4. Route e pagina.**
  - La route `GET`/`POST` riusa `superadminDaRichiesta`, `daAltroSito`, `leggiJson`, `testo(nota, 0, 120)`, `ok` ed `errore` di `piattaforma/server.ts`.
  - Il `POST` risponde `{ codice, link: "/registrati?invito=<codice>", scade }`: il codice si mostra una volta sola.
  - Il `GET` elenca gli inviti con nota, creato, scade, stato (valido, usato, scaduto) e azienda, senza codice.
  - La pagina "Inviti" della Piattaforma ha il campo della nota, "Crea invito", il link da copiare e l'elenco.
- [ ] **Passo 5.** Lancia `npm test && npx tsc --noEmit`: deve PASSARE. Poi apri la Piattaforma nel browser come super admin e crea un invito.
- [ ] **Passo 6.** Salva il lavoro nel ramo con il messaggio "Piattaforma: codici invito per la registrazione".

### Task 5: Registrazione

**File:**
- Crea:
  - `src/lib/accesso/registrazione.ts` (puro) e il suo test;
  - `src/app/api/registrazione/route.ts`;
  - `src/app/registrati/page.tsx` e `view.tsx`.
- Modifica:
  - `src/lib/accesso/percorsi.ts`: aggiunge `/registrati` a `PUBBLICI`, e aggiorna `percorsi.test.ts`;
  - `src/app/accesso/view.tsx`: link "Non hai un account? Registrati".
- Test: `src/lib/accesso/registrazione.test.ts`.

**Interfacce:**
- Consuma:
  - `verificaInvito` e `usaInvito` (Task 4);
  - `creaAzienda(..., { registrata: true })` e `aggiornaAbbonamento` (Task 2);
  - `ABBONAMENTO_NUOVO` (Task 1);
  - `modalitaStripe` (Task 6): `prova` vale `true` quando la modalità è `"prova"`. Fino al Task 6 vale sempre `true`.
- Produce:
  ```ts
  export type DatiRegistrazione = { azienda: string; nome: string; email: string; password: string; invito: string; condizioni: true };
  export function validaRegistrazione(corpo: unknown): { ok: DatiRegistrazione } | { errore: string };
  export function registrazioneConsentita(ip: string | null, ora: number): boolean; // 3 all'ora per indirizzo, in memoria
  ```

- [ ] **Passo 1. Scrivi i test che falliscono.**
  - `validaRegistrazione` rifiuta:
    - un nome dell'azienda sotto i 2 o sopra gli 80 caratteri;
    - un nome vuoto;
    - un'email senza `@`;
    - una password di 9 caratteri ("La password deve avere almeno 10 caratteri.");
    - le condizioni non accettate;
    - un codice invito di formato sbagliato ("Codice invito non valido").
  - `validaRegistrazione` mette l'email in minuscolo e senza spazi ai lati.
  - `registrazioneConsentita`:
    - con lo stesso indirizzo la quarta chiamata nell'ora vale `false`;
    - un altro indirizzo vale `true`;
    - dopo 61 minuti torna `true`;
    - un indirizzo `null` usa un contatore comune.
- [ ] **Passo 2.** Lancia `npm test`: i test devono FALLIRE.
- [ ] **Passo 3. Scrivi `POST /api/registrazione`, nell'ordine:**
  1. `daAltroSito`;
  2. `registrazioneConsentita`, che se è superata risponde 429;
  3. `validaRegistrazione`;
  4. `verificaInvito`;
  5. `creaAzienda(c, azienda, slugDa(azienda), false, { registrata: true })`;
  6. `creaStatoAzienda(id, statoVuoto(...))`, come in `api/piattaforma/aziende/route.ts`;
  7. `creaMembro(c, id, { nome, ruoli: ["responsabile"], email, password })`;
  8. `aggiornaAbbonamento(id, () => ABBONAMENTO_NUOVO(prova, Date.now()))`;
  9. `usaInvito(c, invito, id)`: se dà `false`, si annulla tutto e si risponde "Codice invito non valido";
  10. `registra(id, nome, { entity: "sistema", entityId: id, action: "Azienda registrata", detail: azienda })`.
  - **Errori.** Ogni errore dopo il passo 5 toglie l'azienda (record in `organization` e cartella `cartellaAzienda(id)`); `creaMembro` toglie da sé l'utente.
  - **Email già usata** (`findUserByEmail`): il messaggio generico dei Vincoli generali, prima del passo 5.
  - **Risposta:** `201 { ok: true }`.
- [ ] **Passo 4. Pagina `/registrati`.**
  - Campi: azienda, nome e cognome, email, password, codice invito (riempito da `?invito=`), casella delle condizioni con il link a `/condizioni`, pagina segnaposto da creare.
  - Riga in piccolo: "Ambiente di prova: nessun addebito vero".
  - Senza codice c'è la riga "La registrazione è su invito: chiedi il codice ad AutoLost."
  - Dopo il 201 la pagina fa come `/accesso`: `authClient.signIn.email`, poi `authClient.organization.setActive` sulla prima azienda e `location.assign("/")`.
  - La landing (`src/app/scopri/` e `Sito.tsx`) riceve il link "Accedi" verso `/accesso` e la riga "Ambiente di prova: nessun addebito vero". Il pulsante `REGISTRAZIONE` resta sulla demo.
- [ ] **Passo 5. Controllo.**
  - Lancia `npm test && npx tsc --noEmit`: deve PASSARE.
  - Nel browser, con un invito del Task 4, registrati e arrivi su "Oggi" con solo il Magazzino acceso.
  - Lo stesso link una seconda volta dà "Codice invito non valido".
- [ ] **Passo 6.** Salva il lavoro nel ramo con il messaggio "Registrazione del titolare su invito".

### Task 6: Stripe sul server e sincronizzazione

**File:**
- Si installa la libreria: `npm install stripe` (ultima versione stabile; la versione dell'API si fissa nel costruttore).
- Crea:
  - `src/lib/stripe/chiavi.ts` (puro) e il suo test;
  - `src/lib/stripe/server.ts`;
  - `src/app/api/stripe/webhook/route.ts`;
  - `src/app/api/abbonamento/stato/route.ts`.
- Test: `src/lib/stripe/chiavi.test.ts`, aggiunto allo script `test`.

**Interfacce:**
- Consuma: `abbonamentoDaStripe`, `righeCambio` (Task 1), `aggiornaAbbonamento` e `leggiAbbonamento` (Task 2).
- Produce:
  ```ts
  // chiavi.ts (puro)
  export type ModalitaStripe = "prova" | "live" | "spenta";
  export function modalitaDaChiave(chiave: string | undefined, live: string | undefined): ModalitaStripe;
  // server.ts
  export function modalitaStripe(): ModalitaStripe;
  export function stripe(): Stripe;                                 // lancia se la modalità è "spenta"
  export function clientePer(aziendaId: string, nome: string, email: string): Promise<string>; // customerId; in prova con orologio
  export function prezziPer(moduli: Modulo[], periodo: Periodo): Promise<string[]>;             // price id dalle lookup key
  export function aliquotaIva(): Promise<string>;                   // trova o crea "IVA 22%" con metadata.autolost = "iva22"
  export function sincronizza(aziendaId: string): Promise<Abbonamento>;
  ```

- [ ] **Passo 1. Scrivi i test che falliscono.** `modalitaDaChiave`:
  - `undefined` dà `"spenta"`;
  - `"sk_test_x"` dà `"prova"`;
  - `"sk_live_x"` senza il flag dà `"spenta"`;
  - `"sk_live_x"` con `"1"` dà `"live"`;
  - `"rk_test_x"` dà `"prova"`;
  - qualunque altra stringa dà `"spenta"`.
- [ ] **Passo 2.** Lancia `npm test`: i test devono FALLIRE.
- [ ] **Passo 3. Scrivi `server.ts`.**
  - `sincronizza`:
    1. legge l'abbonamento;
    2. se non c'è `customerId`, restituisce quello che c'è;
    3. altrimenti chiama `subscriptions.list({ customer, status: "all", expand: ["data.items.data.price.product"] })` e, con l'orologio, `testHelpers.testClocks.retrieve` per `frozen_time`;
    4. calcola `abbonamentoDaStripe` e scrive con `aggiornaAbbonamento`;
    5. per ogni riga di `righeCambio` scrive nel registro con `registra(aziendaId, "Stripe", …)`.
  - `clientePer`: in prova crea prima `testHelpers.testClocks.create({ frozen_time: ora in secondi, name: aziendaId })` e passa `test_clock`. Salva `customerId` e `orologioId`. Il cliente ha `metadata.azienda`.
- [ ] **Passo 4. Scrivi il webhook.**
  - Legge `await req.text()` e verifica con `stripe().webhooks.constructEvent(corpo, firma, STRIPE_WEBHOOK_SECRET)`; con una firma sbagliata risponde 400.
  - L'azienda si trova da `metadata.azienda` dell'oggetto o del suo cliente (`customers.retrieve`). Per `test_helpers.test_clock.ready` si cerca il cliente dell'orologio con `customers.list({ test_clock })`.
  - Chiama `sincronizza` e risponde 200 anche per un'azienda sconosciuta, scrivendolo nel log.
  - La route è pubblica: passa già, perché `percorsoApi` lascia passare `/api`.
- [ ] **Passo 5. Scrivi `GET /api/abbonamento/stato`.**
  - Accesso con `accessoDaRichiesta`.
  - Sincronizza se è vera una di queste condizioni: `?sincronizza=1`, oppure `Date.now() - aggiornato > 3_600_000` e chi chiede è il titolare.
  - Risponde `{ abbonamento, registrata, modalita, conto: contoAllaRovescia(a, Date.now()) }`.
  - Nella Piattaforma (`src/app/piattaforma/elenco.tsx`) c'è la riga "Stripe: prova (AutoLost demo)", oppure "Stripe: live" o "Stripe: spento", da `modalitaStripe()` letta in `api/piattaforma/stato`.
- [ ] **Passo 6. Controllo.**
  - Lancia `npm test && npx tsc --noEmit`: deve PASSARE.
  - Con `STRIPE_SECRET_KEY` della sandbox in `.env.local` (la mette Alessandro), `curl` su `/api/abbonamento/stato` con la sessione del titolare dà lo stato `nuovo`.
  - Un webhook firmato male dà 400.
- [ ] **Passo 7.** Salva il lavoro nel ramo con il messaggio "Stripe: chiavi, cliente con orologio di prova, sincronizzazione e avvisi".

### Task 7: Checkout e riquadro di pagamento

**File:**
- Crea:
  - `src/app/api/abbonamento/checkout/route.ts`;
  - `src/app/abbonamento/fatto/page.tsx` e `view.tsx`;
  - `src/lib/use-abbonamento.ts`;
  - `src/components/RiquadroPagamento.tsx`;
  - `src/lib/carte-prova.ts`.
- Modifica: `src/components/AppShell.tsx`.
- Test: `src/lib/abbonamento.test.ts` (`sceltaValida`).

**Interfacce:**
- Consuma: Task 6 (`clientePer`, `prezziPer`, `aliquotaIva`, `sincronizza`, `modalitaStripe`), `bloccato` (Task 1), `inAttesaDiPagamento` (Task 3) e `totale`/`euro`/`risparmioAnnuale` di `listino.ts`.
- Produce:
  ```ts
  export function sceltaValida(corpo: unknown): { periodo: Periodo; moduli: Modulo[] } | null; // in abbonamento.ts; aggiunge sempre magazzino, scarta i doppioni
  export function useAbbonamento(): { dati: StatoApi | null; ricarica: (sincronizza?: boolean) => Promise<void> };
  export const CARTE_DI_PROVA: { numero: string; cosa: string }[]; // i tre numeri e le frasi della sezione 7 dello spec
  ```

- [ ] **Passo 1. Scrivi i test che falliscono.** `sceltaValida`:
  - `{ periodo:"anno", moduli:["ambiente"] }` dà `{ periodo:"anno", moduli:["magazzino","ambiente"] }`;
  - un periodo `"settimana"` dà `null`;
  - un modulo `"boh"` si scarta;
  - il corpo `null` dà `null`.
- [ ] **Passo 2.** Lancia `npm test`: i test devono FALLIRE. Poi scrivi `sceltaValida` e rilancia: deve PASSARE.
- [ ] **Passo 3. Scrivi `POST /api/abbonamento/checkout`.**
  - Accesso: `a.ruoli.includes("responsabile") || !!a.assistenza`, altrimenti `soloRuoli`; serve l'azienda registrata.
  - Se `modalitaStripe() === "spenta"` risponde 503 "Pagamenti non disponibili".
  - Prima sincronizza; se lo stato è `attivo`, `in-ritardo` o `disdetto` risponde 409 "Abbonamento già attivo: aggiungi i moduli da Abbonamento".
  - `checkout.sessions.create` con:
    - `mode: "subscription"`;
    - `customer`;
    - `line_items`: i prezzi con `tax_rates: [iva]`;
    - `client_reference_id`;
    - `subscription_data: { metadata: { azienda } }`;
    - `tax_id_collection: { enabled: true }`;
    - `billing_address_collection: "required"`;
    - `customer_update: { name: "auto", address: "auto" }`;
    - `locale: "it"`;
    - `success_url: <origine>/abbonamento/fatto?session_id={CHECKOUT_SESSION_ID}`;
    - `cancel_url: <origine><da>`, dove `da` passa da `percorsoDaSicuro`.
  - L'origine è `INDIRIZZO_GESTIONALE` se c'è, altrimenti l'origine della richiesta.
  - Risponde `{ url }`.
- [ ] **Passo 4. Pagina `/abbonamento/fatto`.**
  - Il server fa `checkout.sessions.retrieve(session_id)` e controlla che `client_reference_id` sia l'azienda della sessione; se `payment_status` è `paid` o `no_payment_required`, chiama `sincronizza`.
  - Se è pagata mostra "Fatto: moduli attivi" con i moduli e il pulsante per "Oggi".
  - Altrimenti mostra "Pagamento in corso: ti avvisiamo qui appena Stripe conferma" e ricontrolla ogni 3 secondi per 2 minuti con `useAbbonamento().ricarica(true)`.
- [ ] **Passo 5. `RiquadroPagamento`.**
  - Ha la forma dello schizzo dello spec (sezione 3): scelta mese o anno, Magazzino fisso, tre caselle, totale con "IVA esclusa", "Paga con Stripe" che fa `location.assign(url)`.
  - In prova mostra il riquadro "Carte di prova" da `CARTE_DI_PROVA`.
  - Con lo stato `scaduto` usa il titolo dello spec e parte dalla scelta di prima.
  - Chi non è `responsabile` né in assistenza vede solo "L'abbonamento non è attivo. Chiedi al titolare di attivarlo." ed "Esci".
  - In `AppShell`, per un'azienda registrata si mostra quando vale `bloccato(dati.abbonamento, vehicles.length)`, con `vehicles` dallo store, oppure `inAttesaDiPagamento()`.
  - È un `role="dialog" aria-modal="true"` che copre tutto e non si chiude con Esc.
- [ ] **Passo 6. Controllo nel browser**, con la sandbox: serve la verifica dell'avviso "Varie funzionalità sospese" del Task 12, passo 1.
  1. Registrati e salva il primo veicolo: si apre il riquadro.
  2. Scegli Annuale + Ambiente: il totale è 3.738 € + IVA.
  3. Paga con 4242 4242 4242 4242: torni su "Fatto" e Ambiente è acceso.
  4. Anche senza `stripe listen`, "Fatto" ha già sincronizzato.
  5. Fai uno screenshot.
- [ ] **Passo 7.** Salva il lavoro nel ramo con il messaggio "Riquadro di pagamento e Stripe Checkout".

### Task 8: Pagina Abbonamento, moduli in più e portale

**File:**
- Crea:
  - `src/app/(app)/impostazioni/abbonamento/page.tsx` e `view.tsx`;
  - `src/app/api/abbonamento/moduli/route.ts`;
  - `src/app/api/abbonamento/portale/route.ts`;
  - `src/components/FasciaAbbonamento.tsx`.
- Modifica:
  - `src/components/AppShell.tsx`: voce di menu "Abbonamento" al posto di "Moduli" per le aziende registrate, e la fascia;
  - `src/components/ModuloBloccato.tsx`: "Attiva" al posto di WhatsApp per le aziende registrate;
  - `src/app/(app)/impostazioni/moduli/view.tsx`: per le aziende registrate rimanda ad Abbonamento.
- Test: `src/lib/abbonamento.test.ts` (`fasciaDaMostrare`).

**Interfacce:**
- Consuma: `useAbbonamento` (Task 7), `contoAllaRovescia` (Task 1), `sincronizza` (Task 6) e `lavoroAperto` di `moduli-lavoro.ts`.
- Produce: `fasciaDaMostrare(a: Abbonamento, ora: number): boolean`. Vale vero con lo stato `in-ritardo`, oppure con `disdetto` e 7 giorni o meno alla fine, contando da `oraOrologio ?? ora`.
- Route `POST /api/abbonamento/moduli`:
  - corpo `{ aggiungi: Modulo } | { togli: Modulo } | { anteprima: Modulo }`;
  - risposta `{ abbonamento }` oppure, per `anteprima`, `{ importo: number }` in centesimi IVA esclusa.

- [ ] **Passo 1. Scrivi i test che falliscono.** `fasciaDaMostrare`:
  - lo stato `in-ritardo` vale `true`;
  - lo stato `disdetto` a 8 giorni vale `false`, a 7 giorni `true`;
  - lo stato `attivo` a 1 giorno vale `false`.
- [ ] **Passo 2.** Lancia `npm test`: i test devono FALLIRE. Scrivi `fasciaDaMostrare` e rilancia: deve PASSARE.
- [ ] **Passo 3. Route dei moduli.** Il titolare o l'assistenza, con lo stato `attivo` o `disdetto`.
  - `aggiungi`: `subscriptionItems.create({ subscription, price: <lookup del periodo attuale>, tax_rates: [iva], proration_behavior: "always_invoice" })`.
  - `togli`: `subscriptionItems.del(itemId, { proration_behavior: "create_prorations" })`. Il Magazzino dà 400.
  - `anteprima`: `invoices.createPreview` con l'aggiunta della voce, e risponde `amount_due` meno le tasse.
  - Poi `sincronizza` e il registro: "Modulo aggiunto: …", oppure "Modulo tolto: …" per la rimozione (scelta mia, sulla falsariga dello spec).
- [ ] **Passo 4. Route del portale.** Risponde `billingPortal.sessions.create({ customer, return_url: <origine>/impostazioni/abbonamento })` con `{ url }`.
- [ ] **Passo 5. Pagina, fascia e "Attiva".**
  - La pagina segue lo schizzo dello spec (sezione 6):
    - periodo e stato;
    - riga del conto alla rovescia;
    - prossimo addebito, che è la somma del listino dei moduli accesi;
    - moduli con Aggiungi e Togli: Aggiungi mostra l'anteprima e chiede conferma, Togli mostra `lavoroAperto` e chiede conferma;
    - "Carta, fatture e disdetta";
    - "Riattiva" quando lo stato è `disdetto`: chiama la stessa route con `{ riattiva: true }`, che fa `subscriptions.update(id, { cancel_at_period_end: false })`.
  - All'apertura chiama `ricarica(true)`.
  - Il pulsante "Attiva" di `ModuloBloccato` porta a `/impostazioni/abbonamento?aggiungi=<modulo>`, che apre la conferma. Chi non è titolare vede "Chiedi al titolare di attivarlo".
- [ ] **Passo 6. Controllo nel browser.**
  - Dall'azienda del Task 7 aggiungi Pratiche: l'anteprima mostra un importo minore di 219 €, e dopo la conferma Pratiche è acceso.
  - Togli Ambiente: la conferma elenca il lavoro aperto, e dopo Ambiente è spento.
  - Il portale si apre e torna indietro.
- [ ] **Passo 7.** Salva il lavoro nel ramo con il messaggio "Pagina Abbonamento: conto alla rovescia, moduli in più e portale".

### Task 9: Strumenti di prova (orologio)

**File:**
- Crea:
  - `src/app/api/abbonamento/prova/avanza/route.ts`;
  - `src/components/StrumentiProva.tsx`.
- Modifica: `src/app/(app)/impostazioni/abbonamento/view.tsx`.
- Test: `src/lib/abbonamento.test.ts`.

**Interfacce:**
- Produce:
  ```ts
  export type Passo = "giorno" | "settimana" | "mese" | "anno";
  export function nuovaOraOrologio(ora: number, passo: Passo): number;           // mese/anno di calendario, fuso Europe/Rome
  export function avanzamentoPermesso(a: Abbonamento, passo: Passo): boolean;    // "anno" solo con periodo "anno"; mai oltre due periodi
  ```

- [ ] **Passo 1. Scrivi i test che falliscono.**
  - `nuovaOraOrologio`:
    - dal 22/11/2026 con `"mese"` arriva al 22/12/2026;
    - dal 31/01/2027 con `"mese"` arriva al 28/02/2027;
    - con `"giorno"` aggiunge 24 ore;
    - con `"anno"` dal 22/11/2026 arriva al 22/11/2027.
  - `avanzamentoPermesso`:
    - `"anno"` con il periodo `"mese"` vale `false`, con `"anno"` vale `true`;
    - `"mese"` vale sempre `true`.
- [ ] **Passo 2.** Lancia `npm test`: i test devono FALLIRE. Scrivi le due funzioni e rilancia: deve PASSARE.
- [ ] **Passo 3. Route `POST /api/abbonamento/prova/avanza`** con corpo `{ passo }`.
  - Se `modalitaStripe() !== "prova"` risponde 404.
  - Accesso: il titolare o l'assistenza; serve `orologioId`.
  - Se l'avanzamento non è permesso risponde 400 "Stripe fa avanzare l'orologio al massimo di due periodi alla volta".
  - Poi chiama `testHelpers.testClocks.advance(orologioId, { frozen_time })` e risponde 202.
- [ ] **Passo 4. `StrumentiProva`.**
  - Mostra "Data di prova: <oraOrologio>" e i pulsanti +1 giorno, +1 settimana, +1 mese e +1 anno (solo con l'annuale).
  - Dopo il clic ricontrolla `ricarica(true)` ogni 2 secondi, finché `oraOrologio` è cambiata e l'orologio è `ready`; `stato` restituisce anche `orologioPronto`.
  - Sulla pagina Abbonamento compare solo in prova.
- [ ] **Passo 5. Controllo nel browser.**
  1. Abbonamento mensile pagato con 4242: +1 settimana fa scendere il conto alla rovescia di 7 giorni.
  2. Dal portale metti la carta 4000 0000 0000 0341, poi +1 mese: compare la fascia "Pagamento non riuscito".
  3. +1 settimana due volte: alla fine dei 14 giorni scatta il blocco e i dati restano visibili sotto.
  4. Fai uno screenshot di ogni passaggio.
- [ ] **Passo 6.** Salva il lavoro nel ramo con il messaggio "Strumenti di prova: orologio di Stripe".

### Task 10: Negozio chiuso durante il blocco

**File:**
- Modifica:
  - `src/lib/negozio-server.ts`;
  - `src/app/api/negozio/catalogo/route.ts`;
  - `src/app/api/negozio/ordine/route.ts`;
  - la pagina del negozio che mostra il catalogo vuoto.
- Test: `src/lib/abbonamento.test.ts`.

**Interfacce:**
- Produce: `negozioAperto(registrata: boolean, a: Abbonamento | null, veicoli: number): boolean`, che vale `!registrata || !bloccato(a ?? nuovo, veicoli)`.
- Produce: `negozioAttivo(aziendaId: string): Promise<boolean>` in `negozio-server.ts`.

- [ ] **Passo 1. Scrivi i test che falliscono.** `negozioAperto`:
  - un'azienda non registrata vale sempre `true`;
  - un'azienda registrata nello stato `scaduto` vale `false`;
  - nello stato `in-ritardo` vale `true`.
- [ ] **Passo 2.** Lancia `npm test`: i test devono FALLIRE. Scrivi la funzione e rilancia: deve PASSARE.
- [ ] **Passo 3. Le route del negozio.**
  - Il catalogo, con il negozio chiuso, risponde `{ chiuso: true, pezzi: [] }`, e la pagina mostra "Negozio momentaneamente chiuso".
  - `ordine` risponde 403 con quello stesso messaggio.
  - Le route di eBay e delle foto non si toccano: va controllato che non leggano il blocco.
- [ ] **Passo 4. Controllo.** Lancia `npm test && npx tsc --noEmit`: deve PASSARE. Nel browser, con l'azienda scaduta del Task 9 messa come `NEGOZIO_AZIENDA`, il negozio risulta chiuso.
- [ ] **Passo 5.** Salva il lavoro nel ramo con il messaggio "Negozio online chiuso durante il blocco dell'abbonamento".

### Task 11: Persone (accessi dei dipendenti)

**File:**
- Crea:
  - `src/app/(app)/impostazioni/persone/page.tsx` e `view.tsx`;
  - `src/app/api/azienda/persone/route.ts`;
  - `src/app/api/azienda/persone/[userId]/route.ts`;
  - `src/lib/accesso/persone-regole.ts` e il suo test.
- Modifica: `src/components/AppShell.tsx` (voce "Persone" per il `responsabile`).

**Interfacce:**
- Consuma:
  - le regole e i controlli di `src/app/api/piattaforma/aziende/[id]/utenti/route.ts` e `src/app/api/piattaforma/utenti/[userId]/route.ts`;
  - si spostano le parti in comune in `src/lib/piattaforma/utenti.ts` invece di copiarle.
- Produce:
  ```ts
  export function cambioRuoliPermesso(membri: { userId: string; ruoli: Role[]; sospeso: boolean }[], userId: string, nuoviRuoli: Role[]): boolean;
  ```
  Vale `false` se così l'azienda resta senza un `responsabile` non sospeso.

- [ ] **Passo 1. Scrivi i test che falliscono.** `cambioRuoliPermesso`:
  - l'unico responsabile che toglie a sé `responsabile` vale `false`;
  - con due responsabili vale `true`;
  - aggiungere ruoli vale sempre `true`;
  - sospendere l'unico responsabile vale `false`. Si usa la stessa funzione con `nuoviRuoli` invariato e `sospeso: true`, quindi aggiungi il parametro `sospeso?: boolean`.
- [ ] **Passo 2.** Lancia `npm test`: i test devono FALLIRE. Scrivi la funzione e rilancia: deve PASSARE.
- [ ] **Passo 3. Le route.**
  - Accesso: `soloRuoli(a, "responsabile")`, sull'azienda della sessione e mai su un id passato dal browser. `daAltroSito` vale sulle scritture.
  - `GET`: l'elenco.
  - `POST`: crea con `creaMembro`.
  - `PATCH`: ruoli, nuova password, nuovo PIN, sospendi o riattiva.
  - Ogni scrittura va nel registro come fa la Piattaforma.
- [ ] **Passo 4. La pagina.** Elenco e modulo "Aggiungi persona" con nome, ruoli (le sei caselle con `RUOLO_LABEL`), e poi email e password oppure solo PIN.
- [ ] **Passo 5. Controllo nel browser.** Il titolare crea uno smontatore con il PIN e uno con email e password. Lo smontatore che entra non vede la voce "Persone" e prende 403 sulla route.
- [ ] **Passo 6.** Salva il lavoro nel ramo con il messaggio "Persone: il titolare crea gli accessi dei dipendenti".

### Task 12: Sandbox, documentazione e prova completa

**File:**
- Crea: `docs/PAGAMENTI.md`.
- Modifica:
  - `docs/ACCESSO.md`: variabili `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_LIVE`;
  - `docs/ROADMAP.md`;
  - `.env.example`, se esiste.

- [ ] **Passo 1. Pannello della sandbox.** Nel pannello Stripe, sandbox **AutoLost demo** (`acct_1UeZEhPHwF2v5yEU`), controlla sempre che l'indirizzo contenga `/test/` e che l'account sia la sandbox, mai live.
  - Leggi l'avviso "Varie funzionalità sospese": se blocca Checkout, fermati e avvisa Alessandro.
  - Imposta Billing → Revenue recovery → Retries a 14 giorni, poi "Cancel the subscription".
  - Nel portale clienti accendi: metodo di pagamento, fatture, dati di fatturazione e disdetta a fine periodo; il cambio di prodotto resta spento.
  - L'aliquota IVA la crea da sé `aliquotaIva()`.
- [ ] **Passo 2. `docs/PAGAMENTI.md`.** Scrivi:
  - le variabili;
  - i passi del passo 1;
  - `stripe login` e `stripe listen --forward-to localhost:<porta>/api/stripe/webhook`, con il segreto stampato messo in `STRIPE_WEBHOOK_SECRET`;
  - le carte di prova;
  - l'orologio;
  - il limite noto: il tunnel cambia indirizzo e quindi non c'è un endpoint fisso;
  - la fattura elettronica fuori da Stripe.
- [ ] **Passo 3. Prova completa nel browser**, su una porta nuova e un `DATI_DIR` nuovo, con `stripe listen` acceso se Alessandro ha fatto `stripe login`:
  1. invito;
  2. registrazione;
  3. primo veicolo;
  4. riquadro;
  5. Checkout mensile con 4242;
  6. moduli accesi;
  7. aggiunta di un modulo;
  8. +1 mese, con il rinnovo e una fattura nuova;
  9. disdetta dal portale, con la fascia a 7 giorni dalla fine;
  10. avanzamento fino alla fine, con il blocco e i dati visibili.
  Fai uno screenshot di ogni passaggio e scrivi in `docs/PAGAMENTI.md` cosa non è stato provato.
- [ ] **Passo 4.** Lancia `npm test && npx tsc --noEmit && npm run lint`: tutto deve passare.
- [ ] **Passo 5.** Salva il lavoro nel ramo con il messaggio "Pagamenti: documentazione e prova completa nella sandbox".
