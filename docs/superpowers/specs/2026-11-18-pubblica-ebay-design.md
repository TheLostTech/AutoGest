# Pubblica su eBay e annunci con più pezzi: progetto

18/11/2026 · prototipo. eBay è simulato finché in Collegamenti non ci sono le chiavi di prova; con le chiavi pubblica davvero nella **sandbox** di eBay Italia. La produzione eBay non fa parte di questo giro.

## Perché
L'autodemolizione deve vendere i ricambi online senza riscrivere ogni volta l'annuncio a mano. Il gestionale ha già tutto: tipo di pezzo, veicolo d'origine, codice originale, condizione, foto, prezzo. Con un tocco l'annuncio deve finire sul profilo eBay dell'azienda e sul negozio online. Ogni annuncio online rende a noi la commissione dell'8% (vedi `src/lib/pricing.ts`, `ONLINE_FEE_PCT`).

Ricerca su API, obblighi e limiti: `docs/INTEGRAZIONI.md`, sezione "eBay: dal ricambio all'annuncio con un tocco".

## Obiettivi
1. **Annuncio scritto in automatico** dai dati del gestionale: titolo, descrizione, categoria, caratteristiche, veicoli compatibili, foto, prezzo con l'8%. L'operatore vede l'anteprima, corregge se vuole, tocca "Pubblica".
2. **Un annuncio per più pezzi uguali.** Quando entra un pezzo uguale a uno già online, il gestionale lo aggiunge da solo all'annuncio esistente: la quantità sale di uno, su eBay e sul negozio.
3. **L'annuncio non si chiude mai da solo a zero pezzi.** Resta visibile come "esaurito" (sul negozio con il numero da chiamare) e si riattiva al primo pezzo uguale che entra.
4. **Una sola giacenza per tutti i canali.** Banco, negozio ed eBay non vendono mai lo stesso pezzo fisico due volte. Una vendita su eBay segna "venduto" nel gestionale; una vendita al banco abbassa la quantità su eBay.
5. **Simulato o sandbox con lo stesso codice.** Il "ponte eBay" sul server ha due modi: simulato (risposte finte, nessuna chiamata esterna) e sandbox (API vere di eBay, ambiente di prova). Si passa dall'uno all'altro in Collegamenti.

## Non obiettivi (ora)
- eBay in produzione (account veri dei clienti).
- Compatibilità per KType e banche dati a licenza (TecDoc): si usano marca, modello, anno, motore.
- Testo scritto da un modello IA vero: in questo giro un generatore a regole, con il punto pronto per collegare l'IA più avanti (Collegamenti → "IA").
- Altri marketplace (Ovoko e altri): il modello dei canali li deve permettere, ma non si costruiscono.
- Più unità dello stesso annuncio in un ordine **del negozio**: lì ogni ordine prende al massimo un pezzo per annuncio. Su eBay invece l'acquirente può comprarne più di uno (vedi 4).
- Notifiche push di eBay (webhook): le vendite si leggono controllando eBay a intervalli.
- Resi, messaggi degli acquirenti eBay, etichette di spedizione, tariffe eBay a video.
- Fatturazione della commissione dell'8% all'autodemolizione.

## Anti-obiettivi (sarebbe un fallimento anche se funziona)
- Lo stesso pezzo fisico venduto su due canali.
- Un annuncio che sparisce da solo quando i pezzi finiscono.
- Un prezzo online senza l'8%, o diverso tra negozio ed eBay.
- Credenziali o token eBay che arrivano al browser.
- Due pezzi uniti nello stesso annuncio senza codice originale verificato.
- Un pezzo che va online senza passare i controlli di oggi (`publishChecks` in `src/lib/logic.ts`).

