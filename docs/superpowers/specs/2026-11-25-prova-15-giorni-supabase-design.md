# Registrazione libera, prova di 15 giorni e dati su Supabase

Data: 25/11/2026. Parte dal design del 22/11 (`2026-11-22-registrazione-pagamento-design.md`) e ne cambia tre cose: niente codice invito, niente blocco al primo veicolo, dati nel cloud.

## Perché

La demo aperta a tutti (pulsante "Apri la demo", tutti dentro come Sara) non funziona come vetrina: "è un gran casino, nessuno ci capisce niente" (Alessandro, 25/11/2026). Spenta lo stesso giorno (`DEMO_PUBBLICA=0` su Vercel).

Al suo posto Alessandro vuole **"Registrati gratis"**:

1. chi arriva sulla landing si registra e crea la sua autodemolizione;
2. la usa **15 giorni con tutto acceso** (Magazzino, Pratiche, Ambiente, Banco), ognuno con i dati suoi;
3. al 16° giorno il gestionale si blocca e chiede di pagare i moduli (Stripe, mese o anno);
4. noi ci teniamo le registrazioni: sono i contatti da trasformare in clienti.

Oggi il gestionale su Vercel non regge niente di tutto questo: scrive utenti, archivio e foto su disco, e su Vercel il disco è temporaneo (`/tmp`, si svuota a ogni riavvio). Una registrazione sparirebbe dopo pochi minuti. Per questo i dati vanno su **Supabase** (deciso da Alessandro il 25/11/2026).

## Obiettivi

- Pulsante "Registrati gratis" sulla landing al posto di "Apri la demo", verso `/registrati`.
- Registrazione aperta, senza codice invito.
- Prova di 15 giorni dalla registrazione, con tutti i moduli accesi; conto alla rovescia visibile al titolare.
- Al termine: blocco a tutto schermo con il riquadro di pagamento già esistente sul ramo, moduli scelti dal cliente, dati conservati e visibili.
- Utenti, sessioni, archivi, foto, PDF e abbonamenti salvati su Supabase quando il gestionale gira su Vercel, così niente si perde.
- In locale e nei test il gestionale continua a funzionare con la cartella dati su disco, come oggi.

## Non obiettivi

- Dividere l'archivio in tabelle (veicoli, ricambi, clienti): l'archivio resta un documento per azienda.
- Statistiche tra aziende diverse.
- Recupero della password via email e altre email oltre a conferma e fine prova: restano rimandate.
- Chiavi Stripe vere: si decidono a parte (vedi "Domande aperte").
- Un database diverso per ogni azienda.

## Anti-obiettivi (fallimento anche se funziona)

- Una registrazione o un dato di un cliente in prova che si perde.
- Un'azienda che vede i dati, le foto o i PDF di un'altra.
- Due tablet della stessa azienda che salvano insieme e uno cancella il lavoro dell'altro.
- Un cliente bloccato prima del 16° giorno, o uno che lavora gratis oltre senza che nessuno se ne accorga.
- Chiavi di Supabase che finiscono nel browser o nel codice versionato.

## Vincoli

- Next 16 (leggere `node_modules/next/dist/docs/` prima di scrivere codice, come dice `AGENTS.md`); `cacheComponents` acceso: niente `export const dynamic`.
- Vercel: funzioni con corpo della richiesta al massimo **4,5 MB**. Oggi `api/foto` accetta foto fino a 4 MB in base64, cioè circa 5,4 MB di corpo: online si romperebbe.
- Vercel: più istanze del server possono girare insieme; niente stato condiviso in memoria. Oggi sono in memoria il limite delle richieste di Better Auth (`storage: "memory"`), i tentativi per account (`tentativi-account.ts`) e il blocco che mette in fila le scritture dell'archivio (`aggiornaStato`).
- Supabase: progetto **nuovo "Piazzale"**, separato da Futumoney, in Europa (`eu-central-1`, Francoforte), in un'**organizzazione Supabase gratuita** creata da Alessandro (deciso il 25/11/2026: gratis per ora). Il piano gratuito mette in pausa il progetto dopo 7 giorni senza visite: con clienti veri si passa a Pro.
- Il ramo `registrazione-pagamento` (cartella `.claude/worktrees/moduli`) ha già registrazione, Stripe, blocco e riquadro di pagamento (427 test, `docs/PAGAMENTI.md`), ma è indietro di 21 commit rispetto a `main` e non è mai stato unito.

