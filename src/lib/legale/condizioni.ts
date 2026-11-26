// Condizioni del servizio di Piazzale (/condizioni), con in fondo l'accordo sul trattamento dei dati (art. 28 GDPR).
// Piano 3, Task 2. Testo puro: nomi e dati dell'azienda da BRAND e PRODUTTORE, prezzi e commissione da listino.ts,
// giorni di prova da abbonamento.ts, versione da consensi.ts (quella salvata con il consenso). Mai scritti a mano.
// Ruoli come in privacy.ts: l'azienda è titolare di quello che inserisce (clienti, proprietari, account dei dipendenti,
// registro delle attività), noi responsabili; noi titolari solo per chi registra, fatture, consensi e sicurezza.
// Comportamento dell'app descritto qui: abbonamento.ts (blocco, prova), stripe/server.ts (moduli aggiunti e tolti),
// api/abbonamento/portale (disdetta a fine periodo dal portale di Stripe), pricing.ts (prezzo online con la commissione).
import { BRAND, PRODUTTORE } from "../config.ts";
import { VERSIONE_CONDIZIONI } from "../consensi.ts";
import { COMMISSIONE_ONLINE, euro, LISTINO } from "../listino.ts";
import { GIORNI_PROVA } from "../abbonamento.ts";
import { ORDINE_MODULI } from "../moduli.ts";
import { FORNITORI, SERVIZI_COLLEGATI, voceFornitore, voceServizioCollegato, type Documento, type Sezione } from "./comune.ts";

const NOI = PRODUTTORE.ragioneSociale;
const PEC = `[${PRODUTTORE.pec}](mailto:${PRODUTTORE.pec})`;
const INFORMATIVA = "[informativa privacy](/privacy)";
const ACCORDO = "[accordo sul trattamento dei dati](#accordo)";
const PERCENTUALE = `${Math.round(COMMISSIONE_ONLINE * 100)}%`;
const PROVA = `${GIORNI_PROVA} giorni`;
const PORTALE = "«Carta, fatture e disdetta»";

const BASE = LISTINO.magazzino.nome;
const AGGIUNTIVI = ORDINE_MODULI.filter((m) => m !== "magazzino").map((m) => LISTINO[m].nome);
const elencoNomi = (nomi: string[]) => (nomi.length < 2 ? nomi.join("") : `${nomi.slice(0, -1).join(", ")} e ${nomi.at(-1)}`);
const vocePrezzo = (m: (typeof ORDINE_MODULI)[number]) =>
  `${LISTINO[m].nome}: ${euro(LISTINO[m].mese)} al mese oppure ${euro(LISTINO[m].anno)} all'anno${m === "magazzino" ? ", sempre compreso" : ""}.`;

const RECESSO_CON_RIMBORSO = `può recedere prima che valga, scrivendo alla PEC ${PEC}: le restituiamo la parte non usata del periodo già pagato, in proporzione ai giorni`;

