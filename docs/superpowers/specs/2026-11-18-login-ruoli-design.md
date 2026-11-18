# Login, ruoli e più aziende sulla stessa piattaforma: progetto

18/11/2026 · prototipo. Primo passo verso le voci A2 (più aziende, dati separati), A4 (accesso utenti e ruoli) e A13 (pannello interno per noi) di `docs/ROADMAP.md`.

## Perché
Il gestionale si vende a più autodemolizioni. Tutte stanno su **una piattaforma unica** (decisione di Alessandro), ognuna con i suoi dati, invisibili alle altre. Alessandro, che vende e assiste la piattaforma, deve poter entrare in qualunque azienda cliente per darle assistenza. Dentro ogni azienda le persone lavorano con i loro ruoli: accettazione, smontatore, magazziniere, responsabile, vendite, consulente ambientale. In molte realtà la stessa persona fa più cose, per esempio smontaggio e accettazione: i ruoli si combinano.

C'è anche un motivo di sicurezza immediato. Oggi chiunque raggiunga il server (anche dal tunnel pubblico) legge e scrive tutto, e il collegamento dell'account eBay non è legato a nessuno (`/api/ebay/ritorno`, rilievo della revisione di sicurezza del 18/11). Con il login questo si chiude.

Oggi i ruoli sono simulati: il menu "Stai usando come" (`ROLE_USER` in `src/lib/store.ts`, voci per ruolo in `src/components/AppShell.tsx`) cambia schermata a chiunque, senza password. Tutti i dati stanno in un archivio unico (`.demo-data/state.json`, foto, `collegamenti.json`, `ebay.json`), sincronizzato per intero dai dispositivi tramite `/api/demo-state`.

## Obiettivi
1. **Login vero** su tutta la gestione: nessuna pagina o API della gestione risponde senza accesso.
2. **Più aziende, dati separati.** Ogni azienda ha il suo archivio, le sue foto, i suoi collegamenti e il suo eBay. Un utente vede solo l'azienda di cui fa parte.
3. **Super admin (Alessandro)** sopra tutte le aziende: elenco dei clienti, entra in qualunque azienda per assistenza, crea e gestisce aziende e utenti.
4. **Ruoli combinabili.** Ogni utente ha uno o più ruoli, scelti con caselle quando si crea. Chi ne ha più di uno passa dall'uno all'altro con il menu, che mostra solo i suoi.
5. **Accesso veloce sui dispositivi condivisi del piazzale**: si tocca il proprio nome e si mette un PIN di 4 cifre.
6. **Ogni ingresso di assistenza è visibile al cliente** nel suo registro attività.

## Non obiettivi (ora)
- Il responsabile che crea o modifica gli utenti della sua azienda: per ora lo fa solo il super admin, su richiesta scritta. Più avanti diventerà un permesso.
- Ruoli personalizzati per azienda (oltre ai sei esistenti) e permessi fini per singola azione.
- Controllo sul server dell'azione per ruolo: il server garantisce login e separazione tra aziende; il ruolo limita le schermate. Il controllo per azione arriva con il database dei dati (voce A1), quando il server non riceverà più l'intero archivio dal dispositivo. Limite noto, scritto anche nel documento per il cliente: chi ha accesso a un'azienda, con strumenti tecnici, può leggerne tutti i dati.
- "Vedi come questo utente" (entrare al posto di un dipendente): utile per l'assistenza, ma dopo.
- Registrazione libera delle aziende, abbonamenti, fatturazione del servizio (A12).
- Recupero password via email: per ora la reimposta il super admin.
- Un negozio online per ogni azienda (F8): resta un negozio solo, di un'azienda scelta in configurazione.
- Spostare i dati operativi (veicoli, ricambi, ordini...) nel database: restano file per azienda (vedi sotto).

## Anti-obiettivi (sarebbe un fallimento anche se funziona)
- Un dato di un'azienda visibile da un'altra, anche solo per un errore di indirizzo.
- Un operaio che per entrare impiega più di qualche secondo o deve scrivere un'email con i guanti.
- Un ingresso del super admin che il cliente non può vedere.
- Un dispositivo condiviso lasciato aperto a nome di qualcuno per ore.
- Il negozio online che smette di funzionare o che mostra dati interni.

