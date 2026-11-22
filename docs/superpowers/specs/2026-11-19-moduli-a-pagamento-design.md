# Moduli a pagamento: progetto

19/11/2026 · prototipo. Riguarda le voci A12 (abbonamenti e moduli attivabili) e H4 (navigazione con moduli attivabili per piano) di `docs/ROADMAP.md`.

## Perché
Alessandro vuole costruire l'offerta commerciale **a moduli**: quattro servizi comprabili a prezzi separati, in modo indipendente, partendo da un pacchetto base. Le funzioni non acquistate restano **visibili ma bloccate** ("in trasparenza"), così il cliente vede cosa può aggiungere e chiede l'attivazione. Il gestionale è già quasi diviso così (aree Veicoli, Ricambi, Vendite, Ambiente in `src/components/AppShell.tsx`); il lavoro è rendere i confini netti, spostare le poche voci fuori posto e aggiungere blocco e richiesta d'attivazione.

Cambia un principio della roadmap: "I moduli non acquistati non compaiono" diventa "I moduli non acquistati compaiono bloccati, con la spiegazione e la richiesta d'attivazione".

## I quattro moduli

| Modulo | Prezzo | Contiene |
|---|---|---|
| **Magazzino** | base, sempre attivo | Scheda veicolo semplice (targa, telaio, marca, modello, versione, anno, alimentazione, colore, km, peso con "pesato alla pesa", foto, conferma del telaio), lettura della targa dalla foto e ricerca dei dati dalla targa, smontaggio (`/campo`), ricambi, ubicazioni, inventario, area rottami, scorte minime, etichette ed etichette scaffale, scansione, **pubblicazione online** (eBay e negozio online, con il +8% di [commissione](../../INTEGRAZIONI.md)), **ordini online** con scontrino, fattura e reso |
| **Accettazione** | add-on | La parte burocratica e i collegamenti esterni: conferente e documenti, visura PRA, controlli ACI, presa in carico nel RVFU e certificato, radiazione e invio, fascicolo, fermo. In pratica il pannello `PraticaPanel` e tutto ciò che c'è dietro |
| **Ambiente** | add-on | Bonifica (`/veicoli/[id]/bonifica`), registro rifiuti, periodo RENTRI, formulari, soggetti, limiti dell'autorizzazione |
| **Vendite** | add-on | Il banco: vendita in sede, preventivi, scontrino e fattura al banco, resi e note di credito del banco, clienti, listini, elenco completo dei documenti (`/vendite/documenti`) |

**Comune a tutti** (fa parte del base): "Oggi", ricerca globale, registro attività, impostazioni, cambio ruolo.

Scelte di Alessandro: scheda veicolo semplice nel Magazzino (non solo un testo di provenienza); pubblicazione online nel base perché ogni pezzo venduto online genera l'8%; voci bloccate con pagina di spiegazione e richiesta via WhatsApp; gli ordini online si chiudono nel base con scontrino, fattura e reso (il modulo Vendite è il banco); senza Accettazione la scheda semplice ha chi consegna, codice fiscale e numero del certificato; lettura e ricerca della targa nel base (nell'Accettazione restano i collegamenti burocratici: visura PRA, ACI, RVFU, radiazione).

Proposte mie, non contestate finora: la bonifica sta in Ambiente perché il suo risultato è il registro rifiuti; i listini stanno in Vendite perché sono le fasce di prezzo del banco.

## Obiettivi
1. Ogni pagina, voce di menu e azione appartiene a **un solo modulo**, dichiarato in un punto solo.
2. Un modulo non attivo si vede bloccato nel menu, la sua pagina mostra la spiegazione al posto del contenuto, e nelle pagine attive restano piccole tracce bloccate dove il modulo si aggancerebbe.
3. Ogni combinazione di moduli funziona: in particolare **Magazzino da solo**, **Magazzino + Ambiente** (senza Accettazione) e **Magazzino + Accettazione** (senza Ambiente).
4. Il cliente chiede l'attivazione con un tocco, il messaggio arriva ad Alessandro su WhatsApp.
5. I servizi esterni che costano rifiutano la chiamata se il modulo non è attivo.