const SEZIONI: Sezione[] = [
    {
      id: "parti",
      titolo: "Chi siamo e a chi è rivolto il servizio",
      paragrafi: [
        `Queste condizioni regolano l'uso di ${BRAND.azienda}, il gestionale online per autodemolizioni di ${PRODUTTORE.nome}.`,
        `Il servizio lo fornisce ${NOI}, ${PRODUTTORE.sede}, P. IVA e C.F. ${PRODUTTORE.piva}, REA ${PRODUTTORE.rea} («noi»). Il contratto è tra noi e l'impresa che si registra («l'azienda»).`,
        `${BRAND.azienda} è un servizio per autodemolizioni e altre imprese, da usare per la loro attività. Non è rivolto ai consumatori: per questo non si applicano le regole del Codice del consumo pensate per loro, come il recesso di 14 giorni.`,
        "Chi registra l'azienda dichiara di poterla rappresentare e di agire per la propria attività d'impresa o professionale. Il contratto si conclude quando completa la registrazione e accetta queste condizioni.",
      ],
    },
    {
      id: "servizio",
      titolo: "Il servizio",
      paragrafi: [
        `${BRAND.azienda} si usa online, dal browser o dall'app, con un account. L'azienda usa i moduli del suo abbonamento: quelli non attivi restano bloccati.`,
        "L'azienda decide chi entra nel suo gestionale e con quali ruoli. Risponde di come i suoi utenti lo usano e deve tenere riservate password e PIN.",
        `Se l'azienda collega un suo account a servizi di altri, come ${elencoNomi(SERVIZI_COLLEGATI.map((s) => s.nome))}, usa quei servizi con le loro condizioni e i loro costi. Noi non rispondiamo di come funzionano.`,
        `Miglioriamo ${BRAND.azienda} nel tempo e possiamo cambiarne le funzioni. Se togliamo una funzione importante di un modulo a pagamento lo diciamo prima per email.`,
      ],
    },
    {
      id: "prova",
      titolo: "Prova gratuita",
      paragrafi: [
        `Dopo la registrazione mandiamo un'email per confermare l'indirizzo. Dalla conferma partono ${PROVA} di prova gratuita, con tutti i moduli.`,
        "Per la prova non serve la carta e alla fine non c'è nessun addebito automatico: si paga solo se l'azienda sceglie di abbonarsi.",
        "Alla fine della prova il gestionale si blocca: non si possono più inserire o cambiare dati. I dati restano e il gestionale si riapre quando l'azienda si abbona.",
      ],
    },
    {
      id: "abbonamento",
      titolo: "Abbonamento e prezzi",
      paragrafi: [
        `L'abbonamento è a moduli. Il ${BASE} è la base e c'è sempre; ${elencoNomi(AGGIUNTIVI)} si aggiungono a scelta.`,
        "Si paga al mese o all'anno. I prezzi, IVA esclusa, sono questi:",
      ],
      elenco: ORDINE_MODULI.map(vocePrezzo),
      dopo: [
        {
          paragrafi: [
            "All'importo si aggiunge l'IVA. Si paga in anticipo, per un mese o per un anno, con carta su Stripe.",
            "L'abbonamento si rinnova da solo alla fine di ogni periodo, con un nuovo addebito sulla carta, finché l'azienda non lo disdice.",
            "Un modulo aggiunto durante il periodo si paga subito, per i giorni che mancano al rinnovo. Un modulo tolto si spegne subito e i giorni non usati diventano credito sulla fattura successiva, se l'abbonamento non è disdetto.",
            "Se un pagamento non riesce, Stripe riprova da solo e ne avvisa per email. Se alla fine non riesce, l'abbonamento finisce e il gestionale si blocca da solo; i dati restano.",
            `Carta, dati di fatturazione e pagamenti fatti si vedono dalla pagina Abbonamento, con ${PORTALE}.`,
          ],
        },
      ],
    },
    {
      id: "commissione",
      titolo: "Commissione sui pezzi venduti online",
      paragrafi: [
        `Quando l'azienda vende un pezzo online con ${BRAND.azienda} (negozio online, eBay o altri marketplace), il prezzo pubblicato è il suo prezzo più l'${PERCENTUALE}. Questo ${PERCENTUALE} è la nostra commissione per la gestione del venduto.`,
        "La commissione la fatturiamo all'azienda sui pezzi venduti. Se un pezzo viene reso e rimborsato, la commissione su quel pezzo si storna.",
        "Sui pezzi venduti al banco non c'è nessuna commissione.",
        "Le commissioni dei marketplace le applica il marketplace all'azienda, secondo il contratto che ha con lei.",
      ],
    },
    {
      id: "disdetta",
      titolo: "Disdetta e fine del contratto",
      paragrafi: [
        `L'azienda può disdire in ogni momento dalla pagina Abbonamento, con ${PORTALE}. La disdetta vale alla fine del periodo già pagato: fino ad allora il gestionale funziona come prima e l'abbonamento si può riattivare.`,
        "Con la disdetta non rimborsiamo la parte del periodo in corso. Un rimborso c'è solo se l'azienda recede per una modifica in peggio delle condizioni o dei prezzi, o per un nuovo sub-responsabile, come dicono la sezione sulle modifiche e l'accordo.",
        "Dopo la fine il gestionale si blocca. I dati restano per 12 mesi, così l'azienda può riattivare l'abbonamento e ritrovarli; poi li cancelliamo, tranne quello che la legge ci chiede di tenere, come le fatture. Lo stesso vale per una prova finita senza abbonamento.",
        `Prima della cancellazione l'azienda può chiedere una copia dei suoi dati alla PEC ${PEC}.`,
        "Possiamo sospendere o chiudere l'account se l'azienda non paga la commissione, o se usa il servizio in modo illecito o contro queste condizioni. Prima la avvisiamo per email, salvo i casi urgenti, come un attacco alla piattaforma. Il blocco dopo un pagamento dell'abbonamento non riuscito invece è automatico, come detto sopra.",
      ],
    },
    {
      id: "dati",
      titolo: "Dati personali",
      paragrafi: [
        `Come trattiamo i dati di chi registra l'azienda, e quelli per la sicurezza degli accessi, lo spiega l'${INFORMATIVA}.`,
        `I dati che l'azienda inserisce nel gestionale (clienti, proprietari dei veicoli, account e ruoli dei dipendenti, registro delle attività) sono suoi: l'azienda ne è titolare e noi responsabili del trattamento. Le regole sono nell'${ACCORDO} in fondo a questa pagina, che fa parte di queste condizioni.`,
        "L'azienda deve informare i suoi clienti e i suoi dipendenti di come tratta i loro dati, e trattarli secondo la legge.",
      ],
    },
    {
      id: "responsabilita",
      titolo: "Responsabilità",
      paragrafi: [
        `Facciamo il possibile perché ${BRAND.azienda} funzioni bene. Non possiamo però garantire che sia sempre disponibile e senza errori: possono esserci guasti, manutenzioni, problemi dei fornitori o della rete.`,
        `L'azienda resta responsabile dei suoi obblighi di legge: registri, RENTRI, formulari, pratiche dei veicoli, fatture e corrispettivi. ${BRAND.azienda} è uno strumento che la aiuta, ma dati e scadenze li controlla lei.`,
        "La nostra responsabilità verso l'azienda non supera, in tutto, quanto l'azienda ci ha pagato nei 12 mesi prima del fatto che causa il danno. Questo limite non vale in caso di dolo o colpa grave.",
      ],
    },
    {
      id: "modifiche",
      titolo: "Modifiche alle condizioni e ai prezzi",
      paragrafi: [
        "Possiamo cambiare queste condizioni e i prezzi. Le modifiche le diciamo per email almeno 30 giorni prima che valgano, e aggiorniamo la data della versione in cima alla pagina.",
        "Un nuovo prezzo vale dal primo rinnovo dopo quella data.",
        `Se una modifica peggiora le condizioni per l'azienda, compreso un aumento di prezzo, l'azienda ${RECESSO_CON_RIMBORSO}.`,
        "Le modifiche che non peggiorano le condizioni dell'azienda, o che la legge impone subito, possono valere prima dei 30 giorni.",
        "Con l'accettazione salviamo la versione delle condizioni, così resta chiaro quale testo l'azienda ha accettato e quando.",
      ],
    },
    {
      id: "legge",
      titolo: "Legge e foro",
      paragrafi: [
        "Queste condizioni sono regolate dalla legge italiana.",
        "Per ogni controversia è competente in via esclusiva il foro di Torino.",
        `Per domande su queste condizioni scrivi alla PEC ${PEC}.`,
      ],
    },
    {
      id: "accordo",
      titolo: "Allegato: accordo sul trattamento dei dati per conto del cliente (art. 28 GDPR)",
      paragrafi: [
        `Questo accordo fa parte delle condizioni del servizio. Regola i dati personali che ${NOI} tratta per conto dell'azienda, come chiede l'art. 28 del GDPR.`,
        `L'azienda è titolare del trattamento dei dati che inserisce o fa inserire in ${BRAND.azienda}: i dati dei suoi clienti e dei proprietari dei veicoli, gli account dei suoi dipendenti con i loro ruoli, il registro delle attività (chi ha fatto cosa e quando). ${NOI} è responsabile del trattamento di questi dati.`,
        `Restiamo titolari, come spiega l'${INFORMATIVA}, solo dei dati di chi registra l'azienda (contatti e account), dei dati per le fatture, della prova dei consensi e dei dati per la sicurezza della piattaforma.`,
        "Che dati sono: anagrafiche e recapiti di clienti, proprietari dei veicoli e altri contatti dell'azienda; veicoli, pratiche, rifiuti e formulari; vendite e ordini; account, ruoli e registro delle attività. Di chi sono: clienti, proprietari dei veicoli, altri contatti e dipendenti dell'azienda. Per quanto tempo: per la durata del contratto, più il tempo della restituzione e della cancellazione detto qui sotto.",
        "Ci impegniamo a:",
      ],
      elenco: [
        "trattare i dati solo per fornire il servizio e secondo le istruzioni dell'azienda: queste condizioni e quello che l'azienda fa nel gestionale sono le sue istruzioni. Non li usiamo per altri scopi nostri. Se un'istruzione ci sembra contraria al GDPR lo diciamo subito all'azienda. Se una legge ci obbliga a trattarli in altro modo, lo diciamo prima all'azienda, quando la legge lo permette;",
        `far vedere i dati solo alle persone di ${NOI} autorizzate, per assistenza e manutenzione, e tenute alla riservatezza. Quando entriamo nel gestionale dell'azienda per assistenza, l'accesso resta nel suo registro delle attività;`,
        "proteggere i dati con misure adatte (art. 32): accessi personali con password o PIN e ruoli che limitano cosa vede ognuno; blocchi dopo troppi tentativi sbagliati; collegamenti cifrati tra browser, server e database; database e file raggiungibili solo dal server del gestionale, mai direttamente dal browser; credenziali dei servizi collegati salvate cifrate;",
        "aiutare l'azienda a rispondere alle richieste delle persone sui loro dati (accesso, correzione, cancellazione e le altre del GDPR). Se una richiesta arriva a noi, la passiamo all'azienda;",
        "avvisare l'azienda senza ingiustificato ritardo, all'email di chi ha registrato l'azienda, se scopriamo una violazione dei suoi dati, con le informazioni che le servono per valutarla e, se serve, per notificarla al Garante;",
        "aiutare l'azienda, per la nostra parte, con la sicurezza, la valutazione d'impatto e la consultazione del Garante (artt. 32-36 del GDPR);",
        `alla fine del contratto restituire all'azienda una copia dei dati, se la chiede alla PEC ${PEC}, e poi cancellarli entro 12 mesi dalla fine, tranne quello che la legge ci obbliga a tenere;`,
        "dare all'azienda le informazioni che servono a dimostrare che rispettiamo questo accordo, e permettere controlli, anche ispezioni, da parte sua o di un revisore da lei incaricato, su richiesta scritta alla PEC e con un preavviso ragionevole.",
      ],
      dopo: [
        {
          paragrafi: [
            `L'azienda ci autorizza a usare questi sub-responsabili. Ognuno è vincolato da un contratto con obblighi di protezione dei dati come quelli di questo accordo, e ${NOI} risponde per intero verso l'azienda dei suoi sub-responsabili (art. 28.4 del GDPR):`,
          ],
          elenco: FORNITORI.map(voceFornitore),
        },
        {
          paragrafi: [
            `Se aggiungiamo o cambiamo un sub-responsabile lo diciamo per email almeno 30 giorni prima. L'azienda può opporsi per motivi legati alla protezione dei dati; se non troviamo una soluzione, ${RECESSO_CON_RIMBORSO.replace("prima che valga", "prima che il cambio valga")}.`,
            "Questi servizi invece non sono nostri sub-responsabili: l'azienda li collega con un suo account e su sua istruzione passiamo loro i dati che servono.",
          ],
          elenco: SERVIZI_COLLEGATI.map(voceServizioCollegato),
        },
      ],
    },
];

