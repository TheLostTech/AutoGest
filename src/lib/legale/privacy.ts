// Informativa privacy di Piazzale (/privacy), a nome di LOSTAR S.R.L.S. Piano 3, Task 1.
// Testo puro: nomi e dati dell'azienda vengono da BRAND e PRODUTTORE, la versione da consensi.ts (è quella salvata con
// il consenso). Ruoli (decisione del coordinatore, 26/11/2026): siamo titolari solo per chi registra l'azienda, fatture,
// consensi e sicurezza della piattaforma; account dei dipendenti, registro delle attività e dati di lavoro sono
// dell'azienda e li trattiamo come responsabili (accordo in /condizioni#accordo).
import { BRAND, PRODUTTORE } from "../config.ts";
import { VERSIONE_PRIVACY } from "../consensi.ts";
import { FORNITORI, SERVIZI_COLLEGATI, type Documento, type Fornitore } from "./comune.ts";

const PEC = `[${PRODUTTORE.pec}](mailto:${PRODUTTORE.pec})`;
const ACCORDO = "[accordo sul trattamento dei dati](/condizioni#accordo)";
const NOI = PRODUTTORE.ragioneSociale;

const voceFornitore = (f: Fornitore) => `${f.nome}: ${f.cosa}. Dove: ${f.dove}. Garanzia: ${f.garanzia}.`;
const voceCollegato = (f: Fornitore) => `${f.nome}, solo se ${f.soloSe}: ${f.cosa}. È ${f.garanzia}; dove tratta i dati è ${f.dove}.`;

