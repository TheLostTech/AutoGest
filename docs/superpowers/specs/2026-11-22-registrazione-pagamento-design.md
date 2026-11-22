# Registrazione libera e pagamento con Stripe

Data: 22/11/2026. Fa seguito a [moduli a pagamento](2026-11-19-moduli-a-pagamento-design.md), sezione "Cambio di rotta del 22/11/2026", e si appoggia al login del ramo `login-ruoli` ([spec](2026-11-18-login-ruoli-design.md), [docs/ACCESSO.md](../../ACCESSO.md) su quel ramo).

## Perché

AutoLost si vende a moduli (Magazzino base + Pratiche, Ambiente, Banco). Oggi un'azienda la crea solo il super admin, e i moduli si accendono dalla pagina Impostazioni → Moduli, che è scritta dal browser e quindi non protetta. Alessandro vuole che il cliente faccia tutto da solo, senza passare da lui:

1. si registra dalla landing;
2. entra e inserisce il primo veicolo;
3. il gestionale si ferma con un riquadro di pagamento a tutto schermo;
4. paga su Stripe (account Lostar srls) il Magazzino da solo o con i moduli in più, al mese o all'anno;
5. i moduli pagati si accendono da soli.

Vuole anche un'**entrata di prova**: pagare con la carta di prova di Stripe (4242 4242 4242 4242) e vedere scorrere il tempo degli abbonamenti (rinnovo, disdetta, pagamento non riuscito) senza aspettare un mese vero.

## Obiettivi

- Registrazione del titolare su codice invito finché le chiavi sono di prova, senza email di conferma.
- Riquadro di pagamento dopo il primo veicolo salvato.
- Pagamento sulla pagina di Stripe (Checkout), abbonamento mensile o annuale.
- Moduli decisi dal **server**, in base a Stripe, e non più dal browser.
- Pagina **Abbonamento** con il conto alla rovescia (rinnovo, fine, pagamento in ritardo), moduli da aggiungere o togliere, portale Stripe per carta, fatture e disdetta.
- Il titolare crea gli accessi dei dipendenti, con i loro ruoli.
- Strumenti di prova: la carta 4242 e l'orologio di prova di Stripe per far avanzare il tempo.

## Non obiettivi

- Email di qualunque tipo: conferma dell'indirizzo, recupero della password, inviti. Arrivano con il trasloco nel cloud. Una password dimenticata la reimposta il super admin dalla Piattaforma.
- Il trasloco nel cloud: la demo resta sul Mac con il tunnel.
- Il passaggio da mensile ad annuale (e viceversa) senza disdire (vedi "Rimandato").
- La fattura elettronica verso lo SDI (vedi "Vincoli").
- Chiavi Stripe vere (live). Tutto in questa fase gira nella sandbox **AutoLost demo**.

## Anti-obiettivi (sarebbe un fallimento anche se funziona)

- Un cliente che non ha pagato e riesce a lavorare, anche solo riaccendendo i moduli dal browser.
- Un cliente che paga e trova i moduli spenti, anche se l'avviso di Stripe (webhook) non è arrivato.
- Un pagamento vero fatto per sbaglio con una chiave live.
- Dati del cliente persi o cancellati perché l'abbonamento è scaduto.
- I dati della carta che passano dal nostro server.

## Vincoli

- **Next.js 16.4.** Prima di scrivere route e pagine si leggono le guide in `node_modules/next/dist/docs/` (vedi AGENTS.md).
- **Login.** Si parte dal login di `login-ruoli`:
  - Better Auth con `piattaforma.sqlite`, plugin organization (le aziende), admin (il super admin), twoFactor e PIN dei dispositivi;
  - dati di ogni azienda in `DATI_DIR/aziende/<id>/`.
  - `emailAndPassword.disableSignUp: true` resta acceso: la registrazione passa da una route nostra, che usa `creaAzienda` e `creaMembro` di `src/lib/piattaforma/crea.ts`.