/**
 * Clausole onerose da approvare in modo specifico (artt. 1341 e 1342 c.c.), con la seconda casella della registrazione
 * (Task 3). `sezione` è l'id della sezione dove sta la clausola.
 */
export const CLAUSOLE_SPECIFICHE: { sezione: string; clausola: string }[] = [
  { sezione: "servizio", clausola: "nessuna nostra responsabilità per i servizi di altri collegati dall'azienda e facoltà di cambiare le funzioni" },
  { sezione: "prova", clausola: "blocco del gestionale alla fine della prova gratuita" },
  { sezione: "abbonamento", clausola: "rinnovo automatico dell'abbonamento e blocco del gestionale se un pagamento non riesce" },
  { sezione: "disdetta", clausola: "disdetta valida solo alla fine del periodo pagato, senza rimborso della parte in corso" },
  { sezione: "disdetta", clausola: "sospensione o chiusura dell'account da parte nostra" },
  { sezione: "disdetta", clausola: "cancellazione dei dati 12 mesi dopo la fine" },
  { sezione: "responsabilita", clausola: "limite della nostra responsabilità e nessuna garanzia che il servizio sia sempre disponibile" },
  { sezione: "modifiche", clausola: "modifiche delle condizioni e dei prezzi decise da noi, con preavviso e diritto di recesso" },
  { sezione: "legge", clausola: "foro di Torino competente in via esclusiva" },
];

const numero = (id: string) => SEZIONI.findIndex((s) => s.id === id) + 1;
const titoloDi = (id: string) => SEZIONI.find((s) => s.id === id)!.titolo;

const CLAUSOLE: Sezione = {
  id: "clausole",
  titolo: "Clausole approvate specificamente (artt. 1341 e 1342 c.c.)",
  paragrafi: [
    "Con la seconda casella della registrazione l'azienda approva in modo specifico, come chiedono gli artt. 1341 e 1342 del Codice civile, queste clausole:",
  ],
  elenco: CLAUSOLE_SPECIFICHE.map(
    (c, i) => `${c.clausola} (punto ${numero(c.sezione)}, «${titoloDi(c.sezione)}»)${i === CLAUSOLE_SPECIFICHE.length - 1 ? "." : ";"}`,
  ),
};

// L'accordo resta l'ultima sezione; le clausole vanno subito prima
export const CONDIZIONI: Documento = {
  titolo: "Condizioni del servizio",
  versione: VERSIONE_CONDIZIONI,
  sezioni: [...SEZIONI.slice(0, -1), CLAUSOLE, SEZIONI.at(-1)!],
};