export const INFORMATIVA_PRIVACY: Documento = {
  titolo: "Informativa privacy",
  versione: VERSIONE_PRIVACY,
  sezioni: [
    {
      id: "titolare",
      titolo: "Chi tratta i dati",
      paragrafi: [
        `Questa pagina spiega come trattiamo i dati personali di chi usa ${BRAND.azienda}, il gestionale per autodemolizioni di ${PRODUTTORE.nome}.`,
        `Il titolare del trattamento è ${NOI}, ${PRODUTTORE.sede}, P. IVA e C.F. ${PRODUTTORE.piva}, REA ${PRODUTTORE.rea}.`,
        `Per ogni domanda o richiesta sui tuoi dati scrivi alla PEC ${PEC}.`,
        `${BRAND.azienda} è un servizio per imprese. Questa informativa riguarda chi registra l'autodemolizione e, per la sicurezza degli accessi, chiunque entri nel gestionale, dipendenti compresi.`,
      ],
    },
    {
      id: "dati",
      titolo: "Quali dati trattiamo",
      paragrafi: ["Come titolari trattiamo solo questi dati:"],
      elenco: [
        "Di chi registra l'azienda: nome e cognome, email, telefono (facoltativo), nome dell'azienda e password. Della password salviamo solo una sua impronta (hash), da cui non si risale alla password.",
        "Prova dei consensi: quando accetti le condizioni, quando dichiari di aver letto questa informativa e quando dai il consenso alle proposte commerciali salviamo data, ora, indirizzo IP e versione del testo.",
        "Dati per la fattura, se l'azienda si abbona. I dati della carta li inserisci sulla pagina di Stripe: noi non li vediamo.",
        "Dati per la sicurezza della piattaforma, di chiunque accede: tentativi di accesso sbagliati e blocchi, indirizzo IP, dispositivo e browser, segnali tecnici raccolti da BotID sul modulo di registrazione, log tecnici dei server.",
      ],
      dopo: [
        {
          paragrafi: [
            "Questi dati li raccogliamo quasi sempre da te. I dati per la fattura ci arrivano da Stripe, dove li inserisci al pagamento. Se sei un dipendente, il tuo account lo crea l'azienda: come titolari ne usiamo solo i dati di sicurezza degli accessi (art. 14 del GDPR).",
            `Tutti gli altri dati sono dell'autodemolizione, che ne è titolare: gli account dei dipendenti (nome, email o PIN, ruoli), il registro delle attività (chi ha fatto cosa e quando) e i dati che inserisce sul suo lavoro (clienti, veicoli, pratiche, formulari, vendite). Per questi dati ${NOI} è responsabile del trattamento: li tratta solo per far funzionare il servizio e secondo le istruzioni dell'azienda, con le regole dell'${ACCORDO} che fa parte delle condizioni del servizio.`,
          ],
        },
      ],
    },
    {
      id: "finalita",
      titolo: "Perché li trattiamo e su quale base",
      paragrafi: ["Usiamo i dati di cui siamo titolari solo per questi scopi, ognuno con la sua base giuridica:"],
      elenco: [
        "Creare e gestire l'account di chi registra l'azienda, far partire la prova gratuita, attivare e gestire l'abbonamento, dare assistenza. Se sei tu stesso parte del contratto (per esempio hai una ditta individuale) la base è il contratto e i passi prima del contratto (art. 6.1.b del GDPR). Altrimenti è il legittimo interesse, nostro e dell'azienda, a fornire il servizio che l'azienda ha chiesto (art. 6.1.f).",
        "Le email della prova (conferma dell'indirizzo, avviso che la prova sta per scadere, fine della prova) sono comunicazioni di servizio, con la stessa base: arrivano anche senza il consenso alle proposte commerciali.",
        "Fare le fatture e tenere la contabilità: è un obbligo di legge (art. 6.1.c).",
        "Proteggere la piattaforma: bloccare i tentativi di accesso ripetuti, fermare con BotID le registrazioni che sembrano automatiche, tenere i log tecnici per capire un guasto o un attacco. È un nostro legittimo interesse (art. 6.1.f).",
        `Mandarti proposte commerciali di ${PRODUTTORE.nome} su ${BRAND.azienda}, come novità e offerte: solo con il tuo consenso (art. 6.1.a). È facoltativo e puoi revocarlo in ogni momento scrivendo alla PEC. La revoca vale da quel momento in poi.`,
      ],
      dopo: [
        {
          paragrafi: [
            `Senza i dati dell'account non possiamo attivare il servizio. Il consenso alle proposte commerciali invece è libero: senza, ${BRAND.azienda} funziona lo stesso.`,
            "Gli account dei dipendenti, il registro delle attività e gli altri dati dell'azienda li trattiamo solo per conto dell'azienda: scopi e base giuridica li decide lei, come titolare.",
          ],
        },
      ],
    },
    {
      id: "conservazione",
      titolo: "Per quanto tempo li teniamo",
      paragrafi: ["Teniamo i dati solo per il tempo che serve:"],
      elenco: [
        "Dati di chi registra l'azienda: per tutta la durata del contratto.",
        "Registrazioni mai confermate e prove finite senza abbonamento: fino a 12 mesi, poi li cancelliamo.",
        "Dati delle fatture e prova dei consensi: 10 anni, il tempo che la legge chiede per le scritture contabili e per far valere i propri diritti.",
        "Contatti per le proposte commerciali: fino alla revoca del consenso, e comunque non oltre 24 mesi dall'ultimo contatto.",
        "Conteggi dei tentativi di accesso sbagliati: pochi minuti. Log tecnici dei fornitori: pochi giorni.",
      ],
      dopo: [{ paragrafi: [`I dati di cui è titolare l'azienda si tengono e si cancellano come dice l'${ACCORDO}.`] }],
    },
    {
      id: "fornitori",
      titolo: "Chi può riceverli",
      paragrafi: [
        `Vedono i dati le persone di ${NOI} autorizzate, per assistenza e manutenzione, e le autorità quando la legge lo chiede. Dentro l'azienda ogni persona vede solo quello che i suoi ruoli permettono.`,
        `Per far funzionare ${BRAND.azienda} usiamo questi fornitori. Trattano i dati per conto nostro, con un accordo sul trattamento dei dati (art. 28 del GDPR), e solo per il servizio che ci rendono; per i dati dell'azienda sono sub-responsabili:`,
      ],
      elenco: FORNITORI.map(voceFornitore),
      dopo: [
        {
          paragrafi: [
            "Se l'azienda collega un suo account a uno di questi servizi, su sua istruzione passiamo al servizio i dati che servono. Non sono nostri fornitori: ognuno tratta i dati come titolare autonomo.",
          ],
          elenco: SERVIZI_COLLEGATI.map(voceCollegato),
        },
      ],
    },
    {
      id: "trasferimenti",
      titolo: "Dati fuori dall'Unione europea",
      paragrafi: [
        "Il database e i file sono salvati su server nell'Unione europea (Francoforte); il gestionale li elabora su server di Vercel negli Stati Uniti.",
        "Alcuni fornitori (elaborazione del gestionale, email, pagamenti) hanno sede o server negli Stati Uniti. In quei casi il trasferimento si basa su una decisione di adeguatezza della Commissione europea (EU-US Data Privacy Framework) o sulle clausole contrattuali standard, come prevedono gli artt. 44 e seguenti del GDPR.",
        "Puoi chiedere alla PEC quali garanzie usiamo per ogni fornitore.",
      ],
    },
    {
      id: "diritti",
      titolo: "I tuoi diritti",
      paragrafi: ["Sui dati di cui siamo titolari hai diritto di:"],
      elenco: [
        "sapere se trattiamo tuoi dati e averne una copia (art. 15 del GDPR);",
        "farli correggere o completare (art. 16);",
        "farli cancellare, quando non servono più o manca una base per tenerli (art. 17);",
        "chiedere di limitarne l'uso (art. 18);",
        "riceverli in un formato leggibile da un computer, per portarli altrove (art. 20);",
        "opporti al trattamento basato sul legittimo interesse (art. 21);",
        "non essere sottoposto a decisioni prese solo in modo automatico che hanno effetti giuridici su di te o ti toccano in modo simile (art. 22);",
        "revocare in ogni momento il consenso alle proposte commerciali, senza toccare quello che è stato fatto prima (art. 7).",
      ],
      dopo: [
        {
          paragrafi: [
            `Per usarli scrivi alla PEC ${PEC}. Ti rispondiamo entro un mese.`,
            "Non prendiamo decisioni solo automatiche con effetti giuridici su di te. BotID può fermare una registrazione che sembra fatta da un programma: se è successo a te, scrivi alla PEC e la controlla una persona (art. 22).",
            "Per i dati di cui è titolare l'azienda (account dei dipendenti, registro delle attività, dati dei clienti) la richiesta va fatta all'azienda. Noi la aiutiamo a rispondere.",
            "Se pensi che trattiamo i tuoi dati in modo non corretto puoi fare reclamo al Garante per la protezione dei dati personali ([garanteprivacy.it](https://www.garanteprivacy.it)).",
          ],
        },
      ],
    },
    {
      id: "cookie",
      titolo: "Cookie e memoria del browser",
      paragrafi: ["Usiamo solo due cookie, tutti e due tecnici:"],
      elenco: [
        "sessione dell'accesso, per restare dentro senza rifare il login a ogni pagina;",
        "dispositivo, per riconoscere il telefono o il tablet condiviso su cui i dipendenti entrano con il PIN.",
      ],
      dopo: [
        {
          paragrafi: ["Dopo l'accesso il gestionale tiene anche alcune cose nella memoria del browser (localStorage):"],
          elenco: [
            "una copia dell'archivio dell'azienda, con le impostazioni del gestionale, per lavorare veloce anche quando la rete va e viene. Quando nello stesso browser entri in un'altra azienda, la copia della precedente si cancella;",
            "le modifiche non ancora inviate al server, finché non partono; quelle rimaste indietro si scartano dopo 24 ore;",
            "l'azienda aperta e l'ora dell'ultimo utilizzo, per chiudere l'accesso dopo un periodo di inattività.",
          ],
        },
        {
          paragrafi: [
            "Sono tutti strumenti tecnici, che servono a far funzionare il servizio: non richiedono il consenso, per questo non c'è un banner. Non usiamo cookie pubblicitari né analitici, nostri o di altri.",
            "Sul modulo di registrazione BotID di Vercel analizza alcuni segnali tecnici del browser, per capire se a compilarlo è una persona o un programma automatico. Lo usiamo solo per fermare le registrazioni automatiche.",
          ],
        },
      ],
    },
    {
      id: "modifiche",
      titolo: "Modifiche",
      paragrafi: [
        "Se cambiamo questa informativa aggiorniamo la data della versione in cima alla pagina.",
        "Con ogni consenso salviamo la versione del testo, così resta chiaro quale testo hai letto o accettato e quando.",
      ],
    },
  ],
};
