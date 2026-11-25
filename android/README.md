# Piazzale per Android (prove in piazzale)

App Android che apre il gestionale dal Mac. Il gestionale gira sul Mac e i telefoni lo raggiungono con un collegamento https (Cloudflare), anche dalla rete dati.

## Accendere l'ambiente di prova (sul Mac)

```bash
zsh scripts/piazzale-test.sh
```

- Server sulla porta 3215 con i suoi dati in `.dati-test/`, separati da `.demo-data/`.
- **Accesso unico**: l'app entra da sola come «Collaudo», senza credenziali, con tutti e sei i ruoli e tutti i moduli (in alto, «Stai usando come»). Anche «Esci» fa rientrare da solo.
- Alla fine lo script stampa l'indirizzo e il QR. Il Mac resta sveglio finché il collegamento è aperto (non chiudere il coperchio).
- Dopo una modifica al codice: `zsh scripts/piazzale-test.sh aggiorna`. Per spegnere tutto: `zsh scripts/piazzale-test.sh chiudi` (i dati restano).

## Installare l'app

1. Copia `piazzale-test.apk` sul telefono (WhatsApp, Drive, cavo) e aprilo.
2. Android chiede di consentire l'installazione da quella app: consenti.
3. Al primo avvio l'app apre l'indirizzo con cui è stata compilata. Se il collegamento è cambiato, compare la schermata dell'indirizzo: tocca «Inquadra il QR del server» e inquadra il QR stampato dallo script.

L'indirizzo si cambia anche tenendo premuta l'icona → «Cambia server».

## Cosa fa l'app oltre al browser

- fotocamera per Scansiona (chiede il permesso la prima volta);
- foto dai moduli: con «Scatta foto» apre direttamente la fotocamera;
- stampa: «Stampa etichetta» e gli altri pulsanti di stampa aprono la stampa di Android;
- PDF (visure, ricevute): si scaricano e si aprono dalle notifiche;
- tasto Indietro: torna alla pagina prima, e per uscire va premuto due volte.

## Ricompilare l'APK

Servono l'SDK Android (`~/Library/Android/sdk`) e Java 17.

```bash
cd android && ./gradlew assembleDebug -Ppiazzale.indirizzo=https://<indirizzo>.trycloudflare.com && cp app/build/outputs/apk/debug/app-debug.apk piazzale-test.apk
```

È firmata con la chiave di debug di questo Mac: un'APK nuova compilata qui si installa sopra quella vecchia. Se è compilata su un altro computer, bisogna prima disinstallare la vecchia.

## Limiti noti

- L'indirizzo `trycloudflare.com` cambia quando il collegamento si riapre (Mac spento o in stop). Le etichette QR stampate prima contengono il vecchio indirizzo, ma dentro Scansiona conta solo il codice e funzionano comunque.
- Il lettore QR della schermata dell'indirizzo usa Google Play Services. Su telefoni senza Google l'indirizzo va scritto a mano.
