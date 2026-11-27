// Normative commentate per le pagine pubbliche /news.
// Fatti verificati sulle fonti ufficiali il 18/11/2026 (Normattiva, GUUE, rentri.gov.it, documenti del Consiglio UE);
// le schede sui codici del registro, sul MUD e sulle batterie il 25/11/2026 (API RENTRI, DD MASE 251/2023,
// DPCM MUD 30/01/2026, Decisione delegata UE 2025/934 e rettifica).
// Per aggiungere un articolo: un oggetto in ARTICOLI. Sitemap, llms.txt, metadati e dati strutturati
// (Article, FAQPage, BreadcrumbList) si aggiornano da soli.
// SEO e GEO: «inBreve» è la risposta diretta in due frasi (la citano motori e assistenti AI), «domande» sono le
// domande come le farebbe un demolitore, ognuna con una risposta che si regge da sola.

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
  /** Risposta diretta, due o tre frasi che si reggono da sole */
  inBreve?: string;
  /** Tabella dei codici ufficiali di cui parla la scheda */
  codici?: { titolo: string; righe: { codice: string; cosa: string }[] };
  /** Domande frequenti: diventano anche dati strutturati FAQPage */
  domande?: { d: string; r: string }[];
};

export const ARTICOLI: Articolo[] = [
  {
    slug: "codici-registro-rentri-veicoli-fuori-uso",
    titolo: "Registro RENTRI per i veicoli fuori uso: causali, provenienza e classi di pericolo",
    titoloSeo: "Codici del registro RENTRI per autodemolizioni",
    descrizione:
      "T* e non *T, provenienza S, classi HP01–HP15 nel formulario, certificato di rottamazione: i codici che un centro di raccolta scrive nel registro e nel FIR.",
    data: "2026-11-25",
    norma: "RENTRI · DD 251/2023",
    riferimenti: [
      "DM 4 aprile 2023 n. 59, art. 4",
      "Decreto direttoriale MASE n. 251 del 19/12/2023, Allegato 1",
      "Specifiche API RENTRI dati-registri e formulari (ottobre 2026)",
      "D.P.R. 23/09/2022 n. 177 (RVFU)",
    ],
    parole: [
      "codici registro RENTRI",
      "causale T* RENTRI",
      "provenienza rifiuto speciale",
      "classi di pericolo HP",
      "registro carico scarico autodemolizione",
      "veicoli fuori uso RENTRI",
      "certificato di rottamazione registro",
      "rettifica registrazione RENTRI",
    ],
    inBreve:
      "Oltre al codice EER, ogni registrazione di un'autodemolizione nel registro RENTRI porta codici presi da elenchi chiusi: la causale (T*, NP, I, aT), la provenienza (S per i veicoli fuori uso), lo stato fisico, le classi di pericolo HP per i rifiuti con l'asterisco e l'attività di destinazione, per esempio R13. Per ogni veicolo vanno indicati anche numero e data del certificato di rottamazione rilasciato dal RVFU.",
    sintesi: [
      "Le causali ammesse dal RENTRI sono DT, NP, T*, RE, I, aT, M, TR e T*aT. Per un centro di raccolta contano soprattutto T* (veicolo ricevuto da terzi), NP (rifiuti nati dalla bonifica), I (veicolo avviato a bonifica) e aT (rifiuto uscito con formulario).",
      "La causale «ricevuto da terzi» si scrive T*, con l'asterisco dopo la lettera: è il valore che le API RENTRI accettano.",
      "Rettifica e annullamento non sono causali: sono registrazioni nuove, con un proprio numero, che richiamano anno e numero di quella da correggere. Una rettifica non si rettifica e non sposta la data della registrazione originale.",
      "La provenienza vale U (urbano) o S (speciale). La Tabella 8 delle istruzioni del DD 251/2023 mette i veicoli fuori uso (punto 15) tra i rifiuti speciali: per un'autodemolizione è S.",
      "Lo stato fisico ha cinque valori: SP solido pulverulento, S solido non pulverulento, FP fangoso, L liquido, VS vischioso e sciropposo.",
      "Le classi di pericolo vanno da HP01 a HP15. Nel formulario digitale sono «richieste se e solo se» il codice EER è pericoloso; nel registro «possono essere indicate». Nessuna norma le assegna codice per codice: le attribuisce chi produce il rifiuto.",
      "L'impianto indica le quantità in kg (DD 251/2023, campo 14).",
      "Gli impianti del D.Lgs. 209/2003 compilano il campo «Veicoli fuori uso» e indicano data e numero del certificato di rottamazione assegnato dal Registro unico telematico dei veicoli fuori uso (campi 17 e 18).",
      "Le categorie AEE (Cat1–Cat6, PF) le compilano solo gli impianti RAEE dell'art. 20 del D.Lgs. 49/2014. Né il registro né il formulario chiedono la categoria del veicolo (M1, N1).",
    ],
    codici: {
      titolo: "I codici di un'autodemolizione nel registro RENTRI",
      righe: [
        { codice: "T*", cosa: "Carico ricevuto da terzi: il veicolo che entra" },
        { codice: "NP", cosa: "Carico nuovo produttore: batteria, oli, liquidi, carcassa nati dalla bonifica" },
        { codice: "I", cosa: "Scarico interno: il veicolo avviato a bonifica, richiama il carico T*" },
        { codice: "aT", cosa: "Scarico a terzi: il rifiuto che esce con il formulario" },
        { codice: "S", cosa: "Provenienza speciale (U è per gli urbani)" },
        { codice: "S · L", cosa: "Stato fisico solido non pulverulento · liquido (gli altri: SP, FP, VS)" },
        { codice: "HP01–HP15", cosa: "Classi di pericolo, per i codici con l'asterisco" },
        { codice: "R13", cosa: "Messa in riserva: l'attività più comune a destinazione (R1–R13, D1–D15)" },
      ],
    },
    date: [
      { quando: "Ogni mese", cosa: "Trasmissione del registro al RENTRI entro la fine del mese successivo a quello delle annotazioni." },
      { quando: "03/12/2026", cosa: "Il RENTRI pubblica i nuovi codici EER delle batterie." },
      { quando: "09/12/2026", cosa: "Si applicano i nuovi codici 16 06 delle batterie." },
    ],
    commento: [
      "L'errore più frequente che vediamo nei registri portati da programmi vecchi è banale: la causale scritta «*T» invece di «T*». Sembra un dettaglio, ma un sistema che parla con le API lo rifiuta. Conviene controllarlo prima di collegarsi.",
      "Le classi di pericolo sono la parte che si rimanda sempre. Nel registro sono facoltative, ma il formulario di un rifiuto pericoloso senza HP è incompleto. Il modo più semplice è decidere una volta, con il consulente ambientale, le classi di ogni codice che produci, e poi non pensarci più.",
    ],
    nelGestionale:
      "Ogni registrazione nasce già con causale, provenienza, stato fisico, classi di pericolo e attività presi dal codice EER. Il carico del veicolo porta il numero del certificato di rottamazione dalla pratica. Le classi di pericolo proposte si confermano una volta con la consulente; se un codice pericoloso ne è senza, il periodo da trasmettere lo segnala.",
    fonti: [
      { nome: "Istruzioni del registro, Allegato 1 al DD 251/2023 (MASE)", url: "https://www.mase.gov.it/sites/default/files/archivio/bandi/EC/allegato1_dd_251_19_12_2023.pdf" },
      { nome: "Documentazione tecnica e API RENTRI", url: "https://api.rentri.gov.it/docs" },
      { nome: "DM 59/2023 su Normattiva", url: "https://www.normattiva.it/uri-res/N2Ls?urn:nir:ministero.ambiente.e.sicurezza.energetica:decreto:2023-04-04;59" },
    ],
    domande: [
      { d: "Nel registro RENTRI la causale si scrive *T o T*?", r: "T*, con l'asterisco dopo la lettera. È il valore che le API RENTRI accettano per il carico «ricevuto da terzi»; «*T» viene rifiutato." },
      { d: "Che provenienza va indicata per un veicolo fuori uso?", r: "S, rifiuto speciale. Le istruzioni del DD 251/2023 (Tabella 8, punto 15) mettono i veicoli fuori uso tra i rifiuti speciali, e lo stesso vale per i rifiuti che nascono dalla loro bonifica." },
      { d: "Le classi di pericolo HP sono obbligatorie?", r: "Nel formulario digitale sì, per ogni codice EER con l'asterisco. Nel registro si possono indicare. Le attribuisce il produttore del rifiuto, di solito con il consulente ambientale." },
      { d: "Bisogna scrivere la categoria del veicolo, M1 o N1?", r: "No. Né il registro né il formulario RENTRI hanno un campo per la categoria del veicolo. Per un veicolo fuori uso si indicano il codice 16 01 04*, la spunta «veicoli fuori uso» e numero e data del certificato di rottamazione." },
      { d: "Come si corregge una registrazione già numerata?", r: "Con una registrazione di rettifica, che ha un proprio numero e richiama anno e numero di quella sbagliata, oppure con un annullamento. La registrazione originale non si modifica." },
    ],
  },
  {
    slug: "mud-veicoli-fuori-uso-scheda-aut-2026",
    titolo: "MUD veicoli fuori uso: la Scheda AUT e i veicoli prima e dopo il 1980",
    titoloSeo: "MUD veicoli fuori uso: guida alla Scheda AUT",
    descrizione:
      "Chi compila la Scheda AUT, come dividere il 16 01 04 tra veicoli immatricolati prima e dopo il 1980, i codici EER preimpostati e cosa prendere dal registro.",
    data: "2026-11-25",
    norma: "MUD · DPCM 30/01/2026",
    riferimenti: [
      "DPCM 30 gennaio 2026 (GU n. 53 del 5/03/2026), Allegato 1 §7 e Allegato 3",
      "D.Lgs. 24/06/2003 n. 209, art. 7 c. 2-bis",
    ],
    parole: [
      "MUD veicoli fuori uso",
      "scheda AUT autodemolitore",
      "MUD 2026 autodemolizione",
      "comunicazione veicoli fuori uso",
      "veicoli prima del 1980 MUD",
      "codici EER scheda AUT",
      "RT-VEIC DR-VEIC",
    ],
    inBreve:
      "Chi mette in sicurezza i veicoli fuori uso presenta ogni anno la Comunicazione veicoli fuori uso del MUD con la Scheda AUT. I dati si prendono dal registro di carico e scarico, e il peso dei veicoli ricevuti (16 01 04) va diviso tra quelli immatricolati prima e dopo il 1° gennaio 1980.",
    sintesi: [
      "Rientrano nel D.Lgs. 209/2003 i veicoli di categoria M1 (persone, fino a 8 posti oltre al conducente), N1 (merci, fino a 3,5 t) e L2 (tre ruote fino a 50 cc e 50 km/h).",
      "La Scheda AUT la compila chi fa la messa in sicurezza. Chi fa solo demolizione a valle compila la Scheda ROT; chi fa autodemolizione e rottamazione nella stessa unità locale compila solo la AUT.",
      "I dati si ricavano dal registro dei rifiuti. Solo se non è possibile si usano altri registri obbligatori o una stima, che va conservata nell'unità locale.",
      "Per il 16 01 04 ricevuto da terzi si indica il totale, diviso tra veicoli prodotti prima e dopo il 1° gennaio 1980. Come anno di produzione vale l'anno di immatricolazione.",
      "Ogni rifiuto ha i suoi moduli: RT-VEIC per chi l'ha consegnato (privati compresi), DR-VEIC per chi l'ha ricevuto, TE-VEIC per i trasportatori.",
      "Il riepilogo chiede le quantità a reimpiego (compresi i ricambi venduti), a smaltimento, a recupero di materia e di energia, il 16 01 04 in giacenza al 31/12 e gli altri rifiuti in giacenza, 16 01 06 compreso.",
      "Si dichiarano anche i materiali che hanno cessato di essere rifiuti: rottami di ferro e acciaio, alluminio, rame, vetro, plastica, gomma, tessili.",
      "È anche il canale con cui gli impianti comunicano il peso effettivo dei veicoli rilevato in ingresso e i dati per gli obiettivi di recupero (art. 7 c. 2-bis D.Lgs. 209/2003).",
    ],
    codici: {
      titolo: "Codici EER preimpostati nella Scheda AUT 2026",
      righe: [
        { codice: "16 01 04", cosa: "Veicoli fuori uso (ricevuti, divisi prima e dopo il 1980)" },
        { codice: "16 01 06", cosa: "Veicoli fuori uso bonificati" },
        { codice: "16 01 03", cosa: "Pneumatici fuori uso" },
        { codice: "16 01 06 – 16 01 22", cosa: "Componenti e materiali: filtri, airbag, liquidi, metalli, plastica, vetro" },
        { codice: "16 06 01 · 16 08 01 · 16 08 07", cosa: "Batterie al piombo, catalizzatori" },
        { codice: "13 01 09 – 13 01 13", cosa: "Oli del circuito idraulico" },
        { codice: "13 02 05 – 13 02 08", cosa: "Olio motore" },
        { codice: "13 07 01 · 13 07 03 · 13 08 02 · 14 06 01 · 14 06 02 · 16 10 02", cosa: "Altri liquidi e fluidi: gasolio, altri carburanti, emulsioni, gas, liquidi acquosi" },
      ],
    },
    date: [
      { quando: "03/07/2026", cosa: "Scadenza del MUD 2026, sui dati del 2025 (modello pubblicato in G.U. il 5 marzo 2026)." },
      { quando: "31/12", cosa: "Data a cui si fotografano le giacenze: 16 01 04 da bonificare e altri rifiuti." },
    ],
    commento: [
      "La divisione prima e dopo il 1980 è la domanda che fa perdere più tempo a fine anno, perché nel registro tutte le auto sono 16 01 04 e basta. Se l'anno di immatricolazione è nella scheda del veicolo, il conto si fa da solo; se no, si ricostruisce libretto per libretto.",
      "Nell'elenco preimpostato non c'è la benzina 13 07 02, mentre ci sono 13 07 01 e 13 07 03. Se registri la benzina con il suo codice, chiedi al consulente o alla Camera di Commercio come riportarla nella scheda prima della scadenza, non il giorno prima.",
    ],
    nelGestionale:
      "La pagina Registro rifiuti mostra il peso dei veicoli ricevuti nell'anno diviso tra immatricolati prima del 1980 e dal 1980, con rettifiche e annullamenti già applicati, e segnala i veicoli senza anno. Giacenze, uscite e destinatari vengono dal registro e dai formulari.",
    fonti: [
      { nome: "MUD 2026: DPCM e allegati (MASE)", url: "https://www.mase.gov.it/portale/-/mud-modello-unico-di-dichiarazione-ambientale-per-l-anno-2026" },
      { nome: "D.Lgs. 209/2003, art. 7 su Normattiva", url: "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:2003-06-24;209~art7" },
      { nome: "Invio telematico del MUD", url: "https://www.mudtelematico.it" },
    ],
    domande: [
      { d: "Chi deve compilare la Scheda AUT del MUD?", r: "Chi effettua la messa in sicurezza dei veicoli fuori uso ai sensi del D.Lgs. 209/2003. Chi fa solo demolizione dopo la messa in sicurezza compila la Scheda ROT; chi fa autodemolizione e rottamazione nella stessa unità locale compila solo la AUT." },
      { d: "Come si divide il 16 01 04 tra prima e dopo il 1980?", r: "Si riporta il peso totale dei veicoli fuori uso ricevuti nell'anno e lo si divide tra quelli prodotti prima e dopo il 1° gennaio 1980, dove come anno di produzione vale l'anno di immatricolazione." },
      { d: "Da dove si prendono i dati del MUD veicoli fuori uso?", r: "Dal registro di carico e scarico dei rifiuti. Solo se non è possibile si usano altri registri obbligatori o una stima, che va conservata nell'unità locale." },
      { d: "I ricambi venduti contano nel MUD?", r: "Sì: la quantità a reimpiego comprende tutte le parti dei veicoli riutilizzate, comprese quelle vendute direttamente." },
      { d: "Che categorie di veicoli rientrano nel MUD veicoli fuori uso?", r: "M1, N1 e i veicoli a tre ruote L2. Le categorie servono a capire chi dichiara: nella scheda non si scrivono." },
    ],
  },
  {
    slug: "nuovi-codici-eer-batterie-auto-elettriche-2026",
    titolo: "Batterie delle auto elettriche: dal 9 dicembre 2026 cambiano i codici EER",
    titoloSeo: "Nuovi codici EER batterie al litio dal 9/12/2026",
    descrizione:
      "La Decisione (UE) 2025/934 riscrive il capitolo 16 06: arriva 16 06 07* per le batterie al litio, sparisce 16 06 05. Date, codici e cosa cambia in piazzale.",
    data: "2026-11-25",
    norma: "Decisione (UE) 2025/934",
    riferimenti: [
      "Decisione delegata (UE) 2025/934 della Commissione del 5/03/2025, GU L del 20/05/2025",
      "Rettifica, GU L 2025/90657 del 19/08/2025",
      "Decisione 2000/532/CE (elenco europeo dei rifiuti)",
    ],
    parole: [
      "nuovi codici EER batterie",
      "16 06 07 batterie al litio",
      "codice EER batteria auto elettrica",
      "decisione UE 2025/934",
      "batterie di trazione rifiuto",
      "16 06 05 abrogato",
      "batterie NiMH 16 06 08",
    ],
    inBreve:
      "Dal 9 dicembre 2026 le batterie delle auto elettriche e ibride si registrano con i nuovi codici del capitolo 16 06: 16 06 07* per le batterie al litio e 16 06 08* per quelle al nichel come le NiMH. Il codice 16 06 05 sparisce e 16 06 01* diventa «rifiuti di batterie al piombo-acido».",
    sintesi: [
      "La Decisione delegata (UE) 2025/934 sostituisce tutto il capitolo 16 06 dell'elenco europeo dei rifiuti, per allinearlo al regolamento sulle batterie (UE) 2023/1542.",
      "Doveva applicarsi dal 9 novembre 2026; la rettifica del 19 agosto 2025 ha spostato la data al 9 dicembre 2026.",
      "Nasce 16 06 07* «rifiuti di batterie al litio»: è il codice della batteria di trazione di un'auto elettrica o di un'ibrida al litio.",
      "16 06 08* è per le batterie al nichel diverse dal nichel-cadmio, per esempio NiMH: è il caso di molte ibride.",
      "16 06 01* resta, con il nome «rifiuti di batterie al piombo-acido»: è la batteria da 12 volt di quasi tutte le auto.",
      "La vecchia voce 16 06 05 «altre batterie e accumulatori» non c'è più. Al suo posto ci sono codici per tipo chimico, 16 06 13* per le batterie miste, 16 06 14* e 16 06 15 per le altre.",
      "Il RENTRI ha annunciato che il 3 dicembre 2026 pubblicherà i nuovi codici e le descrizioni aggiornate nel servizio dei codici EER.",
    ],
    codici: {
      titolo: "I codici 16 06 che toccano un'autodemolizione",
      righe: [
        { codice: "16 06 01*", cosa: "Rifiuti di batterie al piombo-acido (batteria da 12 V)" },
        { codice: "16 06 07*", cosa: "Rifiuti di batterie al litio (trazione di elettriche e molte ibride)" },
        { codice: "16 06 08*", cosa: "Batterie al nichel diverse dal nichel-cadmio, es. NiMH" },
        { codice: "16 06 02*", cosa: "Batterie al nichel-cadmio" },
        { codice: "16 06 13*", cosa: "Rifiuti di batterie misti" },
        { codice: "16 06 14* · 16 06 15", cosa: "Altre batterie, con o senza sostanze pericolose" },
        { codice: "16 06 05", cosa: "Altre batterie e accumulatori: soppresso dal 9/12/2026" },
      ],
    },
    date: [
      { quando: "20/05/2025", cosa: "Pubblicata la Decisione (UE) 2025/934." },
      { quando: "19/08/2025", cosa: "Rettifica: applicazione spostata dal 9 novembre al 9 dicembre 2026." },
      { quando: "03/12/2026", cosa: "Il RENTRI pubblica i nuovi codici EER." },
      { quando: "09/12/2026", cosa: "Si applicano i nuovi codici." },
    ],
    commento: [
      "Il cambio di codice tocca tre cose insieme: il registro, i formulari e l'autorizzazione. Se l'autorizzazione dell'impianto elenca 16 06 05 per le batterie di trazione, conviene sentire subito l'ente e il consulente per capire come leggerla dal 9 dicembre.",
      "Le batterie di trazione pesano centinaia di chili e restano in piazzale a lungo, spesso in attesa di un ritiro dedicato. Una giacenza registrata a novembre con il codice vecchio va seguita: chiedi al consulente come chiuderla e riaprirla con il codice nuovo.",
    ],
    nelGestionale:
      "Nella bonifica delle auto elettriche e ibride compare la voce «Batteria di trazione»: fino all'8 dicembre 2026 si registra con 16 06 05, dal 9 dicembre con 16 06 07*. La batteria da 12 volt resta 16 06 01*.",
    fonti: [
      { nome: "Decisione delegata (UE) 2025/934 (EUR-Lex)", url: "https://eur-lex.europa.eu/eli/dec_del/2025/934/oj" },
      { nome: "Rettifica del 19/08/2025 (EUR-Lex)", url: "https://eur-lex.europa.eu/eli/dec_del/2025/934/corrigendum/2025-08-19/oj" },
      { nome: "Documentazione tecnica e annunci RENTRI", url: "https://api.rentri.gov.it/docs" },
    ],
    domande: [
      { d: "Che codice EER ha la batteria di un'auto elettrica?", r: "Dal 9 dicembre 2026 è 16 06 07* «rifiuti di batterie al litio». Prima di quella data la batteria di trazione si registrava di solito come 16 06 05." },
      { d: "Da quando si usano i nuovi codici delle batterie?", r: "Dal 9 dicembre 2026. La Decisione (UE) 2025/934 indicava il 9 novembre 2026, ma la rettifica del 19 agosto 2025 ha spostato la data." },
      { d: "Il codice 16 06 05 esiste ancora?", r: "No: dal 9 dicembre 2026 la voce 16 06 05 «altre batterie e accumulatori» non fa più parte dell'elenco europeo dei rifiuti." },
      { d: "Con che codice si registra la batteria di un'ibrida?", r: "Dipende dalla chimica: 16 06 07* se è al litio, 16 06 08* se è al nichel-metallo idruro (NiMH). Il tipo è sull'etichetta della batteria o nei dati tecnici del modello." },
      { d: "Cambia qualcosa per la batteria da 12 volt?", r: "Il codice resta 16 06 01*, ma la descrizione diventa «rifiuti di batterie al piombo-acido»." },
    ],
  },
  {
    slug: "fir-digitale-rentri-16-settembre-2026",
    titolo: "FIR solo digitale dal 16 settembre 2026: cosa cambia per chi demolisce",
    titoloSeo: "FIR digitale dal 16/09/2026: guida RENTRI",
    descrizione:
      "FIR cartaceo finito il 15 settembre 2026: scaglioni RENTRI, trasmissione mensile del registro, contributo annuale e sanzioni per i centri di raccolta.",
    data: "2026-11-18",
    aggiornato: "2026-11-25",
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
    inBreve:
      "Dal 16 settembre 2026 il formulario di identificazione dei rifiuti (FIR) è solo digitale: il cartaceo era ammesso fino al 15 settembre e da quella data si applicano anche le sanzioni sulla trasmissione dei dati. Il registro di carico e scarico si trasmette al RENTRI ogni mese, entro la fine del mese successivo.",
    domande: [
      { d: "Da quando il formulario rifiuti è solo digitale?", r: "Dal 16 settembre 2026. Il FIR cartaceo si poteva usare, in alternativa, fino al 15 settembre 2026." },
      { d: "Ogni quanto si trasmette il registro di carico e scarico al RENTRI?", r: "Ogni mese, entro la fine del mese successivo a quello delle annotazioni. Se nel mese non ci sono annotazioni, non si trasmette niente." },
      { d: "Entro quando si paga il contributo annuale RENTRI?", r: "Entro il 30 aprile di ogni anno, per ciascuna unità locale." },
      { d: "Quando parte la geolocalizzazione dei mezzi nel RENTRI?", r: "La messa a disposizione dei dati di percorso dei mezzi è stata spostata al 13 settembre 2027." },
    ],
  },
  {
    slug: "bonifica-veicoli-fuori-uso-10-giorni-dlgs-209-2003",
    titolo: "Messa in sicurezza entro 10 giorni lavorativi: gli obblighi del centro di raccolta",
    titoloSeo: "Bonifica veicoli fuori uso: i 10 giorni lavorativi",
    descrizione:
      "Dopo il D.Lgs. 119/2020 la bonifica va fatta entro 10 giorni lavorativi dall'ingresso. Accatastamento, stoccaggio dei ricambi e obiettivi di recupero del 95%.",
    data: "2026-11-18",
    aggiornato: "2026-11-25",
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
    inBreve:
      "Un veicolo fuori uso va messo in sicurezza entro dieci giorni lavorativi dall'ingresso nel centro di raccolta, anche se non è ancora cancellato dal PRA (art. 6 c. 2 D.Lgs. 209/2003). Messa in sicurezza vuol dire togliere batterie, liquidi, filtri e componenti pericolosi.",
    domande: [
      { d: "Entro quanti giorni va bonificato un veicolo fuori uso?", r: "Entro dieci giorni lavorativi dall'ingresso nel centro di raccolta, anche se il veicolo non è ancora stato cancellato dal PRA." },
      { d: "Quanti veicoli si possono accatastare in piazzale?", r: "Nell'area di conferimento nessuno. I veicoli messi in sicurezza ma non ancora trattati al massimo in tre; le carcasse già trattate fino a 5 metri di altezza." },
      { d: "Qual è l'obiettivo di recupero dei veicoli fuori uso?", r: "Dal 2015 reimpiego e recupero devono arrivare almeno al 95% del peso medio del veicolo, reimpiego e riciclaggio almeno all'85%." },
    ],
  },
  {
    slug: "regolamento-ue-2026-1738-veicoli-fuori-uso",
    titolo: "Regolamento (UE) 2026/1738: dal 2029 ricambi da smontare ed etichettare prima della frantumazione",
    titoloSeo: "Nuovo regolamento UE veicoli fuori uso 2026/1738",
    descrizione:
      "Il regolamento UE sui veicoli fuori uso sostituisce la direttiva 2000/53/CE: pezzi da smontare, etichetta sui ricambi usati, certificato elettronico, export.",
    data: "2026-11-18",
    aggiornato: "2026-11-25",
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
    inBreve:
      "Il Regolamento (UE) 2026/1738 sostituisce la direttiva 2000/53/CE sui veicoli fuori uso: è in vigore dal 13 agosto 2026 e si applica in generale dal 1° settembre 2028. Dal 1° settembre 2029 i pezzi dell'Allegato VIII vanno smontati prima della frantumazione e i ricambi usati venduti devono portare l'etichetta dell'impianto di trattamento.",
    domande: [
      { d: "Da quando si applica il nuovo regolamento europeo sui veicoli fuori uso?", r: "In generale dal 1° settembre 2028; è in vigore dal 13 agosto 2026. Alcuni obblighi partono dopo, come l'etichetta sui ricambi usati dal 1° settembre 2029." },
      { d: "I ricambi usati venduti online dovranno avere un'etichetta?", r: "Sì: dal 1° settembre 2029 chi vende ricambi usati, anche online, deve garantire che portino l'etichetta dell'impianto di trattamento (art. 31)." },
      { d: "Un ricambio smontato e idoneo al riuso è un rifiuto?", r: "No: se dopo la valutazione è idoneo al riuso non è un rifiuto (art. 30)." },
    ],
  },
  {
    slug: "gpsr-ricambi-usati-online",
    titolo: "Ricambi usati online: cosa chiede il regolamento sulla sicurezza dei prodotti",
    titoloSeo: "GPSR e ricambi usati: cosa va nell'annuncio",
    descrizione:
      "Dal 13 dicembre 2024 il GPSR vale anche per l'usato venduto da professionisti: cosa deve mostrare l'annuncio online e quando i pezzi da riparare sono esclusi.",
    data: "2026-11-18",
    aggiornato: "2026-11-25",
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
    inBreve:
      "Dal 13 dicembre 2024 il regolamento GPSR (UE) 2023/988 vale anche per i prodotti usati venduti da professionisti, ricambi auto compresi. Sono esclusi solo i pezzi venduti chiaramente come da riparare o ricondizionare; per gli altri l'annuncio online deve mostrare fabbricante, immagine, identificativo e avvertenze.",
    domande: [
      { d: "Il GPSR vale anche per i ricambi auto usati?", r: "Sì, se li vende un professionista: il regolamento si applica ai prodotti nuovi, usati, riparati o ricondizionati dal 13 dicembre 2024." },
      { d: "Quali ricambi usati sono esclusi dal GPSR?", r: "Quelli da riparare o ricondizionare prima dell'uso, purché l'annuncio lo dica chiaramente." },
      { d: "Cosa deve mostrare un annuncio di ricambi usati per il GPSR?", r: "Nome, indirizzo postale ed email del fabbricante, l'eventuale responsabile nell'UE, un'immagine, il tipo e l'identificativo del prodotto e le avvertenze di sicurezza (art. 19)." },
    ],
  },
  {
    slug: "rvfu-registro-telematico-veicoli-fuori-uso-radiazione",
    titolo: "Registro telematico dei veicoli fuori uso: certificato digitale e radiazione diretta",
    titoloSeo: "RVFU e radiazione per demolizione: cosa cambia",
    descrizione:
      "Dal 7 giugno 2024 il registro dei veicoli fuori uso è solo telematico e il centro di raccolta radia da sé. Dal 2026 il fermo non blocca più la demolizione.",
    data: "2026-11-18",
    aggiornato: "2026-11-25",
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
    inBreve:
      "Dal 7 giugno 2024 il registro dei veicoli fuori uso è solo telematico (RVFU) e il centro di raccolta cancella direttamente il veicolo dal PRA, emettendo il certificato di rottamazione digitale. Dal 2026 il fermo amministrativo non impedisce più la radiazione per demolizione.",
    domande: [
      { d: "Il fermo amministrativo blocca la demolizione?", r: "Non più: con la L. 14/2026 il fermo non impedisce la radiazione per demolizione. Chi rottama un veicolo con fermo però non ha diritto agli incentivi per comprarne uno nuovo." },
      { d: "Chi cancella il veicolo dal PRA quando si demolisce?", r: "Il centro di raccolta, direttamente, attraverso il Registro unico telematico dei veicoli fuori uso (RVFU)." },
      { d: "Entro quanto si restituiscono documenti e targhe?", r: "Entro 30 giorni dalla consegna del veicolo (art. 5 c. 8 del D.Lgs. 209/2003)." },
    ],
  },
  {
    slug: "garanzia-legale-ricambi-usati-12-mesi",
    titolo: "Garanzia sui ricambi usati: 24 mesi, riducibili a 12, e l'estensione dopo una riparazione",
    titoloSeo: "Garanzia legale sui ricambi usati: 12 o 24 mesi?",
    descrizione:
      "Sui ricambi usati la garanzia legale è di 24 mesi, riducibili a 12 per iscritto. Dal 2026, se il cliente sceglie la riparazione, si allunga di 12 mesi.",
    data: "2026-11-18",
    aggiornato: "2026-11-25",
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
    inBreve:
      "Anche sui ricambi usati venduti a un consumatore la garanzia legale è di 24 mesi, ma per l'usato si può ridurre per iscritto fino a 12 mesi (art. 133 Codice del Consumo). Per i contratti dal 31 luglio 2026, se il cliente sceglie la riparazione la garanzia si allunga una volta di 12 mesi.",
    domande: [
      { d: "Quanto dura la garanzia sui ricambi usati?", r: "24 mesi verso il consumatore, riducibili per iscritto a non meno di 12 mesi per i beni usati." },
      { d: "Come si riduce la garanzia dell'usato a 12 mesi?", r: "Va concordata prima dell'acquisto, quindi scritta sul documento di vendita o nelle condizioni del negozio online. Un cartello in negozio non basta a dimostrarlo." },
      { d: "La garanzia legale vale anche per le officine?", r: "No: vale verso i consumatori. Con officine e aziende si applicano il codice civile e quello che concordate." },
    ],
  },
];

export function articolo(slug: string) {
  return ARTICOLI.find((a) => a.slug === slug);
}

export function dataLunga(iso: string) {
  return new Date(`${iso}T12:00:00`).toLocaleDateString("it-IT", { day: "numeric", month: "long", year: "numeric" });
}
