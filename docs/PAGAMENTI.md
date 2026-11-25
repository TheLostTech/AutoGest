# Pagamenti, registrazione e abbonamento

Come si registra una nuova autodemolizione, come paga l'abbonamento (Stripe) e come si prova tutto senza soldi veri.

## Come funziona in breve

- **Registrazione con codice invito.** Il super admin crea i codici in Piattaforma, Inviti; chi li riceve apre `/registrati` e crea la propria azienda (`src/app/registrati`, `src/app/api/registrazione`). Il registrante diventa `responsabile` (il titolare) dell'azienda.
- **Dipendenti.** Il titolare crea gli accessi della sua gente da Impostazioni, Persone (nome, ruoli, email e password oppure solo PIN). Vedi `docs/ACCESSO.md`.
- **Stato dell'abbonamento.** Ogni azienda ha il suo: su disco in `DATI_DIR/aziende/<id>/abbonamento.json`, con Supabase nella tabella `documento` (tipo `abbonamento`, vedi `docs/SUPABASE.md`) (`src/lib/abbonamento*.ts`). Stati: nuovo, attivo, in ritardo, disdetto, scaduto. Il server decide, mai il browser.
- **Prova fino al primo veicolo.** Un'azienda nuova lavora finché non carica il primo veicolo; poi compare il riquadro di pagamento (`src/components/RiquadroPagamento.tsx`) e, senza abbonamento, il gestionale si blocca. Un abbonamento scaduto blocca sempre. I dati restano visibili.
- **Negozio online chiuso durante il blocco.** Il negozio di un'azienda registrata e bloccata risponde "chiuso". Le altre aziende non cambiano.
- **Checkout.** `src/app/api/abbonamento/checkout` apre il pagamento su Stripe. Si sceglie mese o anno per tutti i moduli insieme (Stripe non mescola i due periodi nello stesso abbonamento).
- **Pagina Abbonamento.** Conto alla rovescia, aggiunta o rimozione di moduli (`/api/abbonamento/moduli`), portale clienti di Stripe (`/api/abbonamento/portale`) per carta, fatture, dati di fatturazione e disdetta a fine periodo. Il cambio da mensile ad annuale non c'è: si disdice e, alla scadenza, si fa un nuovo abbonamento.
- **Fascia in cima al gestionale** (solo per il titolare): pagamento non riuscito, sempre; disdetta, negli ultimi 7 giorni.
- **Disdetta.** Vale sia quella a fine periodo (`cancel_at_period_end`) sia quella a una data (`cancel_at`): lo stato è disdetto e la fine è la prima delle due date. "Riattiva" le toglie tutte e due.
- **Con il PIN si guarda, non si paga.** Checkout, aggiunta e rimozione di moduli, portale e orologio di prova chiedono una sessione con email e password (stessa regola delle Persone): da un dispositivo condiviso con il PIN rispondono 403 e le schermate mostrano "Serve l'accesso con email e password." al posto dei pulsanti.
- **Riquadro di pagamento sempre aggiornato.** Mentre è aperto per il titolare rilegge lo stato da Stripe all'apertura e ogni 10 secondi (il server ne fa al massimo una ogni 15), dopo un 409 del Checkout e quando la sincronizzazione riceve un 402: un pagamento finito in un'altra scheda lo chiude da solo.

## Variabili d'ambiente

| Variabile | A cosa serve |
|---|---|
| `STRIPE_SECRET_KEY` | Chiave segreta di Stripe. `sk_test_…` o `rk_test_…`: modalità **prova** (sandbox AutoLost demo). `sk_live_…` o `rk_live_…`: vale solo con `STRIPE_LIVE=1`, altrimenti Stripe resta **spento**. Se manca, Stripe è spento: nessun pagamento. Mai nel codice, mai in un file versionato. |
| `STRIPE_WEBHOOK_SECRET` | Segreto di firma degli avvisi (`whsec_…`): quello dell'endpoint in dashboard, oppure quello stampato da `stripe listen` in locale. Senza, il webhook risponde 503. |
| `STRIPE_LIVE` | `1` solo quando si andrà con chiavi vere. Con qualunque altro valore una chiave live viene ignorata. |
| `INDIRIZZO_GESTIONALE` | Facoltativo. Indirizzo di riserva per i ritorni da Stripe (Checkout, portale) quando la richiesta non porta `Origin`. Di solito Stripe riporta il titolare all'indirizzo da cui sta usando il gestionale (tunnel, rete locale), dove ha il cookie della sessione. |

