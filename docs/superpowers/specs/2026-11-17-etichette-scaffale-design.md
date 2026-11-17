# Etichette scaffale e carico/scarico a scansione

## Perché
Gli operatori devono poter etichettare tutto il magazzino subito e registrare dove mettono o prendono un pezzo
senza scrivere: scansione del pezzo e dello scaffale. All'inizio continueranno a lavorare anche a mano,
quindi la via manuale resta sempre disponibile e usa la stessa logica.

## Cosa si costruisce
- **Etichetta per ripiano** (`1/T01-103-B`) e, dove il magazzino ha contenitori, per contenitore (`1/T01-103-B-2`).
  QR = indirizzo `/u/<codice>`: con la fotocamera normale apre la mappa su quello scaffale.
- **Stampa etichette** (`/etichette-scaffale`): dalla mappa per uno scaffale o per tutto il magazzino; per i
  magazzini a struttura libera un piccolo generatore (corsia, scaffale, ripiani, contenitori) per etichettare
  scaffali ancora vuoti.
- **Scansiona** riconosce pezzo o scaffale; l'ordine decide l'azione:
  - pezzo → scaffale = **carico** (posizione registrata; "spostato" se stava altrove; bloccato per pezzi venduti/scartati);
  - scaffale → pezzo = **scarico** (il pezzo esce dallo scaffale; avviso se registrato su un altro scaffale).
  - Risultato grande con **Annulla**; nessuna conferma; si continua a scansionare.
  - Scarico di un pezzo in un ordine aperto: "prelevato per O-…". Senza vendita: pulsante "Vendi al banco"
    (carrello già pronto); se resta invenduto compare in Da fare come "senza posizione".
- **Manuale**: nello stesso campo si scrivono codici pezzo (`2389`, `R-002389`, codice vecchio) e scaffale
  (`1/T01-103-B`). Sulla scheda ricambio restano "Sposta" e si aggiunge "Preleva dallo scaffale".
- Consegna/spedizione di un ordine toglie la posizione ai pezzi ancora registrati a scaffale.

## Approcci considerati
- Azione dedotta dall'ordine delle scansioni (scelto: è come l'ha descritta il cliente, zero tocchi in più).
- Modalità esplicita "Carico/Scarico" prima di scansionare: più sicura ma un tocco in più a ogni pezzo.
- Scarico che apre subito il banco: scartato in favore di un pulsante, perché chi preleva spesso non è chi vende
  e la scansione a catena si interromperebbe.

## Lasciato a chi costruisce
Formato di stampa (foglio A4 a griglia, etichette 70×37 mm), testi, stile coerente con l'etichetta ricambio.
