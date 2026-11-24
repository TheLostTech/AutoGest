# Accesso, ruoli e aziende

## Variabili d'ambiente

| Variabile | A cosa serve |
|---|---|
| `BETTER_AUTH_SECRET` | Segreto che firma le sessioni e cifra i codici del secondo fattore. Lungo, casuale, mai nel codice. Se manca, al primo avvio il server ne genera uno e lo scrive in `DATI_DIR/.segreto-accesso` (leggibile dal solo proprietario): vale anche con `next dev`, il valore di prova di Better Auth non si usa mai. |
| `DATI_DIR` | Cartella dei dati. Di serie `.demo-data` nel progetto; sul server dell'azienda una cartella a scelta (es. `D:\AutoGest\dati`). Per il backup basta copiarla. |
| `SUPERADMIN_EMAIL`, `SUPERADMIN_PASSWORD`, `SUPERADMIN_NOME` | Primo super admin (vedi sotto). La password è di almeno 8 caratteri. |
| `NEGOZIO_AZIENDA` | Id dell'azienda che vende dal negozio pubblico. Se manca, è l'azienda demo. |
| `DEMO_UTENTI` | Con `NODE_ENV=production` gli utenti demo si creano solo se vale `1`. |
| `DEMO_PUBBLICA` | Solo per la vetrina online (Vercel): con `1` "Apri la demo" (`/demo`) entra senza credenziali nell'azienda demo come la responsabile, e chi non ha una sessione ci rientra da solo. Il login vero resta su `/accesso?manuale=1`. Va con `DEMO_UTENTI=1` e `DATI_DIR` in una cartella scrivibile (su Vercel `/tmp/...`, che si azzera da sola). Mai sul server di un'azienda. |
| `INDIRIZZO_GESTIONALE` | Indirizzo pubblico del gestionale (es. quello del tunnel): è l'unico altro sito da cui Better Auth accetta le richieste. |

## Primo avvio

All'avvio il server (file `src/instrumentation.ts`, funzione `avviaPiattaforma`) fa da solo:

1. crea le tabelle di `piattaforma.sqlite` (utenti, aziende, sessioni, dispositivi, PIN);
2. se non esiste nessuna azienda, crea **Autodemolizione demo** con i suoi utenti di prova (nomi e ruoli in `src/lib/accesso/demo-utenti.ts`; password e PIN sono generati a caso e scritti solo in `DATI_DIR/credenziali-demo.json`, leggibile dal solo proprietario: non si ripetono né nell'interfaccia né nei log). In produzione gli utenti demo si creano solo con `DEMO_UTENTI=1`;
3. nella stessa prima preparazione **copia** nell'azienda demo i dati di prima (`state.json`, `foto/`, `visure/`, `collegamenti.json`, `ebay.json` della cartella dati). Gli originali restano dove sono, come copia di sicurezza. Se non ci sono dati di prima, l'archivio demo lo scrive il server stesso;
4. se `SUPERADMIN_EMAIL` è impostata e non c'è ancora un super admin, lo crea.

La preparazione dell'azienda demo avviene una sola volta (un marcatore nell'azienda e il file `.passaggio-fatto` nella sua cartella): agli avvii dopo nulla viene ricreato né ricopiato, quindi un utente o una foto tolti non tornano.
Se l'avvio non riesce, il server resta acceso, scrive il motivo nel suo registro e le API rispondono 503 ("il gestionale non è pronto") finché non si risolve e si riavvia.

## Super admin

Si crea impostando le variabili `SUPERADMIN_*` al primo avvio (la password non va mai nel codice). Dopo l'accesso con email e password deve attivare il codice dal telefono (pagina Sicurezza): senza codice non entra in nessuna azienda. L'ingresso in un'azienda è "di assistenza", dura 2 ore e lascia una riga nel registro attività dell'azienda.

## Dispositivi condivisi (nome e PIN)

Il responsabile entra con email e password, apre Impostazioni, Dispositivi e usa "Usa come dispositivo dell'azienda": il suo account esce e il browser mostra l'elenco dei nomi. Chi lavora tocca il proprio nome e scrive il PIN (4 cifre). Dopo 5 minuti senza tocchi (in qualunque scheda dello stesso browser, anche le etichette) il dispositivo tiene nel browser le modifiche non ancora inviate, chiude la sessione e torna all'elenco; le invia al prossimo accesso su quel dispositivo.