## Approcci considerati
1. **Login fatto in casa** (funzioni di cifratura di Node, cookie firmato, utenti su file). Nessuna dipendenza, PIN su misura. Scartato da Alessandro: codice di sicurezza tutto nostro.
2. **Libreria Better Auth con un database** (scelto da Alessandro). Ha di serie organizzazioni (= aziende) con membri a più ruoli, amministratori di piattaforma, codice dal telefono (TOTP). Il database arriva prima di quanto previsto nel piano di lavoro, ma solo per utenti, aziende e accessi. Il PIN su dispositivo condiviso non c'è e va aggiunto come estensione.
3. **Servizio esterno** (Clerk e simili). Scartato: costo per utente, nessun accesso nome+PIN su dispositivo condiviso.

## Come funziona

### Piattaforma, aziende, utenti
- **Better Auth 1.7.x** con i plugin `organization` (azienda = organizzazione), `admin` (super admin di piattaforma) e `twoFactor` (codice dal telefono), più un plugin nostro per il PIN dei dispositivi (vedi sotto).
- **Database della piattaforma: SQLite**, un file nella cartella dati (`DATA_DIR/piattaforma.sqlite`). Contiene solo utenti, aziende, appartenenze, ruoli, sessioni, dispositivi, richieste scritte. Tabelle create con la CLI di Better Auth (`npx auth@latest migrate`) più le nostre.
- **Ruoli dell'azienda**: i sei esistenti (`Role` in `src/lib/types.ts`) definiti con `createAccessControl` e assegnati al membro; più ruoli per membro (Better Auth li salva separati da virgola). Ruoli di serie di Better Auth (`owner`, `admin`, `member`) non usati per le persone dell'azienda.
- **Super admin**: ruolo di piattaforma `superadmin` del plugin `admin`. Codice dal telefono **obbligatorio**: senza averlo attivato non entra in nessuna azienda. Il primo super admin si crea con un comando una tantum (`npx auth@latest create-admin` o uno script nostro), la password non è mai nel codice.

### Gestione aziende e utenti (solo super admin)
Area "Piattaforma" (es. `/piattaforma`), visibile solo al super admin:
- **Elenco aziende**: nome, numero utenti, ultimo accesso; "Nuova azienda"; "Entra per assistenza".
- **Scheda azienda → utenti**: nome, ruoli (caselle), modo d'accesso, stato. Azioni: crea, modifica ruoli, reimposta PIN o password, disattiva (ban del plugin `admin`: blocca l'accesso e chiude le sessioni), riattiva.
- **Modo d'accesso per utente**: con **email e password** (entra da qualunque dispositivo) e/o con **PIN** (entra solo dai dispositivi dell'azienda). Responsabile e consulente di norma email+password; operai di norma solo PIN. Lo decide il super admin utente per utente.
- **Richiesta scritta**: quando crea un utente o ne cambia i ruoli, il super admin allega la richiesta dell'azienda (PDF o foto) e/o ne scrive gli estremi (data, chi la firma). Resta nella scheda dell'utente, con data e autore della modifica: è la prova di chi ha autorizzato cosa. Obbligatoria? Proposta: obbligatoria per creare utenti e cambiare ruoli, facoltativa per reimpostare PIN/password.
- Ogni modifica (utente creato, ruoli cambiati, disattivato, PIN reimpostato) entra nel registro attività dell'azienda.

### Ingresso per assistenza
- Dall'elenco aziende, "Entra per assistenza" chiede un **motivo** (testo breve, obbligatorio). La sessione del super admin prende quell'azienda come azienda attiva; il super admin non è membro dell'azienda ma il server glielo permette per ruolo di piattaforma.
- Dentro l'azienda ha **tutti i ruoli** a disposizione nel menu e una **fascia sempre visibile** "Assistenza in corso · <azienda> · Esci".
- Nel registro attività dell'azienda: "Ingresso assistenza" con motivo e ora, "Uscita assistenza", e ogni azione fatta nel frattempo a nome "Alessandro (assistenza)".
- L'ingresso scade da solo dopo un tempo massimo (proposta: 2 ore) e va rinnovato con un nuovo motivo.

### Accesso con email e password
Pagina di accesso unica. Chi ha una sola azienda entra direttamente; il super admin arriva all'elenco aziende. Dopo il login, il menu "Stai usando come" mostra solo i ruoli dell'utente; il primo è quello di partenza, l'ultimo usato viene ricordato.