## Strade considerate (per i dati)

1. **Database più spazio file di Supabase, dietro un passaggio unico.** Scelta da Alessandro il 25/11/2026.
   - Utenti e sessioni nel Postgres di Supabase tramite Better Auth (che oggi usa SQLite solo attraverso il suo adattatore: nessuna query scritta a mano).
   - Archivio di ogni azienda in una riga, con numero di versione; scritture in transazione.
   - Documenti piccoli (abbonamento, collegamenti, eBay, richieste) in righe.
   - Foto, visure e allegati nello spazio file privato di Supabase.
   - Un'unica interfaccia di salvataggio nel codice: su disco in locale e nei test, Supabase online.
2. **Solo lo spazio file di Supabase usato come disco.** Scartata: il login ha comunque bisogno di un database, e due salvataggi insieme dell'archivio si sovrascrivono (manca il "file temporaneo e rinomina").
3. **Archivio diviso in tabelle.** Scartata per ora: settimane in più senza vantaggio per la prova.

Fuori dalle strade per i dati è stata scartata anche la **demo aperta** (provata e spenta il 25/11) e il **server con disco fisso** (Alessandro ha scelto Supabase).

## Come funziona

### 1. Salvataggio: un passaggio unico, due modi

- Un modulo nuovo (es. `src/lib/deposito/`) con le operazioni che oggi i 15 file fanno direttamente su disco: leggere/scrivere l'archivio di un'azienda con versione, leggere/scrivere un documento JSON per azienda (`abbonamento`, `collegamenti`, `ebay`, richieste), salvare/leggere/elencare/togliere un file binario (foto, visure, allegati).
- Due realizzazioni: **disco** (il comportamento di oggi, sotto `DATI_DIR`) e **Supabase**. Si sceglie con le variabili d'ambiente: se c'è `SUPABASE_URL` si usa Supabase, altrimenti il disco.
- I file da portare sul passaggio unico (contati il 25/11 sul ramo): `api/foto`, `api/foto/[name]`, `api/registrazione`, `abbonamento-server`, `accesso/avvio`, `archivio-azienda`, `archivio-file`, `auth/segreto`, `auth/server`, `cifratura`, `collegamenti-file`, `ebay/archivio`, `ebay/sandbox`, `piattaforma/richieste-file`, `visura-server`.

### 2. Cosa va dove su Supabase

| Oggi su disco | Su Supabase |
|---|---|
| `piattaforma.sqlite` (Better Auth: utenti, aziende, ruoli, sessioni, PIN, assistenza, inviti) | Postgres, tabelle create dalle migrazioni di Better Auth (`getMigrations`) come oggi |
| `aziende/<id>/state.json` | tabella `archivio` (`azienda_id`, `version`, `schema`, `dati` jsonb, `aggiornato`) |
| `aggiungiEventi` sul registro attività | stessa riga, dentro la stessa transazione |
| `abbonamento.json`, `collegamenti.json`, `ebay.json`, richieste | tabella `documento` (`azienda_id`, `tipo`, `dati` jsonb, `aggiornato`) |
| `foto/`, `visure/`, `allegati/`, `richieste/` (PDF, immagini) | spazio file privato, un percorso per azienda: `<azienda_id>/foto/<nome>` |
| `.segreto-accesso` | variabile `BETTER_AUTH_SECRET` su Vercel |
| `.chiave-collegamenti` | variabile d'ambiente (nome a scelta del builder) su Vercel |
| `credenziali-demo.json` | non serve più online: niente utenti demo su Vercel |