Su un browser registrato come dispositivo **ogni** sessione ha le stesse regole, anche quella con email e password (per esempio il responsabile che entra per sbloccare il tablet): blocco dopo 5 minuti senza tocchi e al massimo 10 ore. Quando il responsabile sblocca proprio quel tablet, il suo account esce subito e il tablet torna all'elenco dei nomi.

## Tentativi di accesso

Il server limita i tentativi anche con `next dev` (Better Auth di serie lo fa solo in produzione): al massimo 5 al minuto per l'accesso con email e per il codice dal telefono, 10 al minuto per il PIN (più tablet dello stesso piazzale escono dallo stesso indirizzo), 5 per la registrazione di un dispositivo; oltre, la risposta è 429 ("troppe richieste"). Il conto è per indirizzo IP preso da `cf-connecting-ip`, che Cloudflare Tunnel riscrive sempre (`x-forwarded-for` invece lo può scrivere chiunque); senza quell'intestazione (localhost, rete interna) tutte le richieste dello stesso percorso condividono un contatore, che è più severo. Chi raggiunge il server direttamente (non dal tunnel) può scriverla da sé: su un server esposto oltre il tunnel si mette in ascolto solo su 127.0.0.1 oppure si toglie l'intestazione all'ingresso. La difesa vera resta il blocco per account qui sotto.

Cambiare indirizzo a ogni tentativo non serve: dopo **10 password sbagliate in 15 minuti per lo stesso account** l'accesso a quell'account è rifiutato per 15 minuti, anche con la password giusta (i tentativi si contano all'arrivo, quindi nemmeno tante richieste in parallelo superano il limite). Le email che non esistono hanno un solo contatore comune, 30 tentativi al minuto: riempirlo rifiuta solo altri tentativi su email inesistenti, mai gli account veri, e nel registro di ogni sua azienda resta "Accesso bloccato per 15 minuti". Il codice dal telefono ha lo stesso blocco per account (10 codici sbagliati di fila → 15 minuti, di Better Auth). Tutti questi conti sono in memoria: si azzerano al riavvio.

Dal browser si raggiungono solo gli endpoint di Better Auth che l'app usa (elenco in `src/lib/auth/percorsi-auth.ts`): tutti gli altri rispondono 404 (niente cambio di nome o email dal profilo, niente "lascia l'azienda", niente azioni del pannello admin).

## Più schede e cambio di azienda

Ogni scheda della gestione resta dell'azienda con cui è partita e lo dice al server a ogni chiamata (intestazione `x-azienda`). Se nel frattempo la sessione è passata a un'altra azienda (il super admin entra per assistenza in un'altra azienda da un'altra scheda), il server rifiuta con 409 e la scheda vecchia smette di leggere e scrivere: le modifiche non ancora inviate restano in sospeso per la sua azienda e la scheda si ricarica (o mostra "Azienda cambiata" con il pulsante Ricarica). All'ingresso in un'azienda il browser toglie le copie locali delle altre aziende (restano solo le loro modifiche in sospeso, scartate dopo 24 ore).

Uscire dall'account (menu, Piattaforma, registrazione di un dispositivo, sessione scaduta) durante un ingresso di assistenza chiude l'ingresso e lascia "Uscita assistenza" nel registro dell'azienda, come il pulsante della fascia.

## Dove stanno i dati

- Di tutta la piattaforma, in `DATI_DIR`: `piattaforma.sqlite` (utenti, aziende, ruoli, sessioni), `.chiave-collegamenti` (chiave che cifra i segreti dei collegamenti: non spostarla) e, senza `BETTER_AUTH_SECRET`, `.segreto-accesso` (se si perde, tutte le sessioni si chiudono e il super admin deve riattivare il codice dal telefono).
- Di ogni azienda, in `DATI_DIR/aziende/<id azienda>/`: `state.json` (archivio), `foto/`, `visure/` (PDF delle visure PRA), `collegamenti.json`, `ebay.json`, `richieste/` (richieste scritte). `state.json` e `collegamenti.json` si scrivono con file temporaneo e rinomina; se uno dei due esiste ma non si legge, il server lo segnala e non lo sovrascrive.

## Limite noto

**Ruoli:** Il server controlla l'accesso, la separazione tra aziende e, per ruolo, alcune azioni delicate (collegamenti, collegamento e politiche eBay, richiesta della visura PRA, ripristino dei dati, gestione dei dispositivi, Piattaforma); tutto il resto è limitato per ruolo solo nelle schermate fino al database dei dati (A1).
Il pagamento simulato del negozio vale solo nel negozio dell'azienda demo; in ogni altra azienda un ordine senza pagamento attivo viene rifiutato.