### Dispositivi condivisi e PIN
- **Registrare un dispositivo**: un responsabile (o il super admin) entra con email e password sul telefono o tablet e tocca "Usa come dispositivo dell'azienda", dandogli un nome ("Tablet piazzale 1"). Il dispositivo riceve un **cookie di dispositivo** di lunga durata (casuale, HttpOnly, salvato cifrato in modo irreversibile sul server), legato a quell'azienda. Da quel momento la sua pagina d'ingresso è l'**elenco dei nomi** degli utenti con PIN di quell'azienda.
- **Entrare**: tocco sul nome → PIN di 4 cifre → sessione di quell'utente, con l'azienda del dispositivo. Obiettivo: meno di 5 secondi.
- **Blocco**: dopo **5 minuti** senza tocchi il dispositivo chiude la sessione e torna all'elenco dei nomi. Anche "Esci" torna all'elenco. La sessione da PIN dura al massimo un turno (proposta: 10 ore) anche se si usa di continuo.
- **PIN sbagliato**: dopo **5 tentativi** quel nome si blocca per **15 minuti** su tutti i dispositivi; il blocco va nel registro.
- **Revocare un dispositivo** (perso, rotto): dalla scheda azienda (super admin) o dalle impostazioni dell'azienda (responsabile: vede e revoca i dispositivi, non gli utenti). Il dispositivo torna alla pagina di accesso normale.
- I PIN sono salvati cifrati in modo irreversibile, come le password. Due persone possono avere lo stesso PIN: è il nome toccato che dice chi è.

### Dati separati per azienda
- Ogni azienda ha una cartella: `DATA_DIR/aziende/<idAzienda>/` con `state.json`, `foto/`, `collegamenti.json`, `ebay.json`. Le API esistenti (`/api/demo-state`, `/api/foto`, `/api/collegamenti`, `/api/ebay/*`, `/api/indirizzo`) ricavano l'azienda **sempre dalla sessione**, mai da un parametro della richiesta.
- `src/lib/server-data.ts` resta il solo punto che sa dove stanno i file: dà la cartella di un'azienda a partire dal suo id.
- Il dispositivo tiene in memoria i dati di un'azienda sola: se sullo stesso browser entra qualcuno di un'altra azienda (caso del super admin che cambia azienda), i dati locali si svuotano e si ricaricano dal server.
- **Registro attività**: chi ha fatto l'azione viene dalla sessione (nome della persona, ruolo in uso, nome del dispositivo), non più dalla tabella fissa `ROLE_USER`.
- **Collegamento eBay**: lo stato dell'autorizzazione è legato all'utente e all'azienda della sessione che l'ha avviato; il ritorno da eBay è accettato solo nella stessa sessione, e solo da un responsabile o dal super admin. Chiude il rilievo di sicurezza aperto.

### Pagine pubbliche
- Restano senza login: **negozio online**, pagina **eBay simulato**, sito vetrina (`/scopri`, `/news`, `robots`, `sitemap`), pagina di accesso, API di Better Auth.
- Il negozio oggi legge e scrive l'intero archivio come la gestione. Dopo: legge un **catalogo pubblico** (solo annunci online e i campi da mostrare, dell'azienda del negozio scelta in configurazione) e invia gli ordini a un **endpoint pubblico per gli ordini**, dove il server crea l'ordine nell'archivio di quell'azienda con le stesse regole di oggi (prezzo con l'8%, pezzo più vecchio, annuncio online).
- Le foto dei ricambi servono anche al negozio: le foto dei pezzi degli annunci online restano visibili senza login; le altre richiedono l'accesso.
- QR delle etichette (`/r/...`, `/u/...`) e pagine di stampa (etichette, certificato, documento) vanno dietro il login: si scansionano dai dispositivi dell'azienda.

### Dati demo e passaggio
- Al primo avvio la cartella dati attuale diventa la prima azienda, "Autodemolizione demo", con utenti demo corrispondenti alle persone di `ROLE_USER` (stessi nomi e ruoli), PIN e password di prova scritti nel file dei dati demo, mai nell'interfaccia.
- "Ripristina dati demo" agisce solo sull'azienda in cui si è, e solo per responsabile o super admin.
- Prove sempre su una cartella dati separata (`DATI_DIR`) e una porta nuova: sulla porta 3210 gira il server di Alessandro con i suoi dati.