- **Separazione tra aziende.** Il gestionale parla con Supabase solo dal server, con la chiave di servizio, e ogni lettura e scrittura passa per l'azienda della sessione (`accessoDaRichiesta`), come oggi. Le tabelle hanno la sicurezza per riga (RLS) attiva e nessuna regola che apra l'accesso alla chiave pubblica: dal browser non si legge niente.
- **Scritture dell'archivio.** `aggiornaStato` diventa una transazione: legge la riga con `FOR UPDATE`, applica la funzione, scrive con `version + 1`. Il 409 "versione diversa" resta uguale per il browser.
- **Foto online.** Il limite di `api/foto` scende sotto i 4,5 MB del corpo (es. 3 MB di foto); il gestionale già comprime le foto prima di mandarle, va verificato che stia sotto. Le foto si servono da `api/foto/[name]` leggendo dallo spazio file, con lo stesso controllo dell'azienda di oggi.
- **Memoria condivisa.** Il limite delle richieste di Better Auth passa a `storage: "database"`. I tentativi per account (`tentativi-account.ts`) passano in una tabella. Il resto della memoria (cache) può restare per istanza.
- **Avvio.** `instrumentation.ts` gira a ogni avvio di istanza: le migrazioni restano idempotenti. Online non si crea l'azienda demo; il super admin si crea dalle variabili come oggi.

### 3. Registrazione libera

Si parte dalla registrazione del ramo (`/registrati`, `POST /api/registrazione`) e si toglie il codice invito:

