# Accesso, ruoli e aziende

## Variabili d'ambiente

| Variabile | A cosa serve |
|---|---|
| `BETTER_AUTH_SECRET` | Segreto che firma le sessioni. **Obbligatorio con `next start`** (in sviluppo c'è un valore di prova). Lungo, casuale, mai nel codice. |
| `DATI_DIR` | Cartella dei dati. Di serie `.demo-data` nel progetto; sul server dell'azienda una cartella a scelta (es. `D:\AutoGest\dati`). Per il backup basta copiarla. |
| `SUPERADMIN_EMAIL`, `SUPERADMIN_PASSWORD`, `SUPERADMIN_NOME` | Primo super admin (vedi sotto). La password è di almeno 8 caratteri. |
| `NEGOZIO_AZIENDA` | Id dell'azienda che vende dal negozio pubblico. Se manca, è l'azienda demo. |
| `DEMO_UTENTI` | Con `NODE_ENV=production` gli utenti demo si creano solo se vale `1`. |
| `INDIRIZZO_GESTIONALE` | Indirizzo pubblico del gestionale (es. quello del tunnel): è l'unico altro sito da cui Better Auth accetta le richieste. |

## Primo avvio

All'avvio il server (file `src/instrumentation.ts`, funzione `avviaPiattaforma`) fa da solo:

1. crea le tabelle di `piattaforma.sqlite` (utenti, aziende, sessioni, dispositivi, PIN);
2. se non esiste nessuna azienda, crea **Autodemolizione demo** con i suoi utenti di prova (nomi e ruoli in `src/lib/accesso/demo-utenti.ts`; password e PIN sono generati a caso e scritti solo in `DATI_DIR/credenziali-demo.json`, leggibile dal solo proprietario: non si ripetono né nell'interfaccia né nei log). In produzione gli utenti demo si creano solo con `DEMO_UTENTI=1`;
3. nella stessa prima preparazione **copia** nell'azienda demo i dati di prima (`state.json`, `foto/`, `collegamenti.json`, `ebay.json` della cartella dati). Gli originali restano dove sono, come copia di sicurezza. Se non ci sono dati di prima, l'archivio demo lo scrive il server stesso;
4. se `SUPERADMIN_EMAIL` è impostata e non c'è ancora un super admin, lo crea.

La preparazione dell'azienda demo avviene una sola volta (un marcatore nell'azienda e il file `.passaggio-fatto` nella sua cartella): agli avvii dopo nulla viene ricreato né ricopiato, quindi un utente o una foto tolti non tornano.
Se l'avvio non riesce, il server resta acceso, scrive il motivo nel suo registro e le API rispondono 503 ("il gestionale non è pronto") finché non si risolve e si riavvia.

## Super admin

Si crea impostando le variabili `SUPERADMIN_*` al primo avvio (la password non va mai nel codice). Dopo l'accesso con email e password deve attivare il codice dal telefono (pagina Sicurezza): senza codice non entra in nessuna azienda. L'ingresso in un'azienda è "di assistenza", dura 2 ore e lascia una riga nel registro attività dell'azienda.

## Dove stanno i dati

- Di tutta la piattaforma, in `DATI_DIR`: `piattaforma.sqlite` (utenti, aziende, ruoli, sessioni) e `.chiave-collegamenti` (chiave che cifra i segreti dei collegamenti: non spostarla).
- Di ogni azienda, in `DATI_DIR/aziende/<id azienda>/`: `state.json` (archivio), `foto/`, `collegamenti.json`, `ebay.json`, `richieste/` (richieste scritte).

## Limite noto

I ruoli sono controllati **solo nelle schermate**: finché non arriva il database dei dati, chi ha accesso all'azienda può leggere e scrivere tutto l'archivio dell'azienda dalle API (la separazione tra aziende, invece, è sempre garantita dalla sessione).
Il pagamento simulato del negozio vale solo nel negozio dell'azienda demo; in ogni altra azienda un ordine senza pagamento attivo viene rifiutato.