## Scelte prese dopo la revisione (mie, da confermare leggendo)
- **Dove gira**: in questo giro su un solo processo Node sempre acceso (il Mac di Alessandro, con il tunnel HTTPS), con disco scrivibile: SQLite e cartelle per azienda vanno bene. Dove ospitare la piattaforma in produzione non è deciso e non fa parte di questo giro; quando si sceglierà, SQLite passa a Postgres (Better Auth lo supporta) e i file a un archivio cloud. Cookie `Secure` quando la richiesta arriva in HTTPS (tunnel), non su `localhost`. Il nome della cartella dati resta la variabile esistente `DATI_DIR` (qui chiamata `DATA_DIR` come la costante in `server-data.ts`).
- **Super admin non membro**: non viene aggiunto come membro nascosto. Un solo controllo sul server, in un punto, decide "questa sessione può usare questa azienda": membro dell'azienda, oppure super admin con un ingresso di assistenza valido (motivo registrato, non scaduto). Testato a fondo, perché è la porta tra un'azienda e l'altra.
- **Più dispositivi che scrivono insieme**: resta l'unione per id di oggi in `/api/demo-state`, con il suo blocco sul server; l'endpoint pubblico degli ordini del negozio passa dallo stesso blocco e dalla stessa unione, così un ordine non si perde per una scrittura concorrente di un dispositivo.
- **Blocco dopo 5 minuti e turno di 10 ore valgono anche sul server**: le sessioni da PIN scadono dopo 5 minuti senza richieste (ogni richiesta le allunga) e comunque dopo 10 ore. Il dispositivo, scaduta la sessione, prima prova a inviare le modifiche in sospeso; se non ci riesce le tiene e le invia al prossimo accesso sullo stesso dispositivo (ogni modifica porta già il nome di chi l'ha fatta nel registro). Le sessioni con email e password seguono la durata normale di Better Auth.
- **Azienda del negozio**: variabile d'ambiente (es. `NEGOZIO_AZIENDA`, l'identificativo dell'azienda). Catalogo e ordini pubblici usano solo quella. La foto pubblica si serve solo se, al momento della richiesta, appartiene a un pezzo di un annuncio online di quell'azienda.
- **Passaggio dei dati attuali**: i dati sulla porta 3210 sono finti (solo Alessandro li usa). Al primo avvio la cartella attuale si **copia** in `aziende/<id demo>/`, l'originale resta dov'è come copia di sicurezza; nessun ritorno al vecchio formato.
- **Primo accesso del super admin**: obbligatorio attivare il codice dal telefono (QR da inquadrare con un'app di autenticazione, più codici di riserva da conservare) prima di poter entrare in un'azienda.
- **Richiesta scritta**: il file va nella cartella dell'azienda (`aziende/<id>/richieste/`), al massimo 10 MB, PDF o foto; nel database solo il riferimento, la data, gli estremi e chi l'ha caricata.
- **PIN e furto del dispositivo**: oltre al blocco per nome, un limite per dispositivo: 20 PIN sbagliati in 15 minuti bloccano il dispositivo intero, che va sbloccato da un responsabile con la password (o revocato). Il blocco va nel registro.

## Lasciato a chi costruisce
- Driver SQLite: `better-sqlite3` (consigliato dalla documentazione di Better Auth) o `node:sqlite` incluso in Node (qui Node 26).
- Utenti solo-PIN senza email: Better Auth vuole un'email; si può generarne una interna non usabile per l'accesso, oppure usare il plugin `username`. Scegliere la soluzione più semplice che impedisca a quegli utenti l'accesso con password.
- Come il plugin PIN crea la sessione (endpoint del plugin con l'adattatore interno di Better Auth) e come si ricorda il ruolo in uso.
- Protezione delle pagine in `proxy.ts` (Next 16) più il controllo della sessione in ogni API: la protezione in `proxy.ts` da sola non basta.
- Aspetto delle pagine di accesso, elenco nomi, area Piattaforma, nel linguaggio visivo esistente.
- Come estrarre dalla logica del negozio nel client quello che serve al server per creare un ordine pubblico.

## Domande aperte per Alessandro
(nessuna al momento della stesura: vedi le proposte segnate "Proposta" sopra)