## Vincoli
- **Next.js 16.4** con modifiche rispetto alle versioni note: prima di scrivere route handler leggere la guida in `node_modules/next/dist/docs/` (vedi `AGENTS.md`).
- **Architettura del prototipo:** lo stato vive nello store dell'app (`src/lib/store.ts`, zustand) ed è condiviso tra dispositivi tramite `/api/demo-state` (`src/lib/sync.ts`, elenchi in `SHARED`). Il server tiene solo file nella cartella dati (`src/lib/server-data.ts`).
- **Credenziali:** come gli altri collegamenti (`src/app/api/collegamenti/route.ts`): cifrate sul server, il browser vede solo se ci sono.
- **Nessun login nel prototipo** (scelta di Alessandro, rimandata). Le nuove API del server applicano lo stesso blocco delle richieste da altri siti usato in `collegamenti/route.ts`.
- **eBay (verificato il 18/11/2026):**
  - Inventory API: `createOrReplaceInventoryItem` (SKU) → `createOffer` → `publishOffer`. Alla pubblicazione servono condizioni di vendita (`fulfillmentPolicyId`, `paymentPolicyId`, `returnPolicyId`) e `merchantLocationKey`.
  - Compatibilità: `createOrReplaceProductCompatibility` con `compatibilityProperties` (nomi e valori dalla Taxonomy API, `getCompatibilityProperties` / `getCompatibilityPropertyValues`, eBay Italia = albero 101).
  - Foto: Media API `createImageFromFile`, che restituisce l'URL da usare nell'annuncio; 50 caricamenti ogni 5 secondi.
  - **Quantità zero:** con l'opzione "esaurito" attiva sull'account, l'annuncio resta attivo ma nascosto dalla ricerca; dopo circa 90 giorni a zero eBay lo chiude. Senza l'opzione, eBay rifiuta la quantità zero. L'opzione si attiva con la Trading API `SetUserPreferences` (`OutOfStockControlPreference`).
  - OAuth "authorization code grant": token di 2 ore, rinnovo per circa 18 mesi. L'indirizzo di ritorno deve essere https: si usa il tunnel del prototipo.
  - Vendite: Fulfillment API `getOrders`, filtrate per data.
  - GPSR: i pezzi messi sul mercato UE prima del 13/12/2024 non richiedono i dati del produttore (art. 51, interpretazione eBay). I campi esistono in `regulatory.manufacturer`.
- **Testi in italiano semplice**, come il resto del gestionale. Componenti in `src/components/ui.tsx`.

## Strade valutate
1. **Il gestionale avvisa eBay a ogni cambiamento** (scelta di Alessandro). A ogni cambiamento di un annuncio l'app manda al ponte la situazione completa (quantità, prezzo, testo, foto, compatibilità); il ponte la riporta su eBay così com'è, quindi ripetere l'invio non fa danni. Se fallisce, l'annuncio resta "da riallineare" e riparte. Le vendite eBay si leggono a intervalli mentre l'app è aperta. Segue l'architettura attuale; il ponte è lo stesso che servirà in produzione.
2. Il server tiene eBay allineato da solo, confrontando di continuo l'archivio con eBay. Giusta per il prodotto finale, ma oggi la logica dei pezzi vive nell'app: andrebbe spostata. Scartata per ora; passare alla 2 vuol dire spostare la logica, non riscriverla.
3. Collegamento solo simulato: scartato, perché non arriva mai alla sandbox (Alessandro ha scelto simulato **e** sandbox).

## Cosa si costruisce

### 1. L'annuncio, una cosa a sé
Oggi lo stato online sta nel singolo pezzo (`Part.listing`). Un annuncio a zero pezzi non avrebbe dove stare, quindi nasce un nuovo elenco **`annunci`** nello store, condiviso tra dispositivi come `parts` (aggiungerlo a `SHARED` in `sync.ts`).

Ogni annuncio ha:
- codice `A-000001` (nuovo contatore);
- chiave di raggruppamento, se c'è (vedi sotto);
- tipo di pezzo, lato, condizione, codice originale;
- **prezzo base** dell'autodemolizione (quello online si calcola con `onlinePrice`);
- titolo, descrizione, categoria eBay e caratteristiche: generati, ma modificabili dall'operatore;
- veicoli compatibili;
- stato per canale: **negozio** (`online` · `esaurito` · `ritirato`) ed **eBay** (`non pubblicato` · `in pubblicazione` · `online` · `esaurito` · `chiuso da eBay` · `ritirato` · `errore`), con numero dell'annuncio eBay, link, ultima quantità e ultimo prezzo inviati, segno "da riallineare" ed eventuale errore;
- date di creazione e dell'ultima volta a zero.