- **Ruolo del titolare.** Il titolare è il ruolo `responsabile`: un ruolo "titolare" non esiste e non si aggiunge.
- **Listino.** Prezzi da `src/lib/listino.ts` (ramo `offerta-prezzi`), in centesimi e IVA esclusa. In Stripe i prezzi si trovano con le lookup key: `magazzino_mese`, `magazzino_anno`, `pratiche_…`, `ambiente_…`, `banco_…`; ogni prodotto ha `metadata.modulo` con l'id del modulo dell'app (`magazzino`, `accettazione`, `ambiente`, `vendite`).
- **Un periodo per abbonamento.** Stripe non mette nello stesso abbonamento prezzi mensili e annuali: si sceglie mese o anno per tutto.
- **Dove arrivano gli avvisi di Stripe.** Il server gira sul Mac:
  - gli avvisi (webhook) arrivano dal tunnel (`INDIRIZZO_GESTIONALE`), oppure da `stripe listen` mentre si prova in locale (serve `stripe login`, che oggi è scaduto e deve rifarlo Alessandro);
  - il gestionale non deve dipendere solo da loro (vedi "Sincronizzazione").
- **Fattura elettronica.** Le fatture di Stripe non sono fatture elettroniche: Lostar le emetterà verso lo SDI con il suo strumento. È da chiarire con il commercialista prima di andare live.
- **IVA.** I prezzi sono IVA esclusa: è un'ipotesi ancora da confermare. In Checkout si applica un'aliquota fissa "IVA 22%", creata nella sandbox (scelta mia), e si chiedono partita IVA e indirizzo di fatturazione.

## Strade considerate

1. **Pagina di pagamento di Stripe (Checkout ospitato), con avvisi al server e portale cliente di Stripe.**
   - Il cliente esce un attimo dal gestionale per pagare.
   - È la strada più corta e più sicura, perché la carta non passa mai da noi.
   - Carta, Apple Pay, codice della banca (3D Secure) e ricevute li gestisce Stripe.
   - **Scelta da Alessandro** il 22/11/2026, con in più l'entrata di prova.
2. **Campo della carta dentro il riquadro (Checkout integrato o Elements).**
   - Il cliente non esce mai dal gestionale, ma costa più lavoro: conferma, errori e 3D Secure restano a noi.
   - Il resto è identico alla strada 1.
3. **Scartate:**
   - Link di pagamento fissi: non sanno di quale azienda è il pagamento e servirebbero 16 link.
   - Pacchetto Stripe di Better Auth: pensato per un piano per abbonamento, si adatta male ai moduli aggiunti.

## Come funziona

### 1. Registrazione

- **Pagina pubblica `/registrati`.** Ci si arriva con il link di un codice invito; il pulsante `REGISTRAZIONE` della landing ci porterà quando la registrazione sarà aperta a tutti. Campi:
  - nome dell'azienda;
  - nome e cognome del titolare;
  - email;
  - password, di almeno 10 caratteri;
  - **codice invito** (deciso da Alessandro il 22/11/2026: finché le chiavi sono di prova, chiunque potrebbe "pagare" con la 4242 e usare tutto gratis);
  - casella "Accetto le condizioni": il link porta per ora a una pagina segnaposto.
- **Codici invito.**
  - Li crea il super admin nella Piattaforma, pagina "Inviti": un codice per volta, valido 30 giorni, usabile una volta sola, con una nota ("per Rossi autodemolizioni").
  - Si salvano nel database della piattaforma con chi l'ha creato, quando, e l'azienda che l'ha usato.
  - Il link da mandare è `/registrati?invito=<codice>` e riempie il campo da solo.
  - Un codice sbagliato, scaduto o già usato dà sempre lo stesso messaggio: "Codice invito non valido".
  - Il pulsante della landing resta sulla demo finché la registrazione è su invito; il link "Registrati" di `/accesso` porta a `/registrati`, che senza codice spiega come averne uno.
