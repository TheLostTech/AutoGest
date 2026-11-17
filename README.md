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

Il menu è diviso in aree (Oggi, Veicoli, Ricambi, Vendite, Ambiente, Ufficio): le sottosezioni compaiono solo dentro l'area aperta, e ogni ruolo vede solo le aree e le sezioni che gli servono. Su smartphone la barra in basso mostra le 4 voci del ruolo. La roadmap del prodotto è in [docs/ROADMAP.md](docs/ROADMAP.md).

## Cosa c'è

| Area | Percorso | Note |
|---|---|---|
| Oggi | `/` | Coda «Da fare» del ruolo, generata dai dati e ordinata per scadenza (in ritardo, entro oggi, questa settimana, più avanti); numeri del ruolo, veicoli in lavorazione. Termini dimostrativi in `src/lib/agenda.ts` |
| Accettazione | `/veicoli/nuovo` | Foto targa con OCR (simulato) e caratteri incerti, controllo duplicati targa/VIN, banca dati veicoli (simulata, con guasto simulabile → «da verificare»), pratica separata dall'ID interno |
| Scheda veicolo | `/veicoli/[id]` | Pratica in 4 passi (conferente e documenti, visura PRA con fermo amministrativo, presa in carico e certificato, radiazione), bonifica, ricambi originati, analisi recupero vs scorte |
| Bonifica | `/veicoli/[id]/bonifica` | Modello di bonifica da telefono con quantità tipiche precompilate; genera da sola i movimenti del registro rifiuti |
| Certificato | `/certificato/[id]` | Fac-simile stampabile del certificato di rottamazione |
| Smontaggio (mobile) | `/campo` | Veicolo attivo, lista «da recuperare» confrontata con scorte e soglie, cataloga pezzo con foto, suggerimento IA (simulato) da confermare, etichetta generata al salvataggio |
| Etichetta | `/etichetta/[id]` | Formato 100×50 mm, QR + Code128 con il solo ID; ristampa tracciata con lo stesso ID |
| Etichette scaffale | `/etichette-scaffale` | Una per ripiano (e contenitore), QR + Code128; il QR apre la mappa su quel ripiano (`/u/…`) |
| QR | `/r/[id]` | Indirizzo contenuto nel QR: apre la scheda corretta |
| Scansione | `/scansione` | Pezzo → scaffale = carico, scaffale → pezzo = prelievo. Fotocamera (lettore del browser o ZXing incluso, quindi anche iPhone; serve https), pistola laser o codice digitato |
| Ricambi | `/ricambi`, `/ricambi/[id]` | Ricerca anche per vecchio codice (K000…), codice OE e costruttore; ubicazione, spostamenti, percorso del pezzo, catalogo e compatibilità, controlli di pubblicazione, invendibile/scarto, storico |
| Inventario | `/inventario`, `/inventario/[mag]`, `/inventario/[mag]/nuovo` | Crea magazzino (solo numero e nome) e aprilo; elenco dei ricambi raggruppati per ubicazione; «Aggiungi ricambio» per i pezzi già presenti: tipo (con foto e riconoscimento simulato), marca e modello, codice vecchio, dicitura, condizioni, ubicazione scritta (corsia, scaffale, ripiano, contenitore), pratica passata dal vecchio archivio; ubicazione, modello e pratica restano per il pezzo successivo. «Verifica» di un ripiano (`/inventario/conta`) per l'appello dei pezzi registrati |
| Ubicazioni | `/magazzino` | Mappa Magazzino → Corsia → Scaffale → Ripiano → Contenitore (formato `3/T03-104-B-1`), riempimento scaffali, trova pezzo, «prima posizione libera» per categoria |
| Pubblicazione | `/pubblicazione` | Approvazione bozze; pubblica solo schede complete e con provenienza verificata |
| Vendite | `/vendite` | Banco con listino, scontrino o fattura, preventivo senza riserva; scheda dettaglio del ricambio; ordini con pagamento riuscito/fallito, annullo, spedizione, reso (con nota di credito); prova di doppia vendita simultanea |
| Documenti | `/vendite/documenti`, `/documento/[id]` | Preventivi, scontrini, fatture, note di credito; preventivo → vendita con un tocco; stampa A4 o scontrino 80 mm |
| Registro rifiuti | `/ambiente` | Giacenze per codice EER rispetto ai limiti dell'autorizzazione, movimenti di carico e scarico generati dagli eventi, trasmissione al RENTRI |
| Formulari | `/ambiente/formulari` | Formulari di uscita: creazione, firma (scarico automatico), trasmissione, accettazione del destinatario |
| Listini | `/listini` | Fasce di prezzo per tipo di cliente (rinominabili come L/T/B/2/3/4), quote del prezzo suggerito dell'usato |
| Ricerca | ⌘K o Ctrl+K, icona lente | Targa, telaio, ID, codice OE, vecchio codice, cliente, ordine, formulario, documento |
| Regole scorte | `/regole` | Soglie min/max per tipologia |
| Registro | `/registro` | Audit di ogni operazione con utente, dispositivo, data/ora |
| Negozio online | `/negozio` | Ricerca per veicolo/pezzo, scheda prodotto, carrello, checkout con provider di pagamento simulato |

