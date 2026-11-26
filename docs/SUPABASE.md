# Dati su Supabase

Dove stanno i dati quando l'app gira online (Vercel) e come guardarli.

## Due modi di salvare

Il codice passa sempre da `src/lib/deposito/` (`tipi.ts`, `index.ts`, `disco.ts`, `supabase.ts`).

- **Senza variabili di Supabase**: tutto su disco in `DATI_DIR` (server dell'azienda, prove in locale).
- **Con `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` e `DATABASE_URL` tutte e tre**: tutto su Supabase.
- **Solo una o due delle tre**: l'avvio si ferma con un errore chiaro ("Configurazione Supabase incompleta"). Mai un mezzo e mezzo.

## Progetti

Organizzazione **Piazzale** (piano gratuito, separata da LOSTAR Org dove sta Futumoney).

| Progetto | Ref | Per cosa |
|---|---|---|
| `Piazzale` | `vfdccawezxolcblhtavk` | Produzione. |
| `Piazzale prove` | `syorhwlfihngplsaiwwv` | Anteprime di Vercel e prove in locale. |

Su Vercel le variabili dell'ambiente **Preview** per ora sono impostate solo per il ramo `registrazione-pagamento`; quelle di **Production** non ci sono ancora (si impostano all'unione in `main`).

## Variabili

| Variabile | A cosa serve |
|---|---|
| `SUPABASE_URL` | Indirizzo del progetto. |
| `SUPABASE_SERVICE_ROLE_KEY` | Chiave segreta `sb_secret_…`. Solo sul server, mai nel browser né nel codice. |
| `DATABASE_URL` | Stringa del pooler in modalità transazione (porta 6543): `postgresql://postgres.<ref>:<password>@aws-0-eu-central-1.pooler.supabase.com:6543/postgres`. Dalla stringa copiata dal pannello vanno tolte le parentesi quadre di `[YOUR-PASSWORD]`. |
| `BETTER_AUTH_SECRET` | Obbligatoria online: senza disco non c'è dove scrivere il segreto di riserva. |
| `CHIAVE_COLLEGAMENTI` | 64 caratteri esadecimali (`openssl rand -hex 32`), obbligatoria online. Sostituisce il file `.chiave-collegamenti`. |
| `RESEND_API_KEY`, `EMAIL_MITTENTE` | Email di conferma e avvisi. Mittente: `Lostar Technology <noreply@lostartechnology.com>`. |
| `BETTER_AUTH_URL` | Indirizzo pubblico per i link nelle email; obbligatoria in produzione fuori da Vercel (su Vercel si deduce dal progetto). |
| `CRON_SECRET` | Almeno 16 caratteri: protegge `/api/pianificato/prova`, il giro giornaliero degli avvisi di fine prova. |
| `PIAZZALE_SENZA_BOTID` | `1` solo per i server fuori da Vercel in produzione: salta BotID alla registrazione. |

Preview e Production usano valori diversi per i due segreti. Nei documenti non si scrive mai una chiave, una password o una stringa di connessione vera.

Su Vercel l'indirizzo IP per i limiti di tentativi arriva da `x-real-ip` (`VERCEL=1`); vedi `docs/ACCESSO.md`.

## Cosa sta dove

**Postgres**
- Tabelle di Better Auth: utenti, sessioni, aziende (`organization`), ruoli (`member`), PIN, contatori dei limiti.
- `documento`: una riga per azienda e tipo (`archivio`, `abbonamento`, `collegamenti`, `ebay`, `richieste`), contenuto in `jsonb`.
- `conto_account`: il blocco dopo troppe password sbagliate, per account.

**Spazio privato (Storage)**: bucket `piazzale`, percorso `<aziendaId>/<cartella>/<nome>`. Dentro foto, allegati, visure e richieste. Il bucket è privato: i file escono solo dalle route dell'app, mai con indirizzi `supabase.co`. Ogni foto o PDF caricato può pesare al massimo 3 MB (Vercel accetta richieste fino a 4,5 MB).

*In arrivo (altro piano):* le foto restano sul dispositivo e online vanno solo quelle dei ricambi in vendita.

## Sicurezza

- RLS attiva su ogni tabella dello schema `public`; a ogni avvio `proteggiTabelle` (`src/lib/db/schema.ts`) toglie i privilegi ad `anon` e `authenticated`. Si entra solo dal server con la chiave segreta.
- La connessione a Postgres è sempre verificata con `src/lib/db/supabase-ca.crt` (Supabase Root 2021 CA, **scade il 26/04/2031**; si riscarica dal pannello con "Download certificate"). Senza TLS solo per localhost.

## Come guardare i dati

Nel pannello del progetto:
- **Table Editor**, tabella `documento` (filtro per `azienda_id`), `conto_account`, e `user`, `organization`, `member` di Better Auth.
- **Table Editor**, sezione delle viste, `registrazioni`: una riga per azienda registrata (azienda, titolare, email, telefono, registrata, confermata, fine_prova, giorni_rimasti, stato, moduli_pagati, consenso_commerciale), le più recenti in alto. Oppure nello **SQL Editor**: `select * from registrazioni;`. `giorni_rimasti` c'è solo durante la prova (0 se è finita); `moduli_pagati` solo con un abbonamento in corso. È una vista di sola lettura, creata all'avvio, e `anon`/`authenticated` non la vedono.
- **Storage**, bucket `piazzale`.

## Prove in locale

Nel `.env.local` (non versionato) di `Piazzale prove`: `PROVA_DATABASE_URL`, `PROVA_SUPABASE_URL`, `PROVA_SUPABASE_KEY`. Poi:

```
node --env-file=.env.local --import ./scripts/alias-ts.mjs --test src/lib/deposito/supabase.test.ts
```

## Limiti del piano gratuito

- Il progetto va in pausa dopo 7 giorni senza richieste.
- 500 MB di database, 1 GB di file.
- Niente backup giornalieri.

Si passa a **Pro** quando arrivano i primi clienti paganti, o quando lo spazio usato supera metà del limite.