## Non obiettivi (ora)
- Prezzi, piani, fatturazione del servizio, prove gratuite, scadenze dell'abbonamento: qui c'è solo "attivo / non attivo" per modulo.
- Attivazione da parte di Alessandro in un pannello di piattaforma: arriva con il login (`docs/superpowers/specs/2026-11-18-login-ruoli-design.md`, area `/piattaforma`). Ora gli interruttori stanno nelle impostazioni dell'azienda.
- Moduli più fini dei quattro (es. vendere eBay a parte) e il deposito giudiziario (C12), che diventerà un quinto modulo.
- Invio del messaggio WhatsApp dal server (WhatsApp Business): lo manda il cliente dal suo telefono.

## Anti-obiettivi
- Un cliente con il solo Magazzino che non riesce a fare il suo lavoro quotidiano (accettare un veicolo, smontarlo, catalogare, pubblicare) perché manca un pezzo che sta in un altro modulo.
- Un modulo bloccato che si usa lo stesso aprendo l'indirizzo della pagina o chiamando il servizio.
- Dati persi o incoerenti quando un modulo si attiva o si disattiva: attivare un modulo dopo mesi deve trovare i dati già presenti.
- Un menu pieno di lucchetti che rende faticoso il lavoro di chi ha comprato poco.
- La coda "Oggi" che chiede cose di un modulo non attivo (radiazioni in scadenza a chi non ha l'Accettazione).

## Approcci considerati
1. **Mappa unica dei moduli** (scelto da Alessandro). Un file dichiara per ogni modulo le pagine, le voci di menu e le azioni. Menu, blocco delle pagine, tracce nelle pagine e controlli sul server leggono tutti da lì. Un modulo nuovo o spostato si cambia in un punto.
2. **Interruttori sparsi nelle pagine.** Ogni pagina controlla da sé. Più veloce da iniziare, ma con le tracce incrociate diventa un groviglio e prima o poi una pagina resta aperta. Scartato.
3. **Una versione dell'app per pacchetto.** Contro la piattaforma unica per tutte le aziende già decisa. Scartato.

## Come funziona

### La mappa dei moduli
Un modulo puro, per esempio `src/lib/moduli.ts`, con:
- il tipo `Modulo = "magazzino" | "accettazione" | "ambiente" | "vendite"`;
- per ciascuno: nome, frase di presentazione, 3–4 punti di cosa fa, icona;
- l'elenco dei percorsi che gli appartengono (es. `/ambiente`, `/veicoli/*/bonifica`, `/vendite`, `/listini`), con la regola "vince il percorso più specifico" già usata in `AppShell` (`currentSub`);
- una funzione `moduloDi(percorso)` e una `attivo(moduli, modulo)` (il Magazzino è sempre attivo).

Le voci di `AREAS` in `AppShell.tsx` prendono il modulo dalla mappa. Un test controlla che ogni pagina sotto `src/app/(app)` e ogni pagina di stampa abbia un modulo (nessuna pagina "orfana" che resta aperta per sbaglio).

### Dove si tiene quali moduli sono attivi
Nello stato dell'azienda (`src/lib/store.ts`, sincronizzato tramite `/api/demo-state`), campo per esempio `moduli: Modulo[]`. Valore iniziale per i dati demo: tutti attivi, così il prototipo resta com'è finché non si spegne qualcosa.

**Impostazioni → Moduli** (`/impostazioni/moduli`, ruolo responsabile): quattro righe con nome, cosa contiene e interruttore; il Magazzino è acceso e non si spegne. Ogni cambio entra nel registro attività. Pagina provvisoria: con il login gli interruttori passano al super admin e il cliente non li vede più.

### Menu
- Le aree di un modulo non attivo restano nel menu (barra laterale e "Altro" su telefono), in grigio con lucchetto, dopo le aree attive. Toccandole si apre la pagina del modulo bloccato.
- Le schede della barra inferiore del telefono (`MOBILE_TABS`) mostrano solo voci attive: una scheda di un modulo spento viene sostituita dalla prima area attiva non già presente, così chi lavora sul campo non ha lucchetti sotto il pollice.
- Il ruolo continua a decidere *cosa* si vede; il modulo decide se è *aperto o bloccato*. Se un ruolo vede solo voci bloccate (es. consulente ambientale senza Ambiente), vede comunque "Oggi" e la pagina del modulo bloccato.

### Pagina del modulo bloccato
Al posto del contenuto della pagina, nel layout `src/app/(app)/layout.tsx` (o in un componente che ogni pagina del modulo usa), quando `moduloDi(percorso)` non è attivo:
- titolo del modulo, la frase di presentazione e i 3–4 punti;
- un'anteprima sfocata dello schermo vero (un'immagine statica per modulo in `public/`, presa dalle catture del manuale);
- il pulsante **"Chiedi l'attivazione"**: apre `https://wa.me/<numero>?text=<messaggio>` con il messaggio già scritto, per esempio "Ciao, sono [azienda] su AutoLost: vorrei attivare il modulo Accettazione." Il numero sta in `src/lib/config.ts` (accanto a `PRODUTTORE`), da fornire da Alessandro. La richiesta entra anche nel registro attività dell'azienda.