Ogni pezzo pubblicato punta al suo annuncio (`Part.annuncioId`). Anche un pezzo senza codice verificato ha il suo annuncio, con un solo pezzo.

**Valori calcolati, non salvati:**
- *quantità* = pezzi dell'annuncio in stato `disponibile` (i `riservato` non contano);
- *prossimo a partire* = il pezzo disponibile entrato per primo in magazzino (`createdAt` più vecchio);
- *foto dell'annuncio* = le foto del prossimo a partire, che cambiano quando quel pezzo si vende.

`Part.listing` va sostituito dall'appartenenza all'annuncio. Le schermate che oggi lo usano (chip "online", percorso del pezzo, contatori della home, ordini, scarto) devono continuare a dire la stessa cosa: un pezzo è "online" se è disponibile e il suo annuncio è online su almeno un canale. Come migrare lo lascio a chi costruisce (vedi in fondo).

### 2. Quando due pezzi sono uguali
Si uniscono solo pezzi con **stesso tipo, stesso codice originale verificato (`oemVerified`), stesso lato, stessa condizione e stessa scelta di spedizione** (vedi 2 bis). Il codice si confronta normalizzato: maiuscolo, senza spazi, punti e trattini. Senza codice verificato la chiave non esiste e il pezzo ha sempre il suo annuncio.

### 2 bis. Spedizione sì o no, pezzo per pezzo (decisione di Alessandro)
Oggi la spedizione dipende solo dal tipo di pezzo (`shippable` in `catalog.ts`): motore, cambio, batteria, porta, cofano e paraurti sono sempre "solo ritiro in sede". D'ora in poi per questi tipi si decide **pezzo per pezzo**:
- **Alla creazione del pezzo in magazzino** la schermata chiede "Si può spedire?" con due scelte grandi: **Sì, con corriere** · **No, solo ritiro in sede**. Già scelto "No", come oggi. Vale nei tre punti dove nasce un pezzo: smontaggio (`campo/[id]/nuovo`), nuovo pezzo in inventario (`inventario/[mag]/nuovo`) e conta (`inventario/conta`).
- Per i tipi già spedibili la domanda non compare: restano sempre spedibili.
- La scelta si può cambiare dalla scheda del ricambio.
- Nuovo campo del pezzo (es. `Part.spedibile`). Chi vende guarda **il pezzo, non il tipo**: negozio, carrello, anteprima e controlli di pubblicazione, eBay. Il suggerimento del magazzino in cui riporlo resta invece legato al tipo, perché dipende dall'ingombro.
- **Fa parte della chiave di raggruppamento:** due porte uguali, una spedibile e una no, stanno in due annunci diversi.
- **Su eBay** tutti i pezzi vanno online. Il ponte sceglie da solo tra tre condizioni di spedizione dell'account: **corriere** (pezzi normali), **corriere voluminoso** (pezzi ingombranti segnati spedibili: altro prezzo, anche su bancale) e **solo ritiro in sede**. *(Scelta mia: una porta spedita al prezzo di un alternatore sarebbe una perdita.)* I prezzi di spedizione li fissa l'autodemolizione nelle condizioni del suo account eBay. In Collegamenti si scelgono le tre condizioni; in sandbox, se mancano, il ponte le crea.