- campi: nome azienda, nome e cognome del titolare, email, password (≥ 10 caratteri), "Accetto le condizioni";
- più un campo **telefono** del titolare, facoltativo (scelta mia: servono contatti da richiamare; da confermare);
- la registrazione crea azienda, archivio vuoto, titolare `responsabile`, abbonamento nello stato `prova` (vedi 4), e fa entrare il titolare su "Oggi";
- protezione dai robot: limite per indirizzo (3 all'ora) già nel ramo, letto da `x-forwarded-for` di Vercel (oggi da `cf-connecting-ip` del tunnel), più **BotID di Vercel** sulla route di registrazione (scelta mia);
- i codici invito e la pagina Inviti della Piattaforma restano nel codice ma non servono più per registrarsi (scelta mia: si toglie il controllo, non la funzione).

### 4. Prova di 15 giorni

- Nuovo stato `prova` dell'abbonamento, con `fineProva` = momento della registrazione + 15 giorni. Prende il posto di `nuovo` per le aziende registrate.
- `moduliDaAbbonamento`: in `prova` **tutti i moduli** (deciso da Alessandro il 25/11/2026: offerta massima).
- `bloccato(abbonamento, ora)`: vero se `prova` e `ora ≥ fineProva`, oppure `scaduto`. Il conteggio dei veicoli non c'entra più. Si decide sempre sul server.
- Dal blocco in poi vale tutto quello che il design del 22/11 dice del blocco: scritture rifiutate con 402, letture sì, eBay continua, negozio online chiuso, modifiche in sospeso tenute fino al pagamento.
- **Il riquadro di pagamento** al blocco propone come spuntati i moduli che l'azienda ha usato davvero nella prova (scelta mia: almeno un dato salvato in quel modulo); il cliente può togliere o aggiungere. Il Magazzino è sempre incluso.
- **Conto alla rovescia** per il titolare: una fascia in cima "Prova gratuita: mancano N giorni", con "Scegli i moduli" che apre la pagina Abbonamento. Negli ultimi 3 giorni più evidente (scelta mia).
- Pagando durante la prova, l'abbonamento parte subito e la prova finisce (scelta mia: niente giorni regalati in coda).
- **Far scorrere la prova senza aspettare 15 giorni** (scelta mia). Durante la prova il cliente Stripe e il suo orologio di prova non esistono ancora (nascono al Checkout, `clientePer` in `src/lib/stripe/server.ts`), quindi non si usa l'orologio di Stripe. Con le chiavi di prova la pagina Abbonamento mostra, durante la prova, "Strumenti di prova" con "+1 giorno" e "+1 settimana" che spostano in avanti un orologio **dell'app** salvato nell'abbonamento dell'azienda (es. `spostamentoProva` in millisecondi); `bloccato` confronta `fineProva` con ora + spostamento. Registrare non chiama Stripe.

### 5. Landing e accesso

- `DEMO` e `REGISTRAZIONE` in `Sito.tsx` portano a `/registrati`; testo dei pulsanti "Registrati gratis" con sotto "15 giorni con tutto incluso, senza carta".
- Nella testata della landing resta "Accedi" verso `/accesso`.
- La demo pubblica resta nel codice ma **spenta online** (`DEMO_PUBBLICA` mai a 1 su Vercel): su `main` la usano `scripts/piazzale-test.sh` e l'app Android di prova per entrare come "Collaudo" in locale. Il pulsante della landing non ci porta più.
- La sezione "Come si attiva" di `/scopri` (oggi: registrazione → primo veicolo → Stripe) diventa registrazione → 15 giorni con tutto → scegli i moduli.

## Su che ramo si costruisce

- Primo passo: **unire `main` dentro `registrazione-pagamento`** (21 commit: app Android, ricerca per tipologia, nome Piazzale, landing nuova, demo pubblica). Approvando questo design Alessandro dà il via all'unione.
- Poi Supabase, poi prova e registrazione, poi landing.
- In `main` si unisce alla fine, quando tutto è provato su un'anteprima di Vercel.
- **Due progetti Supabase** nell'organizzazione gratuita (scelta mia; il piano gratuito ne permette due): **Piazzale** per la produzione e **Piazzale prove** per le anteprime di Vercel e le prove in locale. Su Vercel le variabili Supabase sono diverse per Production e Preview, così le registrazioni di prova non finiscono tra i contatti veri e le migrazioni di un'anteprima non toccano la produzione.

## Variabili d'ambiente nuove (Vercel)

| Variabile | A cosa serve |
|---|---|
| `SUPABASE_URL` | Indirizzo del progetto Piazzale. Se c'è, il salvataggio è su Supabase. |
| `SUPABASE_SERVICE_ROLE_KEY` (o chiave segreta nuova di Supabase) | Solo server, mai nel browser. |
| `DATABASE_URL` | Connessione Postgres per Better Auth (attraverso il pooler di Supabase, modalità transazione, adatta alle funzioni di Vercel). |
| `BETTER_AUTH_SECRET` | Già previsto; online diventa obbligatorio. |
| chiave dei collegamenti | Al posto di `.chiave-collegamenti`. |
| `RESEND_API_KEY` | Invio delle email di conferma e di fine prova (account Resend di Lostar). Solo server. |
| `EMAIL_MITTENTE` | Es. `Lostar Technology <noreply@lostartechnology.com>`. |

Da togliere su Vercel a lavoro finito: `DATI_DIR`, `DEMO_UTENTI`, `DEMO_PUBBLICA`.

## Limiti del piano gratuito

- Il progetto si mette in pausa dopo 7 giorni senza richieste; con la landing aperta e i clienti in prova le richieste ci sono. Spazio: 500 MB di database e 1 GB di file, niente backup giornalieri.
- Per le prime decine di aziende in prova basta. Si passa a Pro (backup, niente pausa) quando entrano i primi clienti paganti o quando lo spazio supera metà del limite (scelta mia). Nella Piattaforma una riga mostra lo spazio usato.
- Le aziende con la prova finita e mai pagata **si tengono** (sono contatti, e se tornano ritrovano i dati). Una pulizia automatica è rimandata (scelta mia).

## Lasciato a chi costruisce

- Nomi dei file, delle tabelle e del bucket; forma esatta del passaggio unico.
- Libreria per Postgres (`pg` con il pool, o quella consigliata da Better Auth per Postgres) e client di Supabase per lo spazio file.
- Come si provano le due realizzazioni: gli stessi test sul passaggio unico per disco e Supabase; Supabase in locale con la CLI o su un ramo del progetto.
- Come si portano i dati di oggi: non serve (online oggi non c'è niente da salvare).

## Scelte mie (da controllare)

- Telefono facoltativo nella registrazione.
- BotID di Vercel sulla registrazione.
- Codici invito tenuti nel codice ma non richiesti.
- Moduli "usati nella prova" già spuntati nel riquadro di pagamento.
- Fascia del conto alla rovescia più evidente negli ultimi 3 giorni.
- Pagando durante la prova la prova finisce subito.
- Orologio dell'app (non di Stripe) per far scorrere la prova.
- Due progetti Supabase, produzione e prove.
- `/demo` tenuto per le prove in locale, spento online.
- Passaggio a Pro con i primi clienti paganti o a metà spazio; aziende in prova scadute tenute.

## Decisioni di Alessandro del 25/11/2026 (risposte alle domande aperte)

### Stripe: chiavi di prova

Per ora solo chiavi di prova ("soldi falsi"): le prove le fa Alessandro. Chi finisce la prova può "pagare" con la carta 4242: va bene in questa fase. Il passaggio alle chiavi vere è un lavoro a parte, prima di aprire la registrazione al pubblico per davvero.

### Email di conferma, a nome di Lostar Technology

- Alla registrazione parte un'email con un link: finché il titolare non lo apre, l'azienda è creata ma **la prova non parte** e non si entra (scelta mia sul dettaglio: il link vale 48 ore e si può richiedere di nuovo dalla pagina di accesso).
- I 15 giorni partono **dalla conferma**, non dal modulo compilato (scelta mia).
- Un'email già confermata non può registrare una seconda prova.
- **Mittente: Lostar Technology**, da un indirizzo del dominio `lostartechnology.com` (es. `Lostar Technology <noreply@lostartechnology.com>`), con risposta a un recapito Lostar. Invio con **Resend**, già usato dal sito Lostar. Se il dominio non è ancora verificato su Resend per l'invio, vanno aggiunti i record DNS che Resend indica (lo si controlla nel piano).
- **Nessun riferimento a Supabase**, né nelle email né nelle pagine: le email le manda il gestionale (Better Auth, non il sistema email di Supabase), le foto e i PDF passano dagli indirizzi del gestionale, mai da link `supabase.co`.
- Ogni email ha in fondo i dati di legge del mittente: LOSTAR S.R.L.S., Corso Massimo d'Azeglio 60, 10126 Torino (TO), P. IVA e C.F. 13018890015, REA TO-1333294, il motivo per cui arriva ("ti sei registrato a Piazzale") e il link all'informativa privacy. Versione testo semplice oltre all'HTML.
- Le email di servizio legate alla prova (conferma, "la prova scade fra 3 giorni", "la prova è finita") sono comunicazioni di servizio del contratto, non marketing (scelta mia: "fra 3 giorni" e "finita" sono comprese).

### Registrazioni: si guardano su Supabase

Niente pagina nuova nella Piattaforma. Nel database c'è una **vista `registrazioni`** leggibile dal pannello di Supabase (Table Editor): azienda, titolare, email, telefono, data di registrazione e di conferma, fine prova, giorni rimasti, stato dell'abbonamento, moduli pagati, consenso commerciale sì/no. Più avanti ci sarà una web app aziendale per gli abbonamenti (fuori da questo lavoro).

### Privacy e documenti a norma, sotto Lostar Technology

Titolare e fornitore del servizio: **LOSTAR S.R.L.S.** (dati come sopra; per i diritti privacy la PEC indicata sul sito Lostar, `gustipreziosisrls@pec.cgn.it`). Documenti nuovi, pubblici, linkati da registrazione, landing, piede del gestionale ed email:

- **Informativa privacy di Piazzale** (`/privacy`, artt. 13-14 GDPR), sul modello di quella del sito Lostar: dati del titolare e dei dipendenti che accedono, finalità e basi giuridiche (contratto e misure precontrattuali per account, prova e abbonamento; obbligo legale per fatture; legittimo interesse per sicurezza e prevenzione abusi; **consenso** per i contatti commerciali), tempi di conservazione, fornitori che trattano i dati come responsabili (Vercel, Supabase, Stripe, Resend; eBay solo se l'azienda collega il suo account), trasferimenti fuori UE con le garanzie degli artt. 44 e seguenti, diritti e reclamo al Garante.
- **Condizioni del servizio** (`/condizioni`): contratto tra imprese (il servizio è per autodemolizioni, non per consumatori), prova gratuita di 15 giorni senza carta e cosa succede alla fine (blocco, dati conservati), abbonamento a moduli mensile o annuale, rinnovo e disdetta, commissione dell'8% sulle vendite online, responsabilità, legge italiana e foro di Torino.
- **Accordo sul trattamento dei dati per conto del cliente** (art. 28 GDPR), allegato alle condizioni: per i dati che l'autodemolizione inserisce nel gestionale (clienti, proprietari dei veicoli, dipendenti) Lostar è **responsabile del trattamento** e l'autodemolizione è titolare. Elenco dei sub-responsabili come sopra.
- **Cookie:** il gestionale usa solo cookie tecnici (sessione, dispositivo): niente banner, una sezione nell'informativa. BotID è descritto come nell'informativa del sito Lostar.
- **Nel modulo di registrazione:** casella obbligatoria "Accetto le condizioni del servizio e l'accordo sul trattamento dei dati" (con link), frase "Ho letto l'informativa privacy" (link, nessuna casella), casella **facoltativa e non spuntata** "Acconsento a essere contattato da Lostar Technology per proposte commerciali su Piazzale". Si salvano data, ora, indirizzo IP e **versione** dei testi accettati.
- I testi li scrivo io come bozza a norma; **vanno fatti rileggere a un consulente** prima di aprire la registrazione al pubblico (si segnala nel piano, non blocca la costruzione).

### Foto: online solo quelle dei ricambi in vendita (deciso da Alessandro il 25/11/2026)

Alessandro: le foto restano sul dispositivo che le scatta, con un backup su un supporto fisico in autodemolizione; online vanno solo quelle dei ricambi in vendita, che servono all'annuncio eBay e al negozio, e si tengono finché il pezzo non è venduto.

Come funziona (scelte mie, da controllare):

- **Sul dispositivo.** La foto si scatta e si rimpicciolisce come oggi (1000 px, JPEG 0,72, circa 200 KB) e si salva nella memoria del browser (IndexedDB, con richiesta di memoria persistente). Nell'archivio il ricambio tiene un riferimento `locale:<id>@<dispositivo>`, non l'immagine.
- **Sugli altri dispositivi** una foto locale di un altro telefono si vede come segnaposto "Foto sul telefono di Marco".
- **Quando un ricambio va in vendita** (entra nel catalogo pubblico del negozio oppure ha un annuncio eBay), il dispositivo che ha le sue foto le carica online alla prima occasione, e il riferimento diventa `/api/foto/<nome>`. Se quel telefono è spento, la pubblicazione su eBay aspetta e lo dice: "Foto in arrivo dal telefono di Marco".
- **Venduto:** la copia online si toglie quando il pezzo è venduto e sono passati i 30 giorni del reso (o è stato reso e rimesso in vendita: allora resta). L'originale resta sul telefono.
- **Backup:** in Impostazioni → "Backup foto" si scaricano in un file ZIP tutte le foto di quel dispositivo, da copiare su un disco o una chiavetta in autodemolizione. Un avviso ogni 7 giorni ricorda di farlo (scelta mia).
- **Altre foto** (veicolo all'ingresso, documenti, copia del formulario): restano solo sul dispositivo e nel backup.
- **Rischio da dire chiaro:** se un telefono si rompe o si cancellano i dati del browser prima del backup, le sue foto non in vendita si perdono.

Si costruisce in un piano a parte (`2026-11-25-foto-sul-dispositivo.md`), dopo il piano dei dati su Supabase: il piano dei dati porta comunque foto, allegati e visure sul deposito, perché le copie online e i PDF servono lo stesso.