- **Route `POST /api/registrazione`.** Fa, nell'ordine:
  1. crea l'azienda con `metadata: { demo: false, registrata: true }`;
  2. scrive l'archivio vuoto con `creaStatoAzienda(statoVuoto(...))`, come fa la Piattaforma;
  3. crea il titolare con `creaMembro`, ruolo `responsabile`, email e password;
  4. scrive `abbonamento.json` nello stato `nuovo` (vedi 2);
  5. fa entrare il titolare (sessione Better Auth, azienda attiva quella nuova) e lo porta su "Oggi".
- **Se un passo fallisce**, si toglie quello che è stato creato: azienda, cartella, utente.
- **Email già usata.** Messaggio generico: "Non è stato possibile registrarti con questa email. Se hai già un account, accedi."
- **Limiti.** Al massimo 3 registrazioni all'ora per indirizzo, letto da `cf-connecting-ip` come gli altri limiti di ACCESSO.md. Nel registro attività dell'azienda: "Azienda registrata".
- **Collegamenti.** La landing ha "Accedi", che porta a `/accesso`; `/accesso` ha il link "Non hai un account? Registrati".

### 2. Lo stato dell'abbonamento: fonte di verità sul server

- **File `DATI_DIR/aziende/<id>/abbonamento.json`.** Lo scrive **solo** il server, con file temporaneo e rinomina come `state.json`). Contiene:
  - `stato`: uno tra `nuovo` (mai pagato), `attivo`, `in-ritardo` (pagamento non riuscito, Stripe ritenta), `disdetto` (pagato fino a fine periodo, non si rinnova), `scaduto` (finito, annullato o non pagato);
  - `periodo`: `mese` o `anno`;
  - `moduli`: i moduli pagati, sempre con `magazzino`;
  - `rinnovo`: la fine del periodo pagato. Dalla versione 2025-03-31 dell'API Stripe sta sulle voci dell'abbonamento, non sull'abbonamento;
  - `customerId`, `subscriptionId`;
  - `orologioId` e `oraOrologio`, solo con l'orologio di prova (vedi 6);
  - `aggiornato`.
- **Moduli accesi**, decisi dal server con una funzione pura `moduliDaAbbonamento(abbonamento)`:
  - stato `nuovo`: solo Magazzino, perché il titolare deve poter inserire il primo veicolo;
  - `attivo`, `in-ritardo` e `disdetto`: i moduli pagati;
  - `scaduto`: solo Magazzino, ma con il blocco (vedi 3).