## Cosa è simulato (da definire in analisi)

OCR targhe, banca dati veicoli/VIN, visura PRA, radiazione, RENTRI e formulari digitali, registratore telematico e invio allo SdI, IA riconoscimento componente, catalogo ricambi (costruttore, codice OE, prezzo del nuovo, intercambiabilità: `src/lib/partsdb.ts`; la compatibilità viene dichiarata solo se l'operatore conferma che il codice sul pezzo coincide), stampante etichette, provider di pagamento, corrieri, marketplace, documenti fiscali. I dati condivisi stanno in un file sul server (`/api/demo-state`) con una copia di lavoro nel browser: in Fase 2 lo store (`src/lib/store.ts`) si sostituisce con API e database, e la riserva atomica diventa una transazione lato server.

## Sul server dell'azienda

Il gestionale gira su un computer dell'azienda (anche Windows Server) o nel cloud; telefoni e computer lo aprono dal browser.

- **Dati e foto** stanno nella cartella indicata da `DATI_DIR` (di serie `.demo-data/` nel progetto): `state.json` è l'archivio, `foto/` le foto. Il backup è la copia di quella cartella. Nel telefono resta solo una copia di lavoro senza le foto.
- **Indirizzo nei QR**: `INDIRIZZO_GESTIONALE` (es. `https://gestionale.azienda.it`). Se manca, i QR stampati dal server aperto come `localhost` usano l'indirizzo di rete del server (es. `http://192.168.1.58:3211`), che funziona solo dal Wi-Fi aziendale. Le etichette già stampate contengono l'indirizzo di quel momento: va fissato prima di etichettare il magazzino. Dentro *Scansiona* conta solo il codice, quindi lì funzionano comunque.
- **https**: i telefoni aprono la fotocamera nel browser solo da un indirizzo `https`. Strade possibili: un nome a dominio con certificato (es. Caddy o IIS davanti al gestionale), Cloudflare Tunnel (https senza aprire porte del router, funziona anche su Windows Server), oppure il cloud, dove l'https è già incluso. Senza https resta la pistola laser o il codice scritto a mano.

```bash
DATI_DIR=/percorso/dati INDIRIZZO_GESTIONALE=https://gestionale.azienda.it npm run build && npm start
```

## Stack

Next.js (App Router) · TypeScript · Tailwind CSS · Zustand · qrcode · JsBarcode · barcode-detector (ZXing WebAssembly, servito da `public/zxing/`, copiato a ogni `npm install`) · lucide-react.
Render 3D dei ricambi generati proceduralmente con Blender (`assets-src/blender/`).
