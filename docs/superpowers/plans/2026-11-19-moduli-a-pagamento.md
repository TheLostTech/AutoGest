# Moduli a pagamento: piano di lavoro

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dividere il gestionale in quattro moduli (Magazzino base + Accettazione, Ambiente, Vendite) attivabili per azienda, con i moduli spenti visibili ma bloccati e la richiesta d'attivazione via WhatsApp.

**Architecture:** Una mappa pura dei moduli (`src/lib/moduli.ts`) dice a quale modulo appartiene ogni percorso; menu, blocco delle pagine, tracce nelle pagine, coda "Oggi", ricerca e server leggono da lì. Lo stato dei moduli sta nello store dell'azienda come collezione `moduli` (sincronizzata come le altre collezioni "intere"). Il Magazzino è sempre attivo.

**Tech Stack:** Next.js 16.4 (App Router, rendering lato client nell'area `(app)`), React 19, Zustand 5, Tailwind 4, test con `node --test` (`npm test`), lucide-react.

**Spec:** `docs/superpowers/specs/2026-11-19-moduli-a-pagamento-design.md`

## Global Constraints

- Prima di scrivere codice di routing o layout leggere la guida pertinente in `node_modules/next/dist/docs/` (AGENTS.md: questa versione di Next ha differenze).
- Nessuna nuova dipendenza.
- Testi dell'interfaccia in italiano semplice, nel tono delle pagine esistenti; disegno secondo `DESIGN.md` e componenti di `src/components/ui`.
- I moduli: `"magazzino" | "accettazione" | "ambiente" | "vendite"`. Nomi visibili: "Magazzino", "Accettazione", "Ambiente", "Vendite".
- Il Magazzino non si spegne mai. Dati senza il campo `moduli` = tutti i moduli attivi.
- Un modulo spento nasconde schermate, non smette di salvare dati.
- Messaggio WhatsApp: `Ciao, sono {azienda} su AutoLost: vorrei attivare il modulo {Nome modulo}.` Numero in `WHATSAPP_ATTIVAZIONE` (segnaposto finché Alessandro non lo fornisce).
- La cartella di lavoro può contenere modifiche di altre sessioni (es. `src/lib/store.ts`, `src/lib/periodo.ts`): in ogni commit aggiungere **solo** i file e le parti toccate dal task (`git add -p` dove serve).
- Test: `npm test` deve restare tutto verde dopo ogni task. Lint: `npm run lint` senza nuovi errori.
- Prove nel browser solo su server separato con dati separati (porta nuova + `DATI_DIR` vuoto), mai sui dati veri.

## Review Focus

1. **Dati salvati prima di questa modifica** (localStorage o `state.json` senza `moduli`): tutto resta attivo, nessun lampo di lucchetti all'avvio. → test `moduliAttivi: senza stato salvato sono tutti attivi` (Task 1).
2. **Indirizzo di una pagina bloccata aperto a mano**, comprese le pagine di stampa (`/certificato/[id]`, `/documento/[id]` di un documento del banco): si vede la pagina del modulo bloccato, mai il contenuto. → test `ogni pagina ha un modulo` (Task 1) + controllo nel browser (Task 4).
3. **Barra inferiore del telefono con un modulo spento**: niente schede doppie, niente schede bloccate, sempre 4 schede se esistono abbastanza aree attive. → test `tabsAttive` (Task 3).
4. **Ruolo che vede solo voci bloccate** (consulente senza Ambiente): vede "Oggi" e le aree bloccate, nessun errore né pagina vuota. → test `tabsAttive: consulente senza ambiente` (Task 3).
5. **Modulo cambiato su un altro dispositivo**: il cambio arriva anche agli altri (collezione `moduli` fusa dal server). → passo di verifica con due schede (Task 2).

---

### Task 1: Mappa dei moduli

**Files:**
- Create: `src/lib/moduli.ts`
- Test: `src/lib/moduli.test.ts`
- Modify: `package.json` (nessuna modifica se il glob `src/lib/*.test.ts` già lo prende: verificare)

**Interfaces:**
- Produces:
  - `type Modulo = "magazzino" | "accettazione" | "ambiente" | "vendite"`
  - `interface StatoModulo { id: Modulo; attivo: boolean; cambiatoAt?: string; cambiatoDa?: string }`
  - `const MODULI: Record<Modulo, { nome: string; frase: string; punti: string[] }>` (testi dalla tabella "I quattro moduli" dello spec; 3–4 punti ciascuno)
  - `const ORDINE_MODULI: Modulo[]` = `["magazzino", "accettazione", "ambiente", "vendite"]`
  - `function moduloDi(percorso: string): Modulo` (toglie `?…` e `#…`; vince il prefisso più lungo; segmento `*` = qualsiasi segmento; default `"magazzino"`)
  - `function moduliAttivi(stato: StatoModulo[] | undefined): Set<Modulo>` (undefined o modulo assente = attivo; `magazzino` sempre presente)
  - `function attivo(moduli: Set<Modulo>, m: Modulo): boolean`
  - `const WHATSAPP_ATTIVAZIONE: string` (segnaposto `"390000000000"`)
  - `function linkAttivazione(azienda: string, m: Modulo): string` → `https://wa.me/${WHATSAPP_ATTIVAZIONE}?text=${encodeURIComponent(messaggio)}`
  - `function moduliDaArchivio(raw: unknown): Set<Modulo>` (legge `raw.state.moduli` da `state.json`; forma non valida = tutti attivi)

Tabella dei percorsi (`PERCORSI: [prefisso, Modulo][]`):

| Modulo | Prefissi |
|---|---|
| accettazione | `/certificato` |
| ambiente | `/ambiente`, `/veicoli/*/bonifica` |
| vendite | `/vendite`, `/listini` |
| magazzino | tutto il resto (default), compresi `/`, `/veicoli`, `/campo`, `/ricambi`, `/magazzino`, `/inventario`, `/rottami`, `/pubblicazione`, `/regole`, `/scansione`, `/ordini`, `/registro`, `/impostazioni`, `/moduli`, `/negozio`, `/etichetta`, `/etichette-scaffale`, `/documento` (il documento si decide in Task 6 con `moduloDoc`) |

- [ ] **Step 1: Scrivere i test** in `src/lib/moduli.test.ts` (stile di `periodo.test.ts`: `node:test` + `assert/strict`, import con estensione `.ts`):
  - `moduloDi`: `"/ambiente/periodo?mese=2026-10"` → `"ambiente"`; `"/veicoli/V-000118/bonifica"` → `"ambiente"`; `"/veicoli/V-000118"` → `"magazzino"`; `"/veicoli/V-000118#pratica"` → `"magazzino"`; `"/vendite/documenti"` → `"vendite"`; `"/listini"` → `"vendite"`; `"/certificato/V-1"` → `"accettazione"`; `"/ordini"` → `"magazzino"`; `"/"` → `"magazzino"`; `"/venditex"` → `"magazzino"` (prefisso per segmenti, non per caratteri).
  - `moduliAttivi: senza stato salvato sono tutti attivi`: `moduliAttivi(undefined)` ha dimensione 4.
  - `moduliAttivi([{ id: "vendite", attivo: false }, { id: "magazzino", attivo: false }])` contiene `magazzino`, `accettazione`, `ambiente`, non `vendite`.
  - `linkAttivazione("Demo Srl", "accettazione")` = `"https://wa.me/390000000000?text=" + encodeURIComponent("Ciao, sono Demo Srl su AutoLost: vorrei attivare il modulo Accettazione.")`.
  - `moduliDaArchivio(null)` e `moduliDaArchivio({ state: { moduli: "x" } })` → 4 attivi; `moduliDaArchivio({ state: { moduli: [{ id: "accettazione", attivo: false }] } })` → senza `accettazione`.
  - `ogni pagina ha un modulo`: scorre `src/app` con `fs.readdirSync(…, { recursive: true })`, prende ogni `page.tsx`, ricava il percorso (toglie i gruppi `(x)`, sostituisce `[x]`/`[...x]` con `X`) e verifica che `moduloDi` restituisca un valore di `ORDINE_MODULI`; inoltre verifica i casi attesi `"/certificato/X"` → `accettazione` e `"/veicoli/X/bonifica"` → `ambiente`, così una pagina nuova sotto un prefisso sbagliato non passa inosservata.
- [ ] **Step 2:** `npm test` → FAIL (modulo non trovato).
- [ ] **Step 3:** Implementare `src/lib/moduli.ts` come modulo puro (solo `import type`).
- [ ] **Step 4:** `npm test` → PASS.
- [ ] **Step 5: Commit** `git add src/lib/moduli.ts src/lib/moduli.test.ts` · messaggio `Moduli: mappa dei quattro moduli e dei loro percorsi`.

### Task 2: Stato dei moduli nello store, sincronizzazione e controllo sul server

**Files:**
- Modify: `src/lib/store.ts` (State, Actions, `initial()`)
- Modify: `src/lib/sync.ts:10` (`WHOLE`)
- Modify: `src/app/api/demo-state/route.ts:15` (`WHOLE`)
- Create: `src/lib/moduli-server.ts`
- Modify: `src/app/api/visura/route.ts` (POST)
- Create: `src/lib/use-moduli.ts`

**Interfaces:**
- Consumes: `Modulo`, `StatoModulo`, `moduliAttivi`, `moduliDaArchivio` (Task 1).
- Produces:
  - nello State: `moduli: StatoModulo[]` (iniziale: i quattro con `attivo: true`)
  - azione `setModulo(id: Modulo, attivo: boolean): void` — ignora `magazzino`; scrive `cambiatoAt`/`cambiatoDa`; registro attività `{ entity: "sistema", entityId: "modulo-" + id, action: attivo ? "Modulo attivato" : "Modulo disattivato", detail: MODULI[id].nome }`
  - `useModuli(): Set<Modulo>` in `src/lib/use-moduli.ts` (`useStore((s) => s.moduli)` + `useMemo(moduliAttivi)`)
  - `moduloAttivoSulServer(m: Modulo): Promise<boolean>` in `src/lib/moduli-server.ts` (legge `path.join(DATA_DIR, "state.json")`, file assente = attivo)

- [ ] **Step 1:** Aggiungere `moduli` a `WHOLE` in `sync.ts` e in `route.ts` (è un array di oggetti: `sanitize` lo accetta senza cambi). `STORE_SCHEMA` **non** cambia: il merge di `persist` mantiene il valore iniziale per i dati salvati senza `moduli`.
- [ ] **Step 2:** Aggiungere stato, `setModulo` e `useModuli`.
- [ ] **Step 3:** `moduli-server.ts` + in `visura/route.ts` POST, subito dopo il controllo `richiestaDellApp`: se `!(await moduloAttivoSulServer("accettazione"))` → `json({ error: "Il modulo Accettazione non è attivo" }, 403)`.
- [ ] **Step 4:** `npm test` e `npx tsc --noEmit` → verdi.
- [ ] **Step 5: Verifica del server** (server separato, `DATI_DIR` vuoto): scrivere a mano in `$DATI_DIR/state.json` `"moduli":[{"id":"accettazione","attivo":false}]` dentro `state`, poi `curl -X POST localhost:<porta>/api/visura -H 'Origin: http://localhost:<porta>' -H 'Content-Type: application/json' -d '{"targa":"AB123CD"}'` → 403 con "Il modulo Accettazione non è attivo". (La sincronizzazione tra due schede si verifica nel Task 5, quando esiste l'interruttore.)
- [ ] **Step 6: Commit** solo le parti di questo task (`git add -p src/lib/store.ts`, più gli altri file) · `Moduli: stato per azienda, sincronizzazione e visura bloccata senza Accettazione`.

### Task 3: Menu e barra del telefono

**Files:**
- Modify: `src/components/AppShell.tsx`
- Modify: `src/lib/moduli.ts` (+ test)

**Interfaces:**
- Consumes: `useModuli`, `moduloDi`, `attivo`.
- Produces: `function tabsAttive<T extends { area?: string; href?: string }>(tabs: T[], ricambi: T[], aperta: (t: T) => boolean): T[]` in `moduli.ts` — tiene le schede aperte nell'ordine; ogni scheda chiusa è sostituita dalla prima di `ricambi` aperta e non già presente; se non ce n'è, la scheda sparisce.

Cambi al menu (`AREAS`):
- area Ricambi: aggiungere `{ href: "/ordini", label: "Ordini online", roles: ["magazziniere", "responsabile", "vendite"] }` dopo "Pubblicazione", e spostarvi `{ href: "/negozio", label: "Negozio online", … }` dall'area Vendite;
- area Vendite: restano "Banco e ordini" (`/vendite`) e "Documenti";
- area Impostazioni: aggiungere `{ href: "/impostazioni/moduli", label: "Moduli", roles: ["responsabile"] }`.
- Una sottosezione è **bloccata** se `!attivo(moduli, moduloDi(sub.href))`; un'area è bloccata se tutte le sue sottosezioni visibili lo sono. Aree bloccate: in fondo all'elenco, testo `text-white/50`, icona `Lock` di lucide a destra; il link porta comunque alla prima sottosezione (dove comparirà la pagina del modulo bloccato, Task 4). Dentro un'area aperta, le sottosezioni bloccate hanno lo stesso trattamento.
- `MOBILE_TABS`: si passano per `tabsAttive(tabs, ricambi, aperta)` con `ricambi` = le aree visibili e aperte del ruolo in forma di scheda `{ area, label, icon }`. Nel menu "Altro" le aree bloccate compaiono con il lucchetto.

- [ ] **Step 1: Test** in `moduli.test.ts` con oggetti semplici:
  - `tabsAttive` sostituisce la scheda chiusa `{area:"ambiente"}` con la prima di ricambi aperta non presente, mantenendo la posizione;
  - non duplica una scheda già presente;
  - `tabsAttive: consulente senza ambiente`: schede `[{area:"oggi"},{href:"/ambiente/periodo"},{href:"/ambiente"},{href:"/ambiente/formulari"}]`, ricambi `[{area:"oggi"}]`, ambiente chiuso → risultato `[{area:"oggi"}]`.
- [ ] **Step 2:** `npm test` → FAIL. **Step 3:** implementare `tabsAttive`. **Step 4:** `npm test` → PASS.
- [ ] **Step 5:** Applicare i cambi ad `AppShell.tsx`.
- [ ] **Step 6: Verifica nel browser** (server separato): con Ambiente e Vendite spenti, ruolo responsabile: barra laterale con Ambiente e Vendite in fondo con lucchetto; "Ufficio" mostra "Listini" con lucchetto; a 375 px la barra inferiore del responsabile non mostra Vendite; ruolo consulente: solo "Oggi" in barra, nessun errore in console.
- [ ] **Step 7: Commit** · `Moduli: menu con aree bloccate e barra del telefono senza lucchetti`.

### Task 4: Pagina del modulo bloccato e tracce nelle pagine

**Files:**
- Create: `src/components/ModuloBloccato.tsx`
- Create: `src/app/(app)/moduli/[id]/page.tsx`, `view.tsx`
- Modify: `src/components/AppShell.tsx` (gate sul contenuto)
- Modify: `src/app/(app)/ricambi/[id]/view.tsx` (traccia di Vendite)
- Modify: `src/app/certificato/[id]/page.tsx` (o la sua view)
- Create: `public/moduli/accettazione.png`, `ambiente.png`, `vendite.png` (catture dal manuale in `scripts/manuale`, una per modulo; se non disponibili la pagina si mostra senza anteprima)

**Interfaces:**
- Consumes: `MODULI`, `linkAttivazione`, `useModuli`, `moduloDi`, `BRAND.azienda` da `src/lib/config.ts`, `log` dello store.
- Produces:
  - `<ModuloBloccato modulo={m} />`: titolo `MODULI[m].nome`, frase, punti, anteprima sfocata (`blur-sm`, `aria-hidden`), pulsante "Chiedi l'attivazione" = `<a href={linkAttivazione(BRAND.azienda, m)} target="_blank" rel="noopener">` che al clic chiama `log({ entity: "sistema", entityId: "modulo-" + m, action: "Richiesta attivazione modulo", detail: MODULI[m].nome })`.
  - `<Bloccato modulo={m} funzione="Pratica, visura e radiazione PRA">{children}</Bloccato>`: se attivo mostra `children`, altrimenti una riga sobria con `Lock` + `funzione` + link "Scopri il modulo {nome}" a `/moduli/{m}`.
  - Pagina `src/app/(app)/moduli/[id]/page.tsx` (+ `view.tsx`): `<ModuloBloccato modulo={id} />` se il modulo è spento, altrimenti rimanda alla prima voce del modulo; id sconosciuto → `notFound()`. Percorso `/moduli` = magazzino (aggiungere il caso al test del Task 1).
- In `AppShell`, attorno a `{children}`: se `!attivo(moduli, moduloDi(path))` → `<ModuloBloccato modulo={moduloDi(path)} />`.
- Traccia di Vendite nella scheda ricambio (`src/app/(app)/ricambi/[id]/view.tsx:116`): il pulsante che porta al banco (`/vendite?pezzo=…`) diventa `<Bloccato modulo="vendite" funzione="Vendita al banco">`; il link all'ordine (riga 302) punta a `/ordini` per gli ordini non banco.
- Nella pagina di stampa del certificato: stesso controllo prima del contenuto.

- [ ] **Step 1:** Implementare i due componenti e il gate.
- [ ] **Step 2: Verifica nel browser**: con Accettazione spenta aprire a mano `/certificato/V-000118` e con Ambiente spento `/ambiente/periodo` e `/veicoli/V-000118/bonifica` → pagina del modulo bloccato; il pulsante apre `wa.me` con il testo atteso e una riga "Richiesta attivazione modulo" compare in `/registro`.
- [ ] **Step 3: Commit** · `Moduli: pagina del modulo bloccato con richiesta su WhatsApp`.

### Task 5: Impostazioni → Moduli

**Files:**
- Create: `src/app/(app)/impostazioni/moduli/page.tsx`, `view.tsx` (stesso schema `page.tsx` + `view.tsx` delle altre pagine)
- Create: `src/lib/moduli-lavoro.ts`
- Test: `src/lib/moduli-lavoro.test.ts`

**Interfaces:**
- Consumes: `setModulo`, `useModuli`, `MODULI`, `ORDINE_MODULI`; `isDraft` da `src/lib/periodo.ts`; tipi `Order`, `SalesDoc`, `Vehicle`, `WasteMove`.
- Produces: `function lavoroAperto(m: Modulo, s: { orders: Order[]; docs: SalesDoc[]; vehicles: Vehicle[]; wasteMoves: WasteMove[] }): string[]` — righe leggibili, vuoto se nulla:
  - `vendite`: ordini `channel === "banco"` con `status === "in attesa di pagamento"` → `"{n} ordini al banco in attesa di pagamento (i pezzi restano riservati)"`; preventivi `type === "preventivo" && status === "aperto"` → `"{n} preventivi aperti"`;
  - `accettazione`: veicoli con `conferente` o `presaInCarico` e `radiazione?.stato !== "completata"` → `"{n} pratiche non concluse"`;
  - `ambiente`: `wasteMoves.filter(isDraft)` → `"{n} registrazioni in bozza nel registro rifiuti"`;
  - `magazzino`: sempre `[]`.
  - Singolare quando n = 1 ("1 ordine al banco…", "1 preventivo aperto", "1 pratica non conclusa", "1 registrazione in bozza…").

Pagina: una riga per modulo in `ORDINE_MODULI` con nome, frase, interruttore (il Magazzino acceso e disattivato, con scritta "Sempre incluso"). Spegnendo un modulo con `lavoroAperto` non vuoto: `confirm()` con le righe e "I dati restano salvati e tornano visibili riattivando il modulo." In testa un `Notice` "Pagina provvisoria: con il login gli interruttori passeranno all'amministratore della piattaforma."

- [ ] **Step 1: Test** `lavoroAperto` con dati minimi per ciascun caso, compresi i singolari e il caso vuoto.
- [ ] **Step 2:** `npm test` → FAIL. **Step 3:** implementare. **Step 4:** `npm test` → PASS.
- [ ] **Step 5:** Implementare la pagina.
- [ ] **Step 6: Verifica nel browser**: spegnere Vendite con un ordine al banco in attesa (crearne uno) → la conferma elenca la riga; dopo la conferma il menu mostra Vendite bloccato e `/registro` riporta "Modulo disattivato". **Due schede** sullo stesso server: il cambio fatto nella scheda A compare nel menu della scheda B entro ~3 s.
- [ ] **Step 7: Commit** · `Moduli: pagina di attivazione con avviso sul lavoro aperto`.

### Task 6: Ordini online nel base e documenti per modulo

**Files:**
- Create: `src/components/OrdiniPanel.tsx` (estratto dal pannello "Ordini" di `src/app/(app)/vendite/view.tsx:213-298`)
- Create: `src/app/(app)/ordini/page.tsx`, `view.tsx`
- Modify: `src/app/(app)/vendite/view.tsx`
- Modify: `src/app/documento/[id]/…` (gate per modulo del documento)
- Modify: `src/lib/moduli.ts` (+ test)

**Interfaces:**
- Produces:
  - `<OrdiniPanel canali="online" | "tutti" />`: con `"online"` esclude `channel === "banco"` e il filtro canale non offre "Banco". Stessi pulsanti di oggi (Pagato, Spedito/Consegnato, Emetti scontrino, Emetti fattura, Registra reso, Segna come gestito) e stesso messaggio di esito.
  - `/ordini`: `PageTitle` "Ordini online", sottotitolo "eBay e negozio online: prepara, spedisci, emetti il documento e registra i resi." + `<OrdiniPanel canali="online" />`.
  - `/vendite`: banco + `<OrdiniPanel canali="tutti" />`.
  - `function moduloDoc(d: Pick<SalesDoc, "type" | "orderId">, orders: Pick<Order, "id" | "channel">[]): Modulo` in `moduli.ts`: preventivo → `vendite`; con `orderId` di un ordine `banco` → `vendite`; con `orderId` di un ordine non banco → `magazzino`; senza ordine → `vendite`.
- `/documento/[id]`: se `!attivo(moduli, moduloDoc(doc, orders))` → `<ModuloBloccato modulo="vendite" />`.

- [ ] **Step 1: Test** `moduloDoc` per i quattro casi.
- [ ] **Step 2:** `npm test` → FAIL. **Step 3:** implementare. **Step 4:** `npm test` → PASS.
- [ ] **Step 5:** Estrarre `OrdiniPanel`, creare `/ordini`, aggiornare `/vendite` e il gate del documento.
- [ ] **Step 6: Verifica nel browser** con Vendite spento: `/ordini` mostra gli ordini eBay e negozio, "Emetti fattura" produce il documento e `/documento/<id>` lo stampa; un documento del banco aperto a mano mostra il modulo bloccato.
- [ ] **Step 7: Commit** · `Moduli: ordini online con documenti e resi nel Magazzino`.

### Task 7: "Oggi" e ricerca per modulo

**Files:**
- Modify: `src/lib/agenda.ts`
- Test: `src/lib/agenda.test.ts` (nuovo)
- Modify: `src/app/(app)/view.tsx` (riga 44)
- Modify: `src/components/GlobalSearch.tsx`

**Interfaces:**
- Consumes: `moduloDi`, `attivo`, `useModuli`.
- Produces: `function filtraAgenda(items: AgendaItem[], moduli: Set<Modulo>): AgendaItem[]` in `agenda.ts`:
  - modulo della voce: `kind === "pratica"` → `accettazione`; altrimenti `moduloDi(href)`;
  - voci della bonifica (`href` che finisce con `/bonifica`) con Ambiente spento: restano, con `href` = `/veicoli/{id}` (la casella "Bonificato il …" del Task 8);
  - le altre voci di moduli spenti si tolgono.
- In `buildAgenda`, gli ordini non banco puntano a `/ordini`, quelli banco a `/vendite` (oggi tutti `/vendite`: righe 237, 251, 262).
- Ricerca: ordini → `href` come sopra; documenti → si mostrano solo se `attivo(moduli, moduloDoc(d, orders))`; ogni altro risultato si mostra solo se `attivo(moduli, moduloDi(href))`.

- [ ] **Step 1: Test** `filtraAgenda`: voce `kind:"pratica"` tolta senza Accettazione; voce `/ambiente/periodo?mese=…` tolta senza Ambiente; voce `/veicoli/V-1/bonifica` senza Ambiente resta con `href` `/veicoli/V-1`; voce `/ordini` resta con tutto spento tranne Magazzino; voce `/vendite` tolta senza Vendite. Più un test di `buildAgenda` che un ordine eBay pagato abbia `href` `/ordini`.
- [ ] **Step 2:** `npm test` → FAIL. **Step 3:** implementare. **Step 4:** `npm test` → PASS.
- [ ] **Step 5:** Usare `filtraAgenda` nella pagina "Oggi" e filtrare la ricerca.
- [ ] **Step 6: Commit** · `Moduli: coda Oggi e ricerca senza voci dei moduli spenti`.

### Task 8: Scheda veicolo, bonifica e smontaggio per combinazione

**Files:**
- Modify: `src/lib/types.ts` (`Bonifica`)
- Modify: `src/lib/store.ts` (due azioni)
- Create: `src/lib/dati-registro.ts`
- Test: `src/lib/dati-registro.test.ts`
- Modify: `src/app/(app)/veicoli/[id]/view.tsx`
- Modify: `src/app/(app)/campo/[id]/view.tsx:46-50`
- Modify: `src/app/(app)/veicoli/nuovo/view.tsx:218` (testo che rimanda alla pratica)

**Interfaces:**
- Consumes: `useModuli`, `<Bloccato>`, `completeDraft` (`store.ts`).
- Produces:
  - `Bonifica.semplice?: boolean` (bonifica segnata senza materiali: nessun movimento nel registro).
  - azione `segnaBonificata(vehicleId: string, at: string): void` → `bonifica: { at, by: utente del ruolo, items: [], residualKg: 0, semplice: true }`, registro attività "Bonifica segnata come fatta".
  - `function datiRegistroErrori(d: { nome: string; cf: string; numero: string; data: string }): string[]` in `dati-registro.ts`: nome vuoto → "Scrivi chi ha consegnato il veicolo"; cf non conforme a `/^(IT)?\d{11}$|^[A-Z0-9]{16}$/` (dopo `toUpperCase` e senza spazi) → "Codice fiscale (16 caratteri) o partita IVA (11 cifre) non valido"; numero vuoto → "Scrivi il numero del certificato di rottamazione"; data non valida o futura → "Data del certificato non valida".
  - azione `setDatiRegistro(vehicleId: string, d: { nome: string; cf: string; numero: string; data: string }): Result` → errori di `datiRegistroErrori` come `{ ok: false, error }`; altrimenti aggiorna il veicolo (`conferente: { tipo: "privato", nome, cf }`, `dossier.number = numero`, `presaInCarico: { at: data, by }`) e, se il carico `*T` del veicolo (`origin === vehicleId`) è in bozza, chiama `completeDraft(id, { produttoreNome: nome, produttoreCf: cf, certificato: { numero, data } })`.

Comportamento della scheda veicolo:
- **Pannello Bonifica**: con Ambiente attivo com'è oggi. Senza Ambiente: se non bonificato, pulsante "Bonificato oggi" (`segnaBonificata(id, now)`) e la riga `<Bloccato modulo="ambiente" funzione="Materiali tolti e registro rifiuti">`; se bonificato, "Bonificato il {data} · {chi}". Il pannello ha `id="bonifica"`.
- **Pratica**: `<Bloccato modulo="accettazione" funzione="Pratica, visura e radiazione PRA"><PraticaPanel v={v} /></Bloccato>`.
- **Dati per il registro**: solo con Ambiente attivo **e** Accettazione spenta; quattro campi (chi consegna, codice fiscale, numero del certificato, data) precompilati dal veicolo, pulsante "Salva", errori sotto i campi.
- **Smontaggio** (`campo/[id]`): il richiamo "Bonifica non ancora registrata" punta a `/veicoli/{id}#bonifica` se Ambiente è spento.
- Peso: nessun cambio (`weightKg` è già il peso alla pesa e `pesoPesa` ne deriva).

- [ ] **Step 1: Test** `datiRegistroErrori`: caso valido → `[]`; ognuno dei quattro errori; cf con spazi e minuscole accettato; partita IVA `IT01234567890` accettata.
- [ ] **Step 2:** `npm test` → FAIL. **Step 3:** implementare `dati-registro.ts`, il campo `semplice` e le due azioni. **Step 4:** `npm test` → PASS.
- [ ] **Step 5:** Aggiornare scheda veicolo, smontaggio e nuovo ingresso.
- [ ] **Step 6: Verifica nel browser**, tre combinazioni: (a) solo Magazzino: nuovo veicolo → "Bonificato oggi" → "Avvia smontaggio" attivo; nessun pannello pratica, solo la traccia. (b) Magazzino + Ambiente: "Dati per il registro" compilati → in `/ambiente/periodo` il carico del veicolo non è più in bozza. (c) tutto attivo: scheda identica a prima.
- [ ] **Step 7: Commit** solo le parti del task · `Moduli: scheda veicolo che funziona con ogni combinazione di moduli`.

### Task 9: Collegamenti per modulo

**Files:**
- Modify: `src/lib/collegamenti.ts`
- Modify: `src/app/(app)/impostazioni/collegamenti/view.tsx`
- Test: `src/lib/moduli.test.ts` (aggiunta)

**Interfaces:**
- Produces: `Servizio.modulo: Modulo` e `Servizio.opzioniModulo?: Record<string, Modulo>`.

Assegnazione: `rvfu` accettazione · `rentri` ambiente · `mud` ambiente · `agenzia-entrate` vendite · `orso` ambiente · `firma` accettazione · `rt` vendite · `openapi` magazzino con `opzioniModulo: { "Visura PRA": "accettazione", "Firma elettronica": "accettazione" }` · `platerecognizer` magazzino (uso: "Ingresso veicolo: lettura della targa dalla foto") · `ia` magazzino · `sendcloud` magazzino (uso: "Ordini online: etichette di spedizione") · `ebay` magazzino (uso: "Pubblicazione: annunci su eBay Italia") · `whatsapp` magazzino · `visurenet` accettazione.

Nella pagina: un servizio di un modulo spento mostra la scheda chiusa con `<Bloccato modulo={s.modulo} funzione={s.nome}>`; dentro la scheda Openapi, le opzioni di un modulo spento compaiono disattivate con il lucchetto.

- [ ] **Step 1: Test** `ogni servizio ha un modulo`: `SERVIZI.every((s) => ORDINE_MODULI.includes(s.modulo))` e le chiavi di `opzioniModulo` di Openapi sono tra le sue opzioni `servizi`.
- [ ] **Step 2:** `npm test` → FAIL. **Step 3:** implementare. **Step 4:** `npm test` → PASS.
- [ ] **Step 5:** Aggiornare la pagina; verifica nel browser con Accettazione spenta (RVFU chiuso, "Visura PRA" bloccata dentro Openapi).
- [ ] **Step 6: Commit** · `Moduli: collegamenti divisi per modulo`.

### Task 10: Roadmap e pagina di presentazione

**Files:**
- Modify: `docs/ROADMAP.md` (principio 5 e voce H4)
- Modify: `src/app/scopri/…` (sezione dell'offerta)

- [ ] **Step 1:** Principio 5 della roadmap: "Ognuno vede il suo lavoro. … I moduli non acquistati compaiono bloccati, con la spiegazione e la richiesta d'attivazione." H4 segnata come fatta nel paragrafo "Già nel prototipo".
- [ ] **Step 2:** In `/scopri`, al posto del solo "8% online, 0 al banco": blocco "Come si compra" con Magazzino (base, comprende la pubblicazione online con l'8% sul venduto) e i tre moduli aggiuntivi, ciascuno con `MODULI[m].frase`. Nessun prezzo.
- [ ] **Step 3: Verifica nel browser** di `/scopri` a 375 px e su desktop.
- [ ] **Step 4: Commit** · `Moduli: roadmap e pagina di presentazione con l'offerta a moduli`.

### Dopo l'ultimo task (sessione principale, non un sotto-agente)

- Aggiornare il manuale operativo su Claude Docs indicando per ogni capitolo il modulo a cui appartiene.
- Ricordare ad Alessandro: numero WhatsApp da mettere in `WHATSAPP_ATTIVAZIONE`.