- **Lettura del gestionale.** Quando il browser legge l'archivio (`GET /api/demo-state`), per le aziende registrate il server mette in `moduli` quelli di `moduliDaAbbonamento`.
- **Scrittura del gestionale.** In `PUT /api/demo-state`, il valore `moduli` mandato dal browser si ignora.
- **Controlli dei moduli sul server.** `moduloAttivoSulServer` diventa per azienda e legge `abbonamento.json`.
- **Impostazioni → Moduli.**
  - Per le aziende registrate la pagina con gli interruttori sparisce e il menu porta ad Abbonamento.
  - Gli interruttori restano solo per le aziende senza `registrata` (l'azienda demo e quelle create dal super admin), così la demo che c'è oggi non cambia.
- **Quando c'è il blocco.** Una funzione pura `bloccato(abbonamento, veicoli)` vale vero se:
  - lo stato è `nuovo` e c'è almeno un veicolo;
  - oppure lo stato è `scaduto`.
- **Scritture bloccate.** Con il blocco il server rifiuta le scritture (`PUT /api/demo-state` risponde 402 "Abbonamento non attivo"). Le letture continuano, così i dati restano visibili sotto il riquadro e non si perde nulla.
- **Modifiche in sospeso.** Sul ramo `login-ruoli` le modifiche rifiutate dal server si scartano (`inviaSalvateInSospeso`) e quelle in sospeso scadono dopo 24 ore (`IN_SOSPESO_MAX_MS`). Per il rifiuto 402 si fa un'eccezione (scelta mia): quelle modifiche **non si scartano e non scadono** finché l'abbonamento è bloccato, e partono dopo il pagamento. Il limite di 24 ore resta per tutto il resto, perché protegge i dati di un'azienda su un browser condiviso.
- **Collegamenti durante il blocco** (deciso da Alessandro il 22/11/2026):
  - gli annunci eBay restano online e le vendite eBay continuano a entrare nel gestionale (`ebay/vendite`, `ebay/allinea`): le scritture fatte dal server per conto dei collegamenti non si bloccano, così un pezzo venduto risulta venduto;
  - il negozio online dell'azienda si chiude: il catalogo pubblico risponde vuoto con "Negozio momentaneamente chiuso" e `negozio/ordine` rifiuta i nuovi ordini;
  - le foto si caricano anche con il blocco (`api/foto`), perché fanno parte del salvataggio del primo veicolo;
  - la visura PRA resta bloccata, come ogni funzione di un modulo non attivo.
- **Il primo veicolo.** Il blocco scatta dopo, perché lo stato `nuovo` blocca solo con veicoli ≥ 1: il primo salvataggio passa.

### 3. Il riquadro di pagamento

Il riquadro si apre in `AppShell` sopra ogni pagina quando `bloccato` è vero. Copre tutto lo schermo e non si chiude. Fuori restano solo "Esci" e, durante l'assistenza, la fascia del super admin.

Schizzo per il titolare (`responsabile`):

```
┌──────────────────────────────────────────────┐
│  Il tuo primo veicolo è dentro. 🚗          │
│  Scegli come continuare con AutoLost.        │
│                                              │
│   ( Mensile )  ( Annuale · risparmi il 10% ) │
│                                              │
│   ✓ Magazzino            299,90 € / mese     │
│   ☐ Pratiche              19,90 € / mese     │
│   ☐ Ambiente              49,90 € / mese     │
│   ☐ Banco                 49,90 € / mese     │
│   ───────────────────────────────────────    │
│   Totale                 299,90 € / mese     │
│   IVA esclusa                                │
│                                              │
│   [  Paga con Stripe  ]                      │
│   Prova: carta 4242 4242 4242 4242 …         │  ← solo con chiavi di prova
└──────────────────────────────────────────────┘
```

- **Testi e prezzi.**
  - Totale e risparmio si calcolano con `listino.ts`, come sulla landing.
  - Con lo stato `scaduto` il titolo diventa: "Il tuo abbonamento è finito. I tuoi dati sono al sicuro: riattivalo per continuare".
  - La scelta di partenza riprende i moduli e il periodo che il cliente aveva.
- **Gli altri ruoli** vedono "L'abbonamento non è attivo. Chiedi al titolare di attivarlo." e "Esci", senza scelte.
- **"Paga con Stripe"** chiama `POST /api/abbonamento/checkout` e apre la pagina di Stripe nella stessa scheda.

### 4. Pagamento: Checkout

**Route `POST /api/abbonamento/checkout`.**

- Riceve `{ periodo, moduli[] }`.
- Accesso:
  - solo `responsabile` dell'azienda attiva, o super admin in assistenza;
  - rifiutato con lo stato `attivo`, `in-ritardo` o `disdetto`, perché lì i moduli si aggiungono da Abbonamento.
- **Prezzi.** Si cercano con le lookup key `${idStripe}_${periodo}`: l'id dell'app si traduce in nome Stripe, `accettazione`→`pratiche` e `vendite`→`banco`, con una mappa pura e testata.
- **Cliente Stripe.**
  - Se l'azienda non lo ha, si crea con `metadata.azienda = <id>`, nome dell'azienda ed email del titolare.
  - Con le chiavi di prova si crea dentro un orologio di prova nuovo (vedi 6).
- **Sessione Checkout.**
  - `mode: "subscription"`, con una voce per ogni modulo;
  - `client_reference_id` e `subscription_data.metadata.azienda` con l'id dell'azienda;
  - IVA 22% come aliquota fissa, raccolta della partita IVA, indirizzo di fatturazione obbligatorio, lingua italiana;
  - `success_url`: `/abbonamento/fatto?session_id={CHECKOUT_SESSION_ID}`;
  - `cancel_url`: la pagina da cui si è partiti, con il riquadro ancora aperto.
- **Pagina `/abbonamento/fatto`.** Il server legge la sessione da Stripe e, se è pagata, sincronizza subito (vedi 5) senza aspettare l'avviso. Poi mostra "Fatto: moduli attivi" con l'elenco e porta a "Oggi".
- **Pagamento in sospeso.** Se la sessione non è ancora pagata (SEPA o simili), la pagina dice "Pagamento in corso: ti avvisiamo qui appena Stripe conferma" e il gestionale ricontrolla ogni pochi secondi.

### 5. Avvisi di Stripe e sincronizzazione

- **Route `POST /api/stripe/webhook`.**
  - Legge il corpo grezzo (`req.text()`) e verifica la firma con `STRIPE_WEBHOOK_SECRET`; con una firma sbagliata risponde 400.
  - Eventi ascoltati: `checkout.session.completed`, `customer.subscription.created`, `.updated`, `.deleted`, `invoice.paid`, `invoice.payment_failed`, `test_helpers.test_clock.ready`.
- **Una sola funzione `sincronizza(aziendaId)`**, per ogni evento:
  1. trova l'azienda da `metadata.azienda`;
  2. **rilegge da Stripe** l'abbonamento corrente del cliente e riscrive tutto `abbonamento.json`.
  - Il contenuto dell'evento non si usa direttamente: così l'ordine in cui arrivano gli eventi e gli eventi doppi non contano.
  - Gli eventi di un'azienda sconosciuta si registrano nel log del server e ricevono 200.
- **Da stato Stripe a stato dell'app** (funzione pura e testata):

  | Stato Stripe | Stato nell'app |
  |---|---|
  | `active` o `trialing` | `attivo`, oppure `disdetto` se `cancel_at_period_end` |
  | `past_due` | `in-ritardo` |
  | `canceled`, `unpaid`, `incomplete_expired` | `scaduto` |
  | `incomplete` | lo stato non cambia: il primo pagamento non è ancora riuscito |
  | nessun abbonamento | `nuovo` se non è mai stato pagato, altrimenti `scaduto` |

- **Pagamento non riuscito** (deciso da Alessandro il 22/11/2026): Stripe riprova l'addebito per **14 giorni**. In quei giorni lo stato è `in-ritardo`, il cliente lavora con la fascia "aggiorna la carta". Alla fine dei tentativi Stripe **annulla l'abbonamento** (impostazione della sandbox: Billing → Revenue recovery → Retries, 14 giorni, poi "Cancel the subscription"), lo stato diventa `scaduto` e scatta il blocco, con i dati che restano.
- **Moduli.** Si leggono da `price.product.metadata.modulo` di ogni voce; quelli sconosciuti si scartano e `magazzino` c'è sempre.
- **Quando si sincronizza anche senza avvisi:** al ritorno da Checkout, all'apertura della pagina Abbonamento e, per il titolare, a ogni ingresso nel gestionale se `aggiornato` ha più di un'ora. Se l'avviso non arriva (tunnel spento), il gestionale si rimette in pari da solo.
- **Registro attività dell'azienda.** Si scrive una riga a ogni cambio di stato o di moduli: "Abbonamento attivato", "Modulo aggiunto: Ambiente", "Pagamento non riuscito", "Abbonamento disdetto", "Abbonamento scaduto".

### 6. Pagina Abbonamento e conto alla rovescia

**Pagina `Impostazioni → Abbonamento`**, solo per il `responsabile`. Sostituisce Moduli per le aziende registrate.

```
Abbonamento                               Mensile · Attivo
─────────────────────────────────────────────────────────
Si rinnova il 22/12/2026 · tra 30 giorni
Prossimo addebito: 349,80 € + IVA

Moduli
  Magazzino   299,90 € / mese   incluso
  Ambiente     49,90 € / mese   [Togli]
  Pratiche     19,90 € / mese   [Aggiungi]
  Banco        49,90 € / mese   [Aggiungi]

[ Carta, fatture e disdetta ]   ← portale clienti Stripe
```

**Righe del conto alla rovescia.** I giorni si contano da "adesso", che con l'orologio di prova è `oraOrologio` e non la data del Mac. È una funzione pura e testata.

| Stato | Riga mostrata |
|---|---|
| `attivo` | "Si rinnova il … · tra N giorni" (oggi: "Si rinnova oggi") |
| `disdetto` | "Finisce il … · tra N giorni. Poi il gestionale si blocca, i dati restano." con il pulsante "Riattiva" (toglie la disdetta) |
| `in-ritardo` | "Pagamento non riuscito il …: aggiorna la carta. Stripe riprova da solo." |
| `scaduto` | non c'è la pagina: c'è il riquadro di blocco |

**Fascia in cima al gestionale**, solo per il titolare:

- con lo stato `in-ritardo`, sempre;
- con lo stato `disdetto`, negli ultimi 7 giorni.

**Aggiungere un modulo.**

- Route `POST /api/abbonamento/moduli` con `{ aggiungi }`: crea la voce sull'abbonamento con lo stesso periodo e fa pagare subito la parte che manca al rinnovo (`proration_behavior: "always_invoice"`).
- Prima di confermare si mostra l'importo, che Stripe calcola in anteprima con l'anteprima della fattura.
- Il pulsante "Attiva" di `ModuloBloccato` (oggi "Chiedi l'attivazione" su WhatsApp) porta qui con il modulo già scelto. Per chi non è titolare dice "Chiedi al titolare di attivarlo".

**Togliere un modulo.**

- Stessa route con `{ togli }`: toglie la voce subito, e i giorni non usati diventano credito sulla prossima fattura (`proration_behavior: "create_prorations"`).
- La conferma elenca il lavoro aperto con `lavoroAperto`, come fa oggi la pagina Moduli.
- Il Magazzino non si toglie.

**Portale clienti Stripe** (`POST /api/abbonamento/portale`): serve per carta, fatture, dati di fatturazione e disdetta a fine periodo. Il portale va configurato nella sandbox con queste funzioni accese e il cambio di prodotto spento: con più voci nello stesso abbonamento Stripe non lo gestisce bene, e i moduli si cambiano dal gestionale.

### 7. Entrata di prova (carta 4242 e orologio di Stripe)

Vale solo quando la chiave è di prova (`sk_test_…`), e in questa fase è sempre così. Si entra dalla registrazione normale, con un'email qualunque (anche `prova1@autolost.test`), così si prova il percorso vero.

**Sulla landing e su `/registrati`.** Una riga piccola: "Ambiente di prova: nessun addebito vero".

**Nel riquadro di pagamento e su Abbonamento**, un riquadro "Carte di prova" con:

- `4242 4242 4242 4242`: pagamento riuscito. Scadenza qualunque futura, CVC qualunque.
- `4000 0027 6000 3184`: chiede il codice della banca (3D Secure).
- `4000 0000 0000 0341`: la carta si salva ma l'addebito fallisce. Serve a provare "pagamento non riuscito" al rinnovo: si cambia la carta dal portale.

**Orologio di prova.**

- Con le chiavi di prova ogni cliente Stripe nasce dentro un orologio di prova (test clock) tutto suo, che parte dall'ora di adesso.
- Su **Abbonamento** c'è il riquadro "Strumenti di prova":
  - riga: "Data di prova: 22/11/2026";
  - pulsanti "+1 giorno", "+1 settimana", "+1 mese" e "+1 anno" (questo solo con l'abbonamento annuale);
  - pulsante "Torna a oggi" non c'è: l'orologio va solo avanti, e per ricominciare si registra un'altra azienda.
- Ogni pulsante:
  1. chiama `POST /api/abbonamento/prova/avanza`;
  2. Stripe genera fatture e addebiti come se il tempo fosse passato (rinnovo, carta rifiutata, ritentativi, fine dopo la disdetta);
  3. la pagina aspetta che l'orologio torni "pronto", poi sincronizza.
- **Cosa si vede:** il conto alla rovescia che scende, il rinnovo, la fascia in ritardo, il blocco a scadenza e i dati che restano.
- **Limite di Stripe:** si avanza al massimo di due periodi alla volta. Il server lo controlla e rifiuta con un messaggio chiaro.
- **Con una chiave live** riquadro e route non esistono: la route risponde 404.

**Sicurezza delle chiavi.**

- Il server rifiuta di creare pagamenti se `STRIPE_SECRET_KEY` comincia con `sk_live_` e manca `STRIPE_LIVE=1`.
- Con chiavi di prova la Piattaforma mostra "Stripe: prova (AutoLost demo)".

### 8. Accessi dei dipendenti

**Pagina `Impostazioni → Persone`**, solo per il `responsabile`. Riusa le regole della pagina azienda della Piattaforma, ma per la propria azienda. Il titolare può:

- vedere l'elenco con nome, ruoli, se entra con email o PIN, ultimo accesso;
- aggiungere una persona con `creaMembro`: nome, uno o più ruoli tra i sei, email e password oppure solo PIN di 4 cifre;
- cambiare i ruoli, reimpostare la password o il PIN, sospendere o riattivare.

**Limiti.**

- Il titolare non può togliere il ruolo `responsabile` a sé stesso se è l'unico.
- Le route riusano i controlli che la Piattaforma ha già (`src/app/api/piattaforma/aziende/[id]/utenti`): un'azienda per volta, controllo di provenienza (`daAltroSito`) e registro attività.

**Cosa vede ciascuno.** Resta quello che il ramo `login-ruoli` già fa per ruolo:

- il titolare vede tutto;
- gli altri ruoli vedono il loro lavoro;
- il controllo è nelle schermate, più alcune azioni delicate sul server (limite noto di ACCESSO.md).

### 9. Variabili d'ambiente nuove

Vanno in ACCESSO.md, o in un `docs/PAGAMENTI.md` nuovo.

| Variabile | A cosa serve |
|---|---|
| `STRIPE_SECRET_KEY` | Chiave segreta della sandbox AutoLost demo (`sk_test_…`). Mai nel codice. |
| `STRIPE_WEBHOOK_SECRET` | Segreto di firma degli avvisi: quello dell'endpoint della sandbox, oppure quello stampato da `stripe listen` in locale. |
| `STRIPE_LIVE` | `1` solo quando si andrà con chiavi vere. |

## Su che ramo si costruisce

- **Ramo nuovo** `registrazione-pagamento`, che unisce `login-ruoli`, `moduli-a-pagamento` e `offerta-prezzi`.
- **Conflitti attesi:** `AppShell.tsx`, `store.ts`, `sync.ts` e `api/demo-state/route.ts`, toccati sia dal login sia dai moduli.
- **Moduli per azienda.** `moduli` in WHOLE (ramo moduli) va riconciliato con la sincronizzazione per azienda e le modifiche in sospeso (ramo login).
- `main` non si tocca.
- **L'unione si fa solo con il via di Alessandro**, ed è il primo passo del piano.

## Lasciato a chi costruisce

- Nomi dei file, struttura dei componenti, testi minori e stile, coerenti con il resto dell'app (`ModuloBloccato`, Piattaforma).
- La libreria `stripe` per Node: ultima versione stabile, con la versione dell'API fissata nel codice.
- Come il gestionale ricontrolla lo stato mentre aspetta (intervallo, quando smettere).
- Come si provano gli avvisi:
  - test sulle funzioni pure (mappa degli stati, conto alla rovescia, `bloccato`, `moduliDaAbbonamento`, lookup key);
  - una prova vera nella sandbox con `stripe listen` o con il tunnel.
- **Il listino.** `src/lib/listino.ts` esiste solo nella cartella di lavoro di `offerta-prezzi` (`.claude/worktrees/offerta`) e non è ancora salvato nel ramo, come il pulsante `REGISTRAZIONE` di `Sito.tsx`. Primo passo del piano: farlo salvare in quel ramo da chi ci lavora. Se non succede, si ricopia `listino.ts` così com'è: importi in centesimi IVA esclusa, `LISTINO`, `prezzo`, `risparmioAnnuale`, `totale`, `euro`, con chiavi uguali agli id dei moduli dell'app.
- **Accesso alla sandbox.**
  - La chiave `sk_test` della sandbox AutoLost demo la mette Alessandro in `.env.local`; chi costruisce non la copia dal pannello.
  - Il resto della sandbox si prepara dal pannello di Stripe nel browser, come per i prodotti: aliquota IVA 22%, portale clienti, regole dei tentativi (vedi "Pagamento non riuscito"). I passi si scrivono anche in `docs/PAGAMENTI.md`.
  - Per prima cosa si controlla l'avviso "Varie funzionalità sospese": se blocca Checkout, la prova vera aspetta che Alessandro lo risolva.
- **Avvisi durante la demo.** Il tunnel della presentazione (`scripts/presentazione.sh`) è un indirizzo `trycloudflare.com` che cambia a ogni avvio, quindi un endpoint fisso nella sandbox non regge.
  - In prova gli avvisi arrivano con `stripe listen --forward-to localhost:<porta>/api/stripe/webhook`, dopo lo `stripe login` di Alessandro.
  - Senza `stripe listen` il gestionale si rimette in pari da solo con la sincronizzazione del punto 5.
- **Aziende di prova e chiavi vere.** `abbonamento.json` ha `prova: true` quando è stato scritto con chiavi di prova. Con le chiavi vere quelle aziende non si sincronizzano con Stripe (i loro id non esistono nell'account vero) e non si bloccano: restano com'erano e si tolgono a mano (vedi "Rimandato").
- Le scelte segnate qui sotto come mie, se in costruzione si trova un motivo serio per cambiarle (da dire ad Alessandro).

## Scelte mie (da controllare)

- Mese o anno vale per tutti i moduli insieme.
- Il blocco scatta al salvataggio del primo veicolo, non all'apertura della scheda.
- Con il blocco il server rifiuta le scritture; le letture restano.
- Un modulo aggiunto si paga subito per la parte che manca. Un modulo tolto si spegne subito, e i giorni non usati vanno come credito sulla prossima fattura.
- IVA 22% fissa in Checkout, con la raccolta della partita IVA.
- Ogni cliente di prova ha il suo orologio di Stripe; gli strumenti di prova stanno sulla pagina Abbonamento, non nella Piattaforma, così si provano dallo stesso browser del titolare.
- Le aziende già esistenti (demo e create dal super admin) restano con gli interruttori e senza pagamento.
- Email già usata: messaggio generico.

## Rimandato

- Email: conferma dell'indirizzo, recupero della password, inviti, ricevute nostre. Si fanno con il trasloco nel cloud.
- Cambio da mensile ad annuale senza disdire; per ora: disdetta, e poi un nuovo abbonamento alla scadenza.
- Fattura elettronica verso lo SDI e accordo con il commercialista sull'IVA.
- Periodo di prova gratuito, codici sconto, prezzo "Completo".
- Eliminazione delle aziende di prova e dei loro clienti Stripe.
- Registrazione aperta a tutti senza codice invito: con le chiavi vere, e con una protezione dai robot oltre al limite per indirizzo.
- Chiavi live, endpoint degli avvisi definitivo e verifica dell'attività sulla sandbox ("Varie funzionalità sospese").
