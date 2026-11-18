// Normative commentate per le pagine pubbliche /news.
// Fatti verificati sulle fonti ufficiali il 18/11/2026 (Normattiva, GUUE, rentri.gov.it, documenti del Consiglio UE).
// Per aggiungere un articolo: un oggetto in ARTICOLI. Sitemap, metadati e dati strutturati si aggiornano da soli.

export type Articolo = {
  slug: string;
  titolo: string;
  /** Titolo per i motori di ricerca, se diverso (max ~60 caratteri) */
  titoloSeo?: string;
  /** Descrizione per i motori di ricerca e per l'elenco (max ~160 caratteri) */
  descrizione: string;
  /** Data di pubblicazione, AAAA-MM-GG */
  data: string;
  aggiornato?: string;
  /** Riferimento breve, mostrato sopra il titolo */
  norma: string;
  riferimenti: string[];
  parole: string[];
  sintesi: string[];
  date: { quando: string; cosa: string }[];
  commento: string[];
  nelGestionale?: string;
  fonti: { nome: string; url: string }[];
};

export const ARTICOLI: Articolo[] = [
  {
    slug: "fir-digitale-rentri-16-settembre-2026",
    titolo: "FIR solo digitale dal 16 settembre 2026: cosa cambia per chi demolisce",
    titoloSeo: "FIR digitale obbligatorio dal 16/09/2026: guida RENTRI",
    descrizione:
      "Il formulario cartaceo è finito il 15 settembre 2026. Scaglioni RENTRI, trasmissione mensile del registro, contributo annuale e sanzioni, spiegati per i centri di raccolta.",
    data: "2026-11-18",
    norma: "RENTRI · DM 59/2023",
    riferimenti: [
      "DM 4 aprile 2023 n. 59, artt. 7, 13, 14, 15",
      "D.L. 31/12/2025 n. 200, art. 13, conv. L. 27/02/2026 n. 26",
      "D.Lgs. 152/2006, art. 258 c. 10-bis",
    ],
    parole: [
      "FIR digitale",
      "RENTRI",
      "formulario rifiuti digitale",
      "registro carico scarico digitale",
      "autodemolizione RENTRI",
      "scadenze RENTRI 2026",
      "contributo RENTRI",
      "xFIR",
    ],
    sintesi: [
      "Il formulario di identificazione dei rifiuti (FIR) digitale è previsto dall'art. 7 del DM 59/2023 e doveva partire il 13 febbraio 2026.",
      "La legge di conversione del decreto di fine anno 2025 ha permesso di usare ancora il cartaceo, in alternativa, fino al 15 settembre 2026. Dal 16 settembre vale solo il digitale.",
      "Dal 15 settembre 2026 si applicano anche le sanzioni per la mancata o incompleta trasmissione dei dati dei formulari (nuovo comma 10-bis dell'art. 258 del D.Lgs. 152/2006).",
      "Il registro cronologico di carico e scarico si trasmette al RENTRI ogni mese, entro la fine del mese successivo a quello dell'annotazione. Se nel mese non ci sono annotazioni, non si trasmette niente.",
      "Il contributo annuale al RENTRI si versa entro il 30 aprile di ogni anno, per ciascuna unità locale.",
      "La messa a disposizione dei dati di percorso dei mezzi (geolocalizzazione) è stata spostata al 13 settembre 2027.",
    ],
    date: [
      { quando: "13/02/2025", cosa: "Chiude la finestra di iscrizione del primo scaglione: produttori oltre 50 dipendenti e gestori di rifiuti, come gli impianti di trattamento." },
      { quando: "13/02/2026", cosa: "Partenza formale del FIR digitale." },
      { quando: "15/09/2026", cosa: "Ultimo giorno del FIR cartaceo. Da qui partono le sanzioni sulla trasmissione dei dati dei formulari." },
      { quando: "16/09/2026", cosa: "Solo FIR digitale." },
      { quando: "30/04 di ogni anno", cosa: "Versamento del contributo annuale RENTRI." },
      { quando: "13/09/2027", cosa: "Dati di percorso dei mezzi (geolocalizzazione)." },
    ],
    commento: [
      "Per un'autodemolizione il RENTRI non è un adempimento in più: è la stessa cosa che fai già con il registro, solo che adesso deve tornare al centesimo di chilo e arrivare in tempo. Il problema vero non è trasmettere, è avere i dati giusti alla fine del mese senza ricostruirli a memoria.",
      "Il passaggio al solo digitale toglie l'alibi del foglio compilato in fretta dal trasportatore. Se lo scarico nel tuo registro non combacia con il formulario che ha emesso chi ritira, il RENTRI lo vede. Conviene controllare ogni formulario quando arriva, non a fine mese.",
      "Sullo scaglione: i centri di raccolta sono impianti di gestione e, a nostra lettura, rientrano nel primo. Se non sei iscritto, parlane subito con il consulente ambientale.",
    ],
    nelGestionale:
      "Le registrazioni nascono dagli eventi: ingresso del veicolo, bonifica, uscita con formulario. La consulente ambientale ha una pagina sola, «Periodo da trasmettere», dove vede il mese, trova evidenziato quello che manca o non torna e lo corregge con rettifiche tracciate. I formulari ricevuti si registrano con la foto della copia e lo scarico si scrive da solo.",
    fonti: [
      { nome: "DM 59/2023 su Normattiva", url: "https://www.normattiva.it/uri-res/N2Ls?urn:nir:ministero.ambiente.e.sicurezza.energetica:decreto:2023-04-04;59" },
      { nome: "D.L. 200/2025, art. 13 su Normattiva", url: "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legge:2025-12-31;200~art13" },
      { nome: "Portale RENTRI", url: "https://www.rentri.gov.it" },
    ],
  },
  {
    slug: "bonifica-veicoli-fuori-uso-10-giorni-dlgs-209-2003",
    titolo: "Messa in sicurezza entro 10 giorni lavorativi: gli obblighi del centro di raccolta",
    titoloSeo: "Bonifica veicoli fuori uso entro 10 giorni: D.Lgs. 209/2003",
    descrizione:
      "Dopo il D.Lgs. 119/2020 la bonifica va fatta entro 10 giorni lavorativi dall'ingresso. Accatastamento, stoccaggio dei ricambi e obiettivi di recupero del 95%.",
    data: "2026-11-18",
    norma: "D.Lgs. 209/2003",
    riferimenti: ["D.Lgs. 24/06/2003 n. 209, artt. 6 e 7, Allegato I", "D.Lgs. 3/09/2020 n. 119"],
    parole: [
      "bonifica veicoli fuori uso",
      "messa in sicurezza veicolo",
      "D.Lgs. 209/2003",
      "10 giorni lavorativi bonifica",
      "centro di raccolta veicoli",
      "obiettivi recupero 95%",
      "stoccaggio ricambi usati",
    ],
    sintesi: [
      "Il veicolo va messo in sicurezza entro dieci giorni lavorativi dall'ingresso nel centro di raccolta, anche se non è ancora stato cancellato dal PRA (art. 6 c. 2).",
      "Nell'area di conferimento non si accatastano veicoli. I veicoli messi in sicurezza ma non ancora trattati si sovrappongono al massimo in tre.",
      "Le carcasse già trattate si possono accatastare fino a 5 metri di altezza.",
      "I ricambi destinati alla vendita vanno stoccati in modo da non deteriorarsi (Allegato I, punto 8).",
      "Il deposito presso concessionari e automercati è ammesso per un massimo di 30 giorni (art. 6 c. 8-bis).",
      "Dal 2015 reimpiego e recupero devono arrivare almeno al 95% del peso medio del veicolo, reimpiego e riciclaggio almeno all'85% (art. 7 c. 2).",
    ],
    date: [
      { quando: "Giorno 0", cosa: "Il veicolo entra nel centro di raccolta." },
      { quando: "Entro 10 giorni lavorativi", cosa: "Messa in sicurezza completata: batterie, liquidi, filtri, componenti pericolosi." },
    ],
    commento: [
      "Dieci giorni lavorativi sembrano tanti finché non entrano sei macchine nella stessa settimana. Il termine si sfora quasi sempre per distrazione, non per mancanza di tempo: la macchina finisce in fondo al piazzale e nessuno la vede.",
      "Il 95% di recupero è un obiettivo nazionale, ma si costruisce pezzo per pezzo. Ogni ricambio che rivendi è peso che non va in frantumazione: smontare con criterio conviene due volte.",
    ],
    nelGestionale:
      "Ogni veicolo in ingresso ha la sua scadenza di bonifica nella coda «Da fare», gialla quando si avvicina e rossa se scaduta. La bonifica si segna dal telefono con le quantità tipiche del modello già scritte, e i carichi nel registro rifiuti si generano da soli con il codice EER giusto.",
    fonti: [{ nome: "D.Lgs. 209/2003 su Normattiva", url: "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:2003-06-24;209" }],
  },
  {
    slug: "regolamento-ue-2026-1738-veicoli-fuori-uso",
    titolo: "Regolamento (UE) 2026/1738: dal 2029 ricambi da smontare ed etichettare prima della frantumazione",
    titoloSeo: "Nuovo regolamento UE veicoli fuori uso 2026/1738",
    descrizione:
      "Il nuovo regolamento europeo sui veicoli fuori uso sostituisce la direttiva 2000/53/CE. Rimozione obbligatoria dei pezzi, etichetta sui ricambi usati, certificato elettronico, export.",
    data: "2026-11-18",
    norma: "Reg. (UE) 2026/1738",
    riferimenti: ["Regolamento (UE) 2026/1738 dell'8 luglio 2026, GU L del 24/07/2026", "Abroga le direttive 2000/53/CE e 2005/64/CE"],
    parole: [
      "regolamento veicoli fuori uso",
      "regolamento UE 2026/1738",
      "ELV regulation",
      "etichetta ricambi usati",
      "passaporto circolarità veicolo",
      "certificato di distruzione elettronico",
      "direttiva 2000/53/CE",
    ],
    sintesi: [
      "Il regolamento è in vigore dal 13 agosto 2026 e si applica in generale dal 1° settembre 2028. Essendo un regolamento, vale direttamente in tutti gli Stati membri.",
      "Gli impianti autorizzati devono rimuovere i pezzi elencati nell'Allegato VIII, parte C, dopo la bonifica e prima della frantumazione. Quelli riutilizzabili vanno smontati senza romperli, salvo costi sproporzionati dimostrati (art. 29).",
      "I pezzi rimossi vanno valutati per riuso, rigenerazione o riciclo ed etichettati. Se sono idonei al riuso non sono rifiuti (art. 30).",
      "Dal 1° settembre 2029 chi vende ricambi usati, anche online, deve garantire che portino l'etichetta dell'impianto di trattamento (art. 31).",
      "Il certificato di distruzione diventa elettronico (art. 25).",
      "Si potranno esportare solo veicoli che non sono fuori uso e sono idonei alla circolazione (art. 39).",
    ],
    date: [
      { quando: "13/08/2026", cosa: "Entrata in vigore." },
      { quando: "01/09/2028", cosa: "Applicazione generale." },
      { quando: "01/09/2029", cosa: "Rimozione obbligatoria dei pezzi prima della frantumazione ed etichetta sui ricambi usati venduti." },
      { quando: "01/09/2031", cosa: "Controlli sull'export di veicoli usati." },
      { quando: "01/09/2032", cosa: "Passaporto digitale di circolarità e 15% di plastica riciclata nei veicoli nuovi." },
      { quando: "01/09/2036", cosa: "25% di plastica riciclata." },
    ],
    commento: [
      "È la notizia più importante degli ultimi vent'anni per il settore. Il ricambio usato smette di essere una zona grigia: diventa un prodotto con un'etichetta, una provenienza e una valutazione. Chi oggi vende pezzi senza sapere da che macchina vengono dovrà cambiare metodo.",
      "Per chi lavora già bene è un vantaggio: la tracciabilità del pezzo diventa un obbligo per tutti, quindi smette di essere un costo solo tuo. Il 2029 sembra lontano, ma etichettare un magazzino di migliaia di pezzi non si fa in un mese.",
    ],
    nelGestionale:
      "Ogni ricambio ha già un codice univoco, un'etichetta con QR e la provenienza ereditata dal veicolo: marca, modello, targa, pratica. I dati specifici richiesti dall'etichetta del regolamento li aggiungeremo appena saranno definiti nel dettaglio.",
    fonti: [
      { nome: "Testo del regolamento (GUUE)", url: "https://publications.europa.eu/resource/celex/32026R1738" },
      { nome: "Commissione europea, veicoli fuori uso", url: "https://environment.ec.europa.eu/topics/waste-and-recycling/end-life-vehicles_en" },
    ],
  },
  {
    slug: "gpsr-ricambi-usati-online",
    titolo: "Ricambi usati online: cosa chiede il regolamento sulla sicurezza dei prodotti",
    titoloSeo: "GPSR e ricambi auto usati: cosa mettere nell'annuncio",
    descrizione:
      "Dal 13 dicembre 2024 il regolamento GPSR vale anche per l'usato venduto da professionisti. Cosa deve mostrare l'annuncio online e quando i pezzi da riparare sono esclusi.",
    data: "2026-11-18",
    norma: "Reg. (UE) 2023/988 · GPSR",
    riferimenti: ["Regolamento (UE) 2023/988 del 10/05/2023, GU L 135 del 23/05/2023", "Art. 2 par. 3, art. 19, art. 52"],
    parole: [
      "GPSR ricambi usati",
      "regolamento sicurezza prodotti",
      "regolamento UE 2023/988",
      "vendere ricambi usati su eBay",
      "annuncio ricambi auto obblighi",
      "responsabile UE fabbricante",
    ],
    sintesi: [
      "Il regolamento si applica dal 13 dicembre 2024 ai prodotti «nuovi, usati, riparati o ricondizionati» (art. 2 par. 3).",
      "Sono esclusi i prodotti da riparare o ricondizionare prima dell'uso, se sono chiaramente indicati come tali (stesso articolo).",
      "Il considerando 16 conferma che vale per i prodotti di seconda mano venduti nell'ambito di un'attività commerciale.",
      "Se un componente ha già regole UE specifiche, per esempio un'omologazione, il GPSR copre solo i rischi che quelle regole non disciplinano (art. 2 par. 1).",
      "Un annuncio online deve mostrare nome, indirizzo postale ed email del fabbricante, l'eventuale responsabile nell'UE, un'immagine, il tipo e l'identificativo del prodotto, le avvertenze di sicurezza (art. 19).",
    ],
    date: [{ quando: "13/12/2024", cosa: "Il regolamento si applica." }],
    commento: [
      "Il GPSR è nato per l'e-commerce generalista, ma i marketplace lo applicano a tutti: un annuncio senza i dati richiesti su eBay può restare invisibile o non acquistabile nell'UE. Per un ricambio usato, a nostra lettura, il fabbricante da indicare resta la casa che l'ha prodotto. Non abbiamo trovato indicazioni ufficiali della Commissione su questo punto: chiedi conferma al tuo consulente.",
      "Il pezzo venduto «per ricambio o rigenerazione» è escluso solo se lo scrivi chiaramente. Meglio una dicitura onesta nell'annuncio che un reclamo dopo.",
    ],
    nelGestionale:
      "Prima della pubblicazione su eBay il gestionale chiede di confermare se il pezzo è stato messo in commercio prima del 13 dicembre 2024 oppure di indicare il produttore, con un indirizzo nell'UE. Senza prezzo, foto e provenienza verificata il pezzo non va online.",
    fonti: [{ nome: "Regolamento (UE) 2023/988 (GUUE, in italiano)", url: "https://publications.europa.eu/resource/celex/32023R0988" }],
  },
  {
    slug: "rvfu-registro-telematico-veicoli-fuori-uso-radiazione",
    titolo: "Registro telematico dei veicoli fuori uso: certificato digitale e radiazione diretta",
    titoloSeo: "RVFU e radiazione per demolizione: cosa fa il centro di raccolta",
    descrizione:
      "Dal 7 giugno 2024 il registro dei veicoli fuori uso è solo telematico e il centro di raccolta radia direttamente. Dal 2026 il fermo amministrativo non blocca più la demolizione.",
    data: "2026-11-18",
    norma: "D.P.R. 177/2022 · RVFU",
    riferimenti: [
      "D.P.R. 23/09/2022 n. 177",
      "D.Lgs. 209/2003, art. 5 commi 8, 8-bis e 10",
      "Circolare MIT n. 15 del 17/02/2025",
      "L. 26/01/2026 n. 14",
      "Lettera circolare ACI n. 9626 del 19/02/2026",
    ],
    parole: [
      "RVFU",
      "registro veicoli fuori uso",
      "radiazione per demolizione",
      "certificato di rottamazione digitale",
      "fermo amministrativo demolizione",
      "cancellazione PRA autodemolitore",
    ],
    sintesi: [
      "Dal 7 giugno 2024 il Registro unico telematico dei veicoli fuori uso (RVFU) è obbligatorio e sostituisce il registro cartaceo.",
      "Il centro di raccolta cancella direttamente il veicolo dal PRA e dall'Archivio nazionale veicoli, per i veicoli iscritti al PRA.",
      "Per ogni veicolo preso in carico va emesso il certificato di rottamazione digitale.",
      "Documenti e targhe vanno restituiti entro 30 giorni dalla consegna del veicolo (art. 5 c. 8 del D.Lgs. 209/2003).",
      "Con la L. 14/2026 il fermo amministrativo non impedisce più la radiazione per demolizione. Chi rottama un veicolo con fermo però non ha diritto agli incentivi per comprarne uno nuovo.",
    ],
    date: [
      { quando: "07/06/2024", cosa: "RVFU obbligatorio." },
      { quando: "17/02/2025", cosa: "Circolare MIT n. 15, che sostituisce le istruzioni operative precedenti." },
      { quando: "05/02/2026", cosa: "Pubblicata la L. 14/2026: il fermo non blocca più la radiazione." },
    ],
    commento: [
      "Il fermo amministrativo era il motivo classico per cui una macchina restava mesi nel piazzale in attesa. Adesso si può demolire: è un cambiamento piccolo sulla carta e grande per lo spazio in cortile.",
      "Resta un rischio pratico: il cliente con il fermo che si aspetta l'incentivo. Meglio dirglielo all'accettazione che al momento del certificato.",
    ],
    nelGestionale:
      "La pratica di ogni veicolo segue quattro passi: conferente e documenti, visura PRA con il fermo amministrativo in evidenza, presa in carico e certificato, radiazione. Il numero del certificato resta separato dal codice interno del veicolo, così non si confondono.",
    fonti: [
      { nome: "D.Lgs. 209/2003, art. 5 su Normattiva", url: "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:2003-06-24;209~art5" },
      { nome: "Portale dell'Automobilista", url: "https://www.ilportaledellautomobilista.it" },
    ],
  },
  {
    slug: "garanzia-legale-ricambi-usati-12-mesi",
    titolo: "Garanzia sui ricambi usati: 24 mesi, riducibili a 12, e l'estensione dopo una riparazione",
    titoloSeo: "Garanzia legale sui ricambi usati: 12 o 24 mesi?",
    descrizione:
      "Il Codice del Consumo dà 24 mesi di garanzia anche sull'usato, ma si possono ridurre a 12 per iscritto. Dal 2026, se il cliente sceglie la riparazione, la garanzia si allunga di 12 mesi.",
    data: "2026-11-18",
    norma: "Codice del Consumo, art. 133",
    riferimenti: ["D.Lgs. 6/09/2005 n. 206, art. 133", "D.Lgs. 170/2021", "D.Lgs. 25/09/2026 n. 176 (diritto alla riparazione)"],
    parole: [
      "garanzia ricambi usati",
      "garanzia legale usato",
      "art. 133 codice del consumo",
      "garanzia 12 mesi usato",
      "diritto alla riparazione",
      "vendita ricambi a privati",
    ],
    sintesi: [
      "Il venditore risponde dei difetti presenti alla consegna che si manifestano entro due anni (art. 133 c. 1).",
      "L'azione del consumatore si prescrive in 26 mesi dalla consegna (c. 3).",
      "Per i beni usati le parti possono ridurre la durata della responsabilità e della prescrizione, ma non sotto un anno (c. 4).",
      "Novità 2026: se il consumatore sceglie la riparazione, la responsabilità del venditore si allunga una volta di 12 mesi (c. 1-bis, per i contratti conclusi dal 31 luglio 2026).",
      "La garanzia legale vale verso i consumatori. Con officine e aziende si applicano le regole del codice civile e quello che concordate.",
    ],
    date: [
      { quando: "01/01/2022", cosa: "Regole attuali della garanzia (D.Lgs. 170/2021)." },
      { quando: "31/07/2026", cosa: "Contratti da cui vale l'estensione di 12 mesi dopo la riparazione." },
    ],
    commento: [
      "La riduzione a 12 mesi non è automatica: va concordata, quindi deve stare scritta sul documento di vendita o nelle condizioni del negozio online, prima dell'acquisto. Un cartello in negozio non basta a dimostrarlo.",
      "Il nuovo comma 1-bis spinge a riparare invece di sostituire. Per un ricambio usato spesso la riparazione non ha senso, ma se il cliente la sceglie e tu la fai, ricordati che la garanzia riparte più lunga.",
    ],
    nelGestionale:
      "Scontrini, fatture e preventivi escono dal gestionale con il codice del pezzo e la sua condizione. Il reso si registra con la nota di credito e il pezzo torna in magazzino da ricontrollare prima di rimetterlo in vendita.",
    fonti: [{ nome: "Codice del Consumo, art. 133 su Normattiva", url: "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:2005-09-06;206~art133" }],
  },
];

export function articolo(slug: string) {
  return ARTICOLI.find((a) => a.slug === slug);
}

export function dataLunga(iso: string) {
  return new Date(`${iso}T12:00:00`).toLocaleDateString("it-IT", { day: "numeric", month: "long", year: "numeric" });
}