### Tracce nelle pagine attive
Un componente, per esempio `<Bloccato modulo="accettazione">…</Bloccato>`, che mostra il contenuto se il modulo è attivo, altrimenti una riga sobria con lucchetto e nome della funzione che porta alla pagina del modulo. Dove serve:
- **Scheda veicolo** (`src/app/(app)/veicoli/[id]/view.tsx`): il pannello "Pratica di demolizione · RVFU" (`PraticaPanel`) diventa la riga "Pratica, visura e radiazione PRA 🔒" senza Accettazione; il pannello "Bonifica" vedi sotto.
- **Nuovo ingresso** (`/veicoli/nuovo`): il testo che rimanda alla pratica si adatta; nessun passo dell'Accettazione obbligatorio.
- **Scheda ricambio e smontaggio**: dove oggi si rimanda alla vendita al banco, la traccia di Vendite.
- Sobrietà: al massimo una traccia per pannello, mai nelle liste.

### Come funziona ogni combinazione

**Bonifica e smontaggio.** Oggi lo smontaggio non parte senza bonifica (`src/app/(app)/campo/[id]/view.tsx`, pulsante disattivo se `!v.bonifica`). Con Ambiente attivo resta tutto com'è (bonifica completa con materiali e pesi, che scrive il registro). Senza Ambiente il pannello Bonifica mostra solo **"Bonificato il …"** con data e chi l'ha fatta (un tocco), che soddisfa la stessa condizione per avviare lo smontaggio; il dettaglio dei materiali è la traccia bloccata di Ambiente.

**Registro rifiuti senza Accettazione** (scelta di Alessandro). Il carico del veicolo nasce già alla creazione (`addVehicle` in `store.ts` chiama `movesForIntake`), ma resta in bozza finché mancano produttore (nome e codice fiscale, da `v.conferente`) e certificato (`v.dossier.number` + `v.presaInCarico`), vedi `missingFields` in `src/lib/periodo.ts`. Oggi li compila solo `PraticaPanel`. Senza Accettazione, quindi, la scheda semplice mostra un piccolo pannello **"Dati per il registro"** con tre campi: chi consegna, codice fiscale, numero (e data) del certificato di rottamazione, che il cliente ricopia dalla pratica fatta altrove. Scrivono negli stessi campi del veicolo che usa la pratica, così il carico si completa come oggi e attivando l'Accettazione dopo i dati ci sono già. Con l'Accettazione attiva il pannello non compare (li compila la pratica). Il pannello serve solo se Ambiente è attivo; con il solo Magazzino non compare.

**Peso** (mia scelta). Un solo campo, `weightKg`, nella scheda del Magazzino, con la casella "pesato alla pesa" (`pesoPesa` del carico). Lo usano registro e bonifica come oggi.

**Targa e telaio nel base** (scelta di Alessandro). Lettura della targa dalla foto e ricerca dei dati dalla targa (oggi `simulateOcr` e `lookupPlate` in `src/lib/services.ts`, usati da `/veicoli/nuovo`) sono del Magazzino: se la ricerca va a buon fine il telaio nasce verificato, come oggi. Nelle impostazioni → Collegamenti i servizi relativi (Plate Recognizer, la parte "dati da targa" di Openapi) passano al Magazzino. Openapi è un servizio solo per più usi (dati da targa, visura PRA, fattura elettronica, firma): la sua scheda resta aperta nel base, e le singole funzioni di un modulo spento compaiono bloccate dentro la scheda.

**Dati con moduli spenti.** I fatti operativi si registrano sempre allo stesso modo; un modulo spento nasconde le schermate, non smette di salvare. Mia scelta, perché attivando un modulo dopo mesi il cliente trova lo storico. In particolare i movimenti del registro rifiuti si continuano a generare anche senza Ambiente (restano in bozza, non si trasmettono). Da validare: vedi "Lasciato al costruttore".