In Piattaforma una riga dice in che modalità è Stripe: "Stripe: prova (AutoLost demo)", "Stripe: live" o "Stripe: spento".

Si impostano nell'ambiente del server (per esempio in `.env.local`, che non si versiona). Nel progetto non c'è un `.env.example`.

## Preparare la sandbox

Account Stripe: sandbox **AutoLost demo** (`acct_1UeZEhPHwF2v5yEU`), sotto Lostar srls. Prezzi e prodotti ci sono già:

- i prezzi si trovano per lookup key: `magazzino_mese`, `magazzino_anno`, `pratiche_…`, `ambiente_…`, `banco_…`;
- ogni prodotto ha `metadata.modulo` con l'id del modulo dell'app (`magazzino`, `accettazione`, `ambiente`, `vendite`);
- l'aliquota "IVA 22%" la crea da sola l'app (`aliquotaIva()`), non serve farla a mano;
- ogni prezzo deve andare con `src/lib/listino.ts`: stesso importo in centesimi, `eur`, periodo `month` o `year`, IVA esclusa (`tax_behavior: exclusive`). Se no il server scrive nel log quale prezzo non va e Checkout e moduli rispondono 502 "Prezzi di Stripe diversi dal listino: avvisa l'assistenza" (nessun addebito diverso da quello mostrato).

Passi da fare una volta, nella dashboard:

- [ ] Controlla che l'indirizzo contenga `/test/` e che l'account sia la sandbox. **Un link senza `/test/` porta all'account vero (live).**
- [ ] Leggi l'avviso "Varie funzionalità sospese" prima di provare Checkout: se lo blocca, fermati e chiedi ad Alessandro.
- [ ] Billing, Revenue recovery, Retries: 14 giorni, poi "Cancel the subscription".
- [ ] Portale clienti: attivi metodo di pagamento, fatture, dati di fatturazione e disdetta a fine periodo. Il cambio di prodotto resta spento.
- [ ] Copia la chiave `sk_test_…` in `STRIPE_SECRET_KEY` (mai nel codice).

## Avvisi (webhook) in locale

Il tunnel rapido (`scripts/presentazione.sh`, trycloudflare.com) cambia indirizzo a ogni avvio: non esiste un endpoint fisso da registrare in dashboard. In locale si usa Stripe CLI:

1. `stripe login` (lo fa Alessandro; la sessione scade).
2. `stripe listen --forward-to localhost:<porta>/api/stripe/webhook`, con la porta del `next dev` che si sta provando.
3. Il comando stampa un segreto `whsec_…`: va in `STRIPE_WEBHOOK_SECRET`, poi si riavvia il server.

Gli avvisi che l'app ascolta (`src/lib/stripe/chiavi.ts`):

