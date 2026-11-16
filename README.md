# Gestionale autodemolizione · prototipo (Fase 1)

Prototipo validabile della piattaforma descritta in *Specifiche funzionali v0.1* (16/11/2026).
Serve per la validazione sul posto con il cliente: **veicolo → ricambi suggeriti → foto → scheda → etichetta QR → magazzino → pubblicazione → vendita**.

> Tutti i dati sono dimostrativi (targhe, telai, pratiche, prezzi). Il nome dell'azienda è un segnaposto in `src/lib/config.ts`.

## Avvio

```bash
npm install
npm run dev
```

Apri http://localhost:3000. Il ruolo si cambia dalla barra laterale (desktop) o dalla testata (smartphone). «Ripristina dati demo» riporta i dati iniziali.

Il menu è diviso in aree (Oggi, Veicoli, Ricambi, Vendite, Ufficio): le sottosezioni compaiono solo dentro l'area aperta, e ogni ruolo vede solo le aree e le sezioni che gli servono. Su smartphone la barra in basso mostra le 4 voci del ruolo. La roadmap del prodotto è in [docs/ROADMAP.md](docs/ROADMAP.md).

## Cosa c'è

| Area | Percorso | Note |
|---|---|---|
| Oggi | `/` | Coda «Da fare» del ruolo, generata dai dati e ordinata per scadenza (in ritardo, entro oggi, questa settimana, più avanti); numeri del ruolo, veicoli in lavorazione. Termini dimostrativi in `src/lib/agenda.ts` |
| Accettazione | `/veicoli/nuovo` | Foto targa con OCR (simulato) e caratteri incerti, controllo duplicati targa/VIN, banca dati veicoli (simulata, con guasto simulabile → «da verificare»), pratica separata dall'ID interno |
| Scheda veicolo | `/veicoli/[id]` | Pratica, verifica, ricambi originati, analisi recupero vs scorte |
| Smontaggio (mobile) | `/campo` | Veicolo attivo, lista «da recuperare» confrontata con scorte e soglie, cataloga pezzo con foto, suggerimento IA (simulato) da confermare, etichetta generata al salvataggio |
| Etichetta | `/etichetta/[id]` | Formato 100×50 mm, QR + Code128 con il solo ID; ristampa tracciata con lo stesso ID |
| QR | `/r/[id]` | Indirizzo contenuto nel QR: apre la scheda corretta |
| Scansione | `/scansione` | Fotocamera (BarcodeDetector, Chrome Android) o codice digitato |
| Ricambi | `/ricambi`, `/ricambi/[id]` | Ricerca anche per vecchio codice (K000…), codice OE e costruttore; ubicazione, spostamenti, percorso del pezzo, catalogo e compatibilità, controlli di pubblicazione, invendibile/scarto, storico |
| Ubicazioni | `/magazzino` | Mappa Magazzino → Corsia → Scaffale → Ripiano → Contenitore (formato `3/T03-104-B-1`), riempimento scaffali, trova pezzo, «prima posizione libera» per categoria |
| Pubblicazione | `/pubblicazione` | Approvazione bozze; pubblica solo schede complete e con provenienza verificata |
| Vendite | `/vendite` | Banco (prenota / incassa), ordini con pagamento riuscito/fallito, annullo, spedizione, reso; prova di doppia vendita simultanea |
| Regole scorte | `/regole` | Soglie min/max per tipologia |
| Registro | `/registro` | Audit di ogni operazione con utente, dispositivo, data/ora |
| Negozio online | `/negozio` | Ricerca per veicolo/pezzo, scheda prodotto, carrello, checkout con provider di pagamento simulato |

## Cosa è simulato (da definire in analisi)

OCR targhe, banca dati veicoli/VIN, IA riconoscimento componente, catalogo ricambi (costruttore, codice OE, intercambiabilità: `src/lib/partsdb.ts`; la compatibilità viene dichiarata solo se l'operatore conferma che il codice sul pezzo coincide), stampante etichette, provider di pagamento, corrieri, marketplace, documenti fiscali. I dati vivono nel browser (localStorage): in Fase 2 lo store (`src/lib/store.ts`) si sostituisce con API e database, e la riserva atomica diventa una transazione lato server.

## Stack

Next.js (App Router) · TypeScript · Tailwind CSS · Zustand · qrcode · JsBarcode · lucide-react.
Render 3D dei ricambi generati proceduralmente con Blender (`assets-src/blender/`).