**Pubblicazione senza Accettazione.** Oggi i ricambi non si pubblicano senza telaio verificato. La verifica del telaio ("Confermo dati e telaio") resta nella scheda semplice del Magazzino, quindi la regola vale anche con il solo base.

**Vendite senza modulo Vendite** (scelta di Alessandro). Gli ordini online (eBay, negozio) si chiudono per intero nel base: si vedono, si preparano, si spediscono, e sulla riga dell'ordine restano "Emetti scontrino", "Emetti fattura" e "Registra reso" (oggi in `src/app/(app)/vendite/view.tsx`, righe degli ordini). Restano quindi nel base anche `issueDoc` e `returnOrder` per gli ordini online e la pagina di stampa `/documento/[id]` per i loro documenti. Del modulo Vendite sono il banco (vendita in sede), i preventivi, i listini, i clienti e l'elenco completo dei documenti (`/vendite/documenti`). La pagina `/vendite` oggi mescola banco e ordini online: va divisa (come, vedi "Lasciato al costruttore").

**Spegnere un modulo** (mia scelta). Prima di spegnerlo, la pagina Moduli mostra il lavoro aperto di quel modulo: ordini al banco in attesa di pagamento, preventivi aperti, pratiche a metà, bozze del registro con scadenza. Avvisa e chiede conferma; non cambia nulla da sola. I pezzi riservati da un ordine al banco restano riservati e si liberano dalla scheda ricambio (azione del base).

**Pagine di stampa** (mia scelta). Le pagine fuori da `(app)` (`/certificato/[id]`, `/documento/[id]`, `/etichetta`, ecc.) seguono la stessa mappa: il certificato è dell'Accettazione; i documenti di ordini online sono del base, quelli del banco di Vendite.

### "Oggi" e ricerca
- Ogni voce della coda (`src/lib/agenda.ts`, campo `kind`) ha un modulo; le voci di moduli spenti non compaiono.
- La ricerca globale (`src/components/GlobalSearch.tsx`) non mostra risultati di moduli spenti (es. formulari senza Ambiente); i veicoli si trovano sempre.

### Controlli sul server
- `/api/visura` (Openapi, costa a richiesta) rifiuta con un errore chiaro se l'Accettazione non è attiva, leggendo i moduli dallo stato dell'azienda sul server.
- Stessa regola per ogni futuro servizio esterno di un modulo add-on (RVFU, RENTRI vero, fatturazione elettronica). I servizi eBay sono del base e non hanno controllo.
- **Impostazioni → Collegamenti**: i servizi di un modulo spento compaiono bloccati, con la stessa traccia.
- Limite noto, come nel progetto del login: finché lo stato arriva intero dal dispositivo, chi ha accesso tecnico può riaccendere i moduli. Si chiude con il login (interruttori del super admin) e il database (A1).

### Pagine pubbliche e manuale
- `/scopri` presenta l'offerta a moduli (base + tre add-on) al posto del solo "8% online, 0 al banco". I prezzi restano fuori finché Alessandro non li decide.
- Il manuale operativo indica per ogni capitolo il modulo a cui appartiene.

## Lasciato al costruttore
- Nome e posizione esatta dei file (`moduli.ts`, componente `Bloccato`), forma del campo nello stato, migrazione dei dati salvati senza il campo (= tutti attivi).
- Come separare dentro `/vendite` la parte ordini online (base) dal banco (Vendite): sottopagina, schede o pagina nuova.
- Disegno del lucchetto, della pagina bloccata e delle anteprime sfocate, seguendo `DESIGN.md`.
- Se generare i movimenti del registro anche con Ambiente spento (proposta: sì, in bozza) o ricostruirli all'attivazione.
- Elenco preciso delle voci di "Oggi" e dei tipi di risultato della ricerca per modulo.

## Da fornire da Alessandro
- I prezzi, quando vorrà mostrarli su `/scopri`.
- ~~Il numero WhatsApp per le richieste d'attivazione.~~ Superato il 22/11/2026: vedi sotto.

## Cambio di rotta del 22/11/2026: attivazione con Stripe
Decisione di Alessandro: i moduli non si attivano più su richiesta WhatsApp ma **pagando con Stripe** (account Lostar srls, non quello di Futugrana). Registrazione e accesso partono dalla landing page; l'app resta tutta in cloud. Flusso voluto: registrazione → si entra nel gestionale → si inserisce il primo veicolo → l'app si blocca con un riquadro di pagamento al centro dello schermo che non lascia fare altro. Si paga il base oppure il base più gli add-on. Va progettato a parte (registrazione, prova, Stripe, attivazione automatica); il pulsante WhatsApp di oggi diventerà "Attiva" verso il pagamento.