### 3. Il percorso di un pezzo
1. Il pezzo diventa `disponibile` e passa i controlli di pubblicazione.
2. **Esiste un annuncio con la stessa chiave** (in qualsiasi stato tranne "ritirato" dall'operatore):
   - **prezzo uguale** a quello dell'annuncio → il pezzo si aggiunge da solo, senza tocchi. L'annuncio sale di un'unità; se era esaurito torna online; se eBay l'aveva chiuso, si ripubblica con lo stesso testo.
   - **prezzo diverso** → il pezzo resta nella coda di Pubblicazione con l'avviso "Prezzo diverso dall'annuncio A-…: 95 € contro 90 €" e due scelte: tenere il prezzo dell'annuncio (il pezzo si allinea) o usare quello nuovo (cambia il prezzo dell'annuncio su tutti i canali).
   - **annuncio ritirato dall'operatore** → nessuna unione automatica. La coda propone "Ripubblica l'annuncio A-…".
3. **Nessun annuncio uguale** → il pezzo resta in coda e l'operatore tocca "Pubblica": si apre l'anteprima e si sceglie su quali canali andare (negozio, eBay; di serie tutti e due se eBay è collegato).

Il prezzo dell'annuncio è uno solo. Unendo un pezzo, il suo prezzo si allinea a quello dell'annuncio.

**Modifiche a un pezzo già dentro un annuncio** *(scelta mia, dopo la revisione)*:
- **Prezzo:** i pezzi uguali hanno un prezzo solo, anche al banco. Cambiare il prezzo dalla scheda di un pezzo cambia il prezzo dell'annuncio e di tutti i suoi pezzi. La scheda lo dice prima di salvare: "Cambia il prezzo di tutti e 3 i pezzi dell'annuncio A-…". Anche "usa quello nuovo" nella coda (vedi sopra) riallinea il prezzo di tutti i pezzi.
- **Codice originale, lato, condizione, verifica del codice o spedizione:** se cambia la chiave, il pezzo esce dall'annuncio e torna nella coda di Pubblicazione, dove segue il percorso normale (si unisce a un altro annuncio uguale, oppure ne nasce uno nuovo). L'annuncio di prima perde un'unità. Per un annuncio con un solo pezzo, invece, cambia l'annuncio stesso.
- **Pezzo che esce per qualsiasi motivo** (scartato, invendibile, chiave cambiata): l'annuncio resta, con un'unità in meno.

### 4. Vendite e giacenza unica
- **Negozio:** il carrello contiene annunci, non pezzi. Alla conferma dell'ordine lo store riserva il prossimo a partire, nello stesso aggiornamento che controlla la disponibilità (come `createOrder` oggi). Prezzo = `onlinePrice` del prezzo dell'annuncio.
- **eBay:** le vendite arrivano dal ponte (vedi 6) con SKU = codice annuncio e quantità comprata. Per ognuna l'app crea un ordine canale `marketplace` già pagato, che prende **tanti pezzi quanti ne sono stati comprati**, in ordine di entrata in magazzino, al prezzo pagato su eBay. Un'officina può comprare tre iniettori uguali in un colpo solo. Se i pezzi disponibili sono meno di quelli comprati (venduti nel frattempo altrove), l'ordine prende quelli che ci sono, viene segnato **"da gestire: mancano N pezzi"** e compare nella coda Da fare. *(Scelta mia, dopo la revisione.)*
- **Banco e qualsiasi cambio di stato** (venduto, riservato, scartato, invendibile, di nuovo disponibile) ricalcolano la quantità dell'annuncio e lo segnano "da riallineare".
- **A zero:** negozio → stato `esaurito`; eBay → quantità 0, l'annuncio resta (nascosto da eBay). Se eBay lo chiude dopo circa 90 giorni, lo stato diventa `chiuso da eBay` e al primo pezzo nuovo si ripubblica.

### 5. Il testo scritto in automatico
Funzioni pure in `src/lib` (da testare), dai dati dei pezzi e del veicolo d'origine:
- **Titolo** (massimo 80 caratteri, limite di eBay): tipo di pezzo + lato + marca e modello (versione se c'è spazio) + anni + codice originale + "usato". Si accorcia togliendo prima la versione, poi gli anni; il codice originale resta.
- **Descrizione:** condizione con la sua spiegazione, eventuali difetti, km del veicolo d'origine, veicolo d'origine, codice originale, "pezzo controllato e catalogato con codice univoco", spedizione o solo ritiro. Con più pezzi niente km o difetti del singolo: solo la condizione comune, e "le foto mostrano il pezzo che riceverai" vale per il prossimo a partire.
- **Categoria eBay:** tabella tipo di pezzo → categoria eBay Italia, nel codice. In sandbox il ponte può chiedere conferma alla Taxonomy API (`getCategorySuggestions`); l'operatore può cambiarla nell'anteprima.
- **Caratteristiche eBay:** marca, numero ricambio del produttore (codice originale), posizione sul veicolo (lato), tipo. In sandbox il ponte chiede alla Taxonomy API quali sono obbligatorie per la categoria; quelle mancanti si mostrano nell'anteprima come da completare.
- **Veicoli compatibili:** il veicolo d'origine di ogni pezzo (marca, modello, anno, motore ricavato dalla versione) più, se la compatibilità è verificata, le piattaforme di `compat.platforms` (marca, modello e anni da `PLATFORMS` in `catalog.ts`). In sandbox il ponte traduce questi valori in quelli di eBay con `getCompatibilityPropertyValues`. Quelli non riconosciuti si mostrano come avviso, ma non bloccano la pubblicazione.
- **Quando il testo si riscrive** *(scelta mia, dopo la revisione)*: titolo e descrizione si generano alla creazione dell'annuncio, dal **primo pezzo**: marca e modello del titolo sono quelli del suo veicolo d'origine. L'annuncio ricorda se l'operatore li ha modificati. Se non sono stati modificati, si rigenerano quando cambiano i pezzi (per esempio nella descrizione "disponibili da più veicoli"). Se sono stati modificati, non si toccano più da soli. Nell'anteprima c'è il pulsante "Riscrivi in automatico". L'elenco dei veicoli compatibili invece si aggiorna sempre: è l'unione dei veicoli d'origine e delle piattaforme verificate di tutti i pezzi, anche di quelli venduti.
- **GPSR:** veicolo d'origine immatricolato prima del 13/12/2024 → nessun dato del produttore. Dopo → produttore = casa auto, da una tabella marca → ragione sociale e sede UE nel codice. Pezzo senza anno del veicolo → nell'anteprima l'operatore conferma "pezzo messo in commercio prima del 13/12/2024" oppure indica il produttore.

### 6. Il ponte eBay sul server
Route sotto `/api/ebay/` (nomi definitivi a chi costruisce). Le credenziali le legge dall'archivio di Collegamenti; un file suo nella cartella dati tiene token, data dell'ultimo controllo delle vendite e URL delle foto già caricate.

- **Allinea un annuncio:** riceve la situazione completa (SKU = codice annuncio, quantità, prezzo online, titolo, descrizione, categoria, caratteristiche, condizione, foto, compatibilità, dati GPSR, canale attivo o ritirato) e la porta su eBay. Restituisce stato, numero annuncio, link, errore.
  - *Sandbox:* `createOrReplaceInventoryItem`, poi compatibilità, poi offerta creata o aggiornata, poi pubblicazione se serve. A quantità zero aggiorna e basta. Se l'annuncio era chiuso, ripubblica. Se l'annuncio è ritirato, `withdrawOffer`. Prima di pubblicare carica le foto con la Media API (lette dalla cartella foto o da `public/`), una volta sola per foto.
  - *Simulato:* risponde dopo un attimo con un numero finto e un link a una pagina "annuncio eBay simulato" del prototipo che mostra titolo, foto, prezzo e quantità. Per provare gli errori: un prezzo che finisce in ,13 restituisce un errore finto.
- **Controlla vendite:** restituisce le vendite nuove dall'ultimo controllo (sandbox: `getOrders`). In simulato non ne arrivano da sole: c'è il pulsante "Simula vendita su eBay" sull'annuncio.
- **Collega account:** avvia OAuth e riceve il ritorno, salva il token cifrato, attiva l'opzione "esaurito" (`SetUserPreferences`) e legge condizioni di vendita e magazzini dell'account. Se mancano, li crea con valori di base, solo in sandbox.

Ripetere la stessa richiesta non deve creare doppioni: per eBay lo SKU è il codice annuncio.

**Riallineamento nell'app:** ogni modifica che tocca un annuncio online su eBay lo segna "da riallineare". Un piccolo esecutore nell'app manda al ponte gli annunci segnati, uno alla volta: subito dopo la modifica, all'apertura dell'app e ogni minuto finché ne restano. Se più dispositivi mandano lo stesso annuncio non succede nulla, perché la richiesta è sempre completa. Il controllo delle vendite parte ogni 5 minuti mentre l'app è aperta (solo sandbox) e c'è anche un pulsante "Controlla vendite eBay".

### 7. Schermate
- **Collegamenti → eBay** (nuova voce in `SERVIZI`, gruppo "consumo"): modo (Simulato · Sandbox), App ID, Cert ID (segreto), RuName, pulsante "Collega account eBay", poi stato del collegamento, condizioni di vendita (pagamento, reso e le tre di spedizione: corriere, corriere voluminoso, solo ritiro) e magazzino scelti da elenco, stato dell'opzione "esaurito". Nota su costi e commissione eBay come nella ricerca.
- **Pubblicazione:**
  - *coda* dei pezzi non ancora in un annuncio, con i controlli di oggi e gli avvisi nuovi (prezzo diverso, annuncio ritirato da ripubblicare);
  - *anteprima* con titolo e descrizione modificabili, categoria, caratteristiche (mancanti evidenziate), veicoli compatibili (non riconosciuti evidenziati), foto, prezzo base e prezzo online con l'8%, scelta dei canali, pulsante "Pubblica";
  - *elenco annunci* con quantità, stato per canale, link a eBay, "da riallineare" ed errori, e le azioni modifica testo, ritira, ripubblica, "Simula vendita su eBay" (solo in simulato).
- **Scheda ricambio:** riga "Annuncio A-000123 · 3 disponibili · negozio online · eBay online" con i link, accanto alla riga "Online (+8%)" già presente.
- **Negozio online:** elenca annunci, non pezzi. Disponibili in alto. Esauriti in una sezione in fondo, così restano raggiungibili anche da Google: la loro pagina dice "Esaurito: chiamaci per questo pezzo o per altri dello stesso veicolo" con telefono (nuovo campo `telefono` in `BRAND`, `src/lib/config.ts`) e un modulo "avvisami quando torna" solo simulato. La pagina dell'annuncio mostra la quantità disponibile. Il vecchio indirizzo `/negozio/R-…` porta all'annuncio del pezzo.
- **Vendite:** gli ordini eBay compaiono con canale "eBay" e numero d'ordine eBay; quelli "da gestire" in evidenza.
- **Registro attività:** ogni azione sugli annunci (creato, pezzo aggiunto, prezzo cambiato, pubblicato o ritirato per canale, esaurito, chiuso da eBay, errore, vendita eBay) entra nel registro come gli altri eventi.

### 8. Prove
- Test con `node --test` per le funzioni pure: chiave di raggruppamento, scelta dell'annuncio per un pezzo nuovo (compresi prezzo diverso e annuncio ritirato), quantità, prossimo a partire, titolo entro 80 caratteri e accorciamento, regola GPSR, situazione completa inviata al ponte, ponte simulato.
- Prova nel browser in modo simulato:
  1. due pezzi uguali → un annuncio con quantità 2;
  2. vendita al banco → quantità 1 su eBay;
  3. "Simula vendita su eBay" → il pezzo giusto diventa venduto e l'annuncio va a esaurito;
  4. nuovo pezzo uguale → torna online.
- La prova in sandbox la fa Alessandro, quando ha l'account sviluppatore.

## Lasciato a chi costruisce
- Come migrare da `Part.listing` all'annuncio, e come ricreare i dati demo (nuova versione di `STORE_SCHEMA`, annunci ricavati dai pezzi oggi pubblicati).
- Nomi delle route e dei file, impaginazione delle schermate, testi esatti.
- Tabella tipo di pezzo → categoria eBay e tabella marca → produttore (valori da verificare in sandbox).
- Intervalli esatti di riallineamento e di controllo vendite.
- Gestione dei singoli errori eBay, mostrati con parole semplici.
