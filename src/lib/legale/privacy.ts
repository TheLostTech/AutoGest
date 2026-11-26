// Informativa privacy di Piazzale (/privacy), a nome di LOSTAR S.R.L.S. Piano 3, Task 1.
// Testo puro: i dati dell'azienda vengono da PRODUTTORE, la versione da consensi.ts (è quella salvata con il consenso).
import { PRODUTTORE } from "../config.ts";
import { VERSIONE_PRIVACY } from "../consensi.ts";
import { FORNITORI, type Documento, type Fornitore } from "./comune.ts";

const PEC = `[${PRODUTTORE.pec}](mailto:${PRODUTTORE.pec})`;

function voceFornitore(f: Fornitore): string {
  const chi = f.soloSe ? `${f.nome}, solo se ${f.soloSe}` : f.nome;
  return `${chi}: ${f.cosa}. Dove: ${f.dove}. Garanzia: ${f.garanzia}.`;
}

export const INFORMATIVA_PRIVACY: Documento = {
  titolo: "Informativa privacy",
  versione: VERSIONE_PRIVACY,
  sezioni: [
    {
      id: "titolare",
      titolo: "Chi tratta i dati",
      paragrafi: [
        `Questa pagina spiega come trattiamo i dati personali di chi usa Piazzale, il gestionale per autodemolizioni di ${PRODUTTORE.nome}.`,
        `Il titolare del trattamento è ${PRODUTTORE.ragioneSociale}, ${PRODUTTORE.sede}, P. IVA e C.F. ${PRODUTTORE.piva}, REA ${PRODUTTORE.rea}.`,
        `Per ogni domanda o richiesta sui tuoi dati scrivi alla PEC ${PEC}.`,
        "Piazzale è un servizio per imprese. Questa informativa riguarda le persone che lo usano per conto della loro azienda: chi registra l'autodemolizione e i dipendenti che accedono.",
      ],
    },
    {
      id: "dati",
      titolo: "Quali dati trattiamo",
      paragrafi: [
        "Trattiamo come titolari i dati delle persone che usano Piazzale. I dati che l'autodemolizione inserisce nel gestionale sul suo lavoro (clienti, veicoli, pratiche, formulari, vendite) sono invece dell'azienda: per quei dati il titolare è l'autodemolizione e noi siamo responsabili del trattamento. Li trattiamo solo per far funzionare il servizio e secondo le sue istruzioni, con le regole dell'[accordo sul trattamento dei dati](/condizioni#accordo) che fa parte delle condizioni del servizio.",
        "Come titolari trattiamo questi dati:",
      ],
      elenco: [
        "Di chi registra l'azienda: nome e cognome, email, telefono (facoltativo) e nome dell'azienda. La password non la conosciamo: salviamo solo una sua impronta (hash), da cui non si risale alla password.",
        "Dei dipendenti che accedono: nome, email oppure PIN (anche il PIN solo come impronta) e i ruoli che l'azienda assegna.",
        "Dati tecnici: indirizzo IP, dispositivo e browser usati, registro delle attività nel gestionale (chi ha fatto cosa e quando).",
        "Prova dei consensi: quando accetti le condizioni, questa informativa o le proposte commerciali salviamo data, ora, indirizzo IP e versione del testo.",
        "Se l'azienda si abbona: i dati per la fattura. I dati della carta li inserisci sulla pagina di Stripe: noi non li vediamo.",
      ],
    },
    {
      id: "finalita",
      titolo: "Perché li trattiamo e su quale base",
      paragrafi: [
        "Senza i dati dell'account non possiamo attivare il servizio. Il consenso alle proposte commerciali invece è libero: senza, Piazzale funziona lo stesso.",
        "Usiamo i dati solo per questi scopi, ognuno con la sua base giuridica:",
      ],
      elenco: [
        "Creare e gestire l'account, far partire la prova gratuita, attivare e gestire l'abbonamento, dare assistenza: serve per il contratto e per i passi prima del contratto (art. 6.1.b del GDPR).",
        "Le email della prova (conferma dell'indirizzo, avviso che la prova sta per scadere, fine della prova) sono comunicazioni di servizio: fanno parte del contratto e arrivano anche senza il consenso alle proposte commerciali.",
        "Fare le fatture e tenere la contabilità: è un obbligo di legge (art. 6.1.c).",
        "Proteggere il servizio: bloccare i tentativi di accesso ripetuti, fermare le registrazioni automatiche con BotID, tenere il registro delle attività per ricostruire cosa è successo. È un nostro legittimo interesse, e anche dell'azienda che usa il gestionale (art. 6.1.f).",
        "Mandarti proposte commerciali di Lostar su Piazzale, come novità e offerte: solo con il tuo consenso (art. 6.1.a). È facoltativo e puoi revocarlo in ogni momento scrivendo alla PEC. La revoca vale da quel momento in poi.",
      ],
    },
    {
      id: "conservazione",
      titolo: "Per quanto tempo li teniamo",
      paragrafi: ["Teniamo i dati solo per il tempo che serve:"],
      elenco: [
        "Account e dati dell'azienda: per tutta la durata del contratto.",
        "Registrazioni mai confermate e prove finite senza abbonamento: fino a 12 mesi, poi li cancelliamo.",
        "Dati delle fatture e prova dei consensi: 10 anni, il tempo che la legge chiede per le scritture contabili e per far valere i propri diritti.",
        "Contatti per le proposte commerciali: fino alla revoca del consenso, e comunque non oltre 24 mesi dall'ultimo contatto.",
        "Log tecnici dei fornitori, come i registri delle richieste al server: pochi giorni.",
      ],
    },
    {
      id: "fornitori",
      titolo: "Chi può riceverli",
      paragrafi: [
        `Vedono i dati le persone di ${PRODUTTORE.ragioneSociale} autorizzate, per assistenza e manutenzione, e le autorità quando la legge lo chiede. Dentro l'azienda ogni persona vede solo quello che i suoi ruoli permettono.`,
        "Stripe ed eBay trattano alcuni dati anche come titolari autonomi, secondo le loro informative.",
        "Per far funzionare Piazzale usiamo questi fornitori. Chi tratta dati per conto nostro lo fa con un accordo sul trattamento dei dati (art. 28 del GDPR) e solo per il servizio che ci rende:",
      ],
      elenco: FORNITORI.map(voceFornitore),
    },
    {
      id: "trasferimenti",
      titolo: "Dati fuori dall'Unione europea",
      paragrafi: [
        "Il database e i file del gestionale restano su server nell'Unione europea.",
        "Alcuni fornitori (hosting, email, pagamenti, eBay) hanno sede o server negli Stati Uniti. In quei casi il trasferimento si basa su una decisione di adeguatezza della Commissione europea (EU-US Data Privacy Framework) o sulle clausole contrattuali standard, come prevedono gli artt. 44 e seguenti del GDPR.",
        "Puoi chiedere alla PEC quali garanzie usiamo per ogni fornitore.",
      ],
    },
    {
      id: "diritti",
      titolo: "I tuoi diritti",
      paragrafi: [
        `Per usare i tuoi diritti scrivi alla PEC ${PEC}. Ti rispondiamo entro un mese.`,
        "Per i dati che l'autodemolizione inserisce sui suoi clienti la richiesta va fatta all'azienda, che ne è titolare. Noi la aiutiamo a rispondere.",
        "Se pensi che trattiamo i tuoi dati in modo non corretto puoi fare reclamo al Garante per la protezione dei dati personali ([garanteprivacy.it](https://www.garanteprivacy.it)).",
        "Sui tuoi dati hai diritto di:",
      ],
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
    },
    {
      id: "cookie",
      titolo: "Cookie",
      paragrafi: [
        "Piazzale usa solo cookie tecnici, che servono a farlo funzionare. Non usiamo cookie pubblicitari né analitici, nostri o di altri. I cookie tecnici non richiedono il consenso: per questo non c'è un banner.",
        "Sul modulo di registrazione BotID di Vercel analizza alcuni segnali tecnici del browser, per capire se a compilarlo è una persona o un programma automatico. Lo usiamo solo per fermare le registrazioni automatiche.",
        "I cookie tecnici che usiamo sono questi:",
      ],
      elenco: [
        "sessione dell'accesso, per restare dentro senza rifare il login a ogni pagina;",
        "identificativo del dispositivo, per riconoscere il telefono o il tablet condiviso su cui i dipendenti entrano con il PIN;",
        "preferenze, per ricordare le scelte fatte nel gestionale.",
      ],
    },
    {
      id: "modifiche",
      titolo: "Modifiche",
      paragrafi: [
        "Se cambiamo questa informativa aggiorniamo la data della versione in cima alla pagina.",
        "Con ogni consenso salviamo la versione del testo che hai letto, così resta chiaro cosa hai accettato e quando.",
      ],
    },
  ],
};