## Listino (22/11/2026)
Abbonamento mensile o annuale a scelta del cliente; l'annuale si paga in un'unica soluzione con circa il 10% di sconto. Regola di Alessandro: i prezzi finiscono in 9 (49,90, 99,90…), mai cifre tonde come 50 o 100. Prezzi IVA esclusa (da confermare).

| Modulo | Nome commerciale | Mensile | Annuale |
|---|---|---|---|
| Magazzino (base) | AutoLost Magazzino | 299,90 € | 3.199 € (deciso da Alessandro) |
| Accettazione | AutoLost Pratiche | 19,90 € | 219 € |
| Ambiente | AutoLost Ambiente | 49,90 € | 539 € |
| Vendite | AutoLost Banco | 49,90 € | 539 € |

Prezzi rivisti da Alessandro il 22/11/2026 (prima: Pratiche 49,90/539, Ambiente 99,90/1.079; Pratiche detta "20 €", messa a 19,90 € per la regola del 9). Annuali: 12 mesi meno circa il 10%, arrotondati al 9. Fonte unica nel codice: `src/lib/listino.ts`, usata dalla sezione prezzi di `/scopri`.

## Stripe: sandbox AutoLost demo (22/11/2026)
Account Lostar srls (`acct_1TT0kgAq3HCB9mJS`), sandbox **AutoLost demo** `acct_1UeZEhPHwF2v5yEU`, separata dalle altre ("Sandbox di Lostar srls", "Modalità di test"). Prezzi in EUR, IVA esclusa (`tax_behavior=exclusive`), ricorrenti; ogni prodotto ha `metadata.modulo` uguale all'identificativo del modulo nel codice. Il gestionale trova i prezzi per **lookup key**, non per ID.

| Prodotto | ID prodotto | lookup key mensile | lookup key annuale |
|---|---|---|---|
| AutoLost Magazzino (299,90 € / 3.199 €) | `prod_Vfv7gm7X9Aayr3` | `magazzino_mese` | `magazzino_anno` |
| AutoLost Pratiche (19,90 € / 219 €) | `prod_Vfv85Atpr439j8` | `pratiche_mese` | `pratiche_anno` |
| AutoLost Ambiente (49,90 € / 539 €) | `prod_Vfv8syhEffdLoK` | `ambiente_mese` | `ambiente_anno` |
| AutoLost Banco (49,90 € / 539 €) | `prod_Vfv86z3t35LpPa` | `banco_mese` | `banco_anno` |

Nella sandbox compare l'avviso "Varie funzionalità sospese: un'attività obbligatoria è scaduta" (verifica dell'attività): da controllare prima di provare Checkout.

## Rimandato (aggiornato il 22/11/2026)
Dalla revisione finale del ramo `moduli-a-pagamento`, cose minori lasciate per dopo:
- In "Oggi", il riquadro "In numeri" mostra anche dati dei moduli spenti (pratiche aperte, bozze del registro, prossima trasmissione).
- In "Oggi", il pulsante principale del ruolo vendite ("Nuova vendita al banco") e della consulente ("Periodo da trasmettere") apre la pagina bloccata se il modulo è spento.
- Il test "ogni pagina ha un modulo" non si accorge di una pagina nuova di un modulo aggiuntivo dimenticata nella mappa: serve un elenco esplicito pagina → modulo.
- Due dispositivi che cambiano due moduli diversi nello stesso istante: uno dei due cambi si perde (il server sostituisce l'elenco intero; andrebbe fuso per modulo). Con Stripe l'attivazione passerà dal server e il problema sparisce.
- Barra del telefono: resta a 4–5 colonne anche quando le schede sono meno.
- "Bonificato oggi" non chiede conferma e non si annulla.

Altro rimandato, già noto:
- Interruttori dei moduli in mano al cliente (Impostazioni → Moduli): con login e Stripe passano al server, il cliente non li tocca più.
- Capitoli del manuale operativo da etichettare per modulo.
- `setDatiRegistro` segna la presa in carico ma non la radiazione "da richiedere": se poi si attiva l'Accettazione, il passo della radiazione va controllato.