- `checkout.session.completed`
- `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`
- `invoice.paid`, `invoice.payment_failed`
- `test_helpers.test_clock.ready` (fine di un avanzamento dell'orologio di prova)

Gli altri ricevono 200 e non fanno nulla. Un avviso con firma sbagliata riceve 400. Un avviso di un altro ambiente (`livemode` vero con le chiavi di prova, o falso con quelle vere) finisce nel log e riceve 200.

**Senza avvisi l'app funziona lo stesso:** si rilegge da Stripe da sola (quando la pagina lo chiede, dopo ogni cambio di moduli o di orologio, e per il titolare quando l'ultimo aggiornamento ha più di un'ora; le richieste del browser non vanno a Stripe più di una volta ogni 15 secondi per azienda). Gli avvisi servono a essere più rapidi.

## Carte di prova

Solo con le chiavi di prova compaiono nel riquadro di pagamento e su Abbonamento (`src/lib/carte-prova.ts`). Scadenza futura e CVC qualunque.

| Carta | Cosa prova |
|---|---|
| `4242 4242 4242 4242` | Pagamento riuscito. |
| `4000 0027 6000 3184` | Chiede il codice della banca (3D Secure). |
| `4000 0000 0000 0341` | La carta si salva, ma l'addebito fallisce al rinnovo: serve a provare "pagamento non riuscito" e la fascia in ritardo. Si risolve cambiando carta dal portale. |

## Orologio di prova

Con le chiavi di prova ogni cliente Stripe nasce dentro un orologio di prova (test clock) tutto suo. Su Abbonamento c'è il riquadro "Strumenti di prova" (`src/components/StrumentiProva.tsx`) con la data di prova e i pulsanti:

| Pulsante | Cosa fa |
|---|---|
| +1 giorno, +1 settimana | Avanza di 24 ore o di 7 giorni. |
| +1 mese | Avanza di un mese di calendario (a Roma, alla stessa ora). Fa partire rinnovo e nuova fattura. |
| +1 anno | Solo con l'abbonamento annuale. |

- Ogni pulsante chiama `POST /api/abbonamento/prova/avanza`; Stripe genera fatture e addebiti come se il tempo fosse passato, e la pagina aspetta che l'orologio sia "pronto" (al massimo un minuto) prima di sincronizzare.
- **Limite di Stripe:** l'orologio avanza al massimo di due periodi dell'abbonamento per volta. Per questo "+1 anno" è permesso solo con l'annuale.
- L'orologio va solo avanti: per ricominciare si registra un'altra azienda.
- Con una chiave live il riquadro non c'è e la route risponde 404. Solo il titolare (o l'assistenza) può usarla.

## Limiti noti

- **Nessun endpoint fisso.** Il server gira sul Mac e il tunnel rapido cambia indirizzo: finché non c'è un indirizzo stabile gli avvisi arrivano solo da `stripe listen`; il resto lo fa la sincronizzazione dell'app.
- **Fattura elettronica fuori da Stripe.** Le fatture di Stripe non sono fatture elettroniche per lo SDI: le emette Lostar con il suo strumento. L'IVA (prezzi esclusi, aliquota 22%) è da confermare con il commercialista prima di andare live.
- **Un solo processo Node.** Le code e i blocchi (un Checkout per volta, un cambio di moduli per volta, i 15 secondi tra sincronizzazioni) stanno in memoria: valgono per un solo processo e si azzerano al riavvio. Con più processi o più server non bastano.
- **Cliente cancellato su Stripe.** Se il cliente, l'abbonamento o l'orologio di prova non esistono più (cancellati dalla dashboard), la sincronizzazione non sbaglia a ogni giro: l'azienda resta senza abbonamenti (scaduta se aveva pagato, altrimenti nuova) e il prossimo Checkout crea un cliente nuovo.
- **Aziende di prova e chiavi vere.** Le aziende create con le chiavi di prova non si sincronizzano con le chiavi live (i loro id non esistono lì): se mai pagate si riparte da zero, se già pagate l'app rifiuta e serve l'assistenza. Le aziende di prova e i loro clienti Stripe non si eliminano (rimandato).
- **Rimandato:** email (conferma indirizzo, recupero password, inviti, ricevute nostre); periodo di prova gratuito a tempo, codici sconto, prezzo "Completo"; registrazione aperta senza codice invito (serve una protezione dai robot); chiavi live e endpoint definitivo.

## Prova completa

Su una porta nuova e un `DATI_DIR` nuovo, con `stripe listen` acceso se c'è `stripe login`. Da compilare quando la prova è fatta.

| # | Passo | Esito |
|---|---|---|
| 1 | Invito creato in Piattaforma, Inviti | |
| 2 | Registrazione con il codice | |
| 3 | Primo veicolo caricato | |
| 4 | Compare il riquadro di pagamento | |
| 5 | Checkout mensile con 4242 | |
| 6 | Moduli accesi dopo il pagamento | |
| 7 | Aggiunta di un modulo | |
| 8 | +1 mese: rinnovo e fattura nuova | |
| 9 | Disdetta dal portale e fascia a 7 giorni dalla fine | |
| 10 | Avanzamento fino alla fine: blocco e dati visibili | |

Cosa non è stato provato: da scrivere qui dopo la prova.
