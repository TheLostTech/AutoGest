# Periodo RENTRI e accesso consulente — progetto breve

17/11/2026 · prototipo (trasmissione al RENTRI simulata)

## Perché
Oggi l'autodemolizione paga **Ecomatico** solo per tenere il registro di carico e scarico rifiuti, consigliato dalla consulente ambientale. Ogni 30 giorni la consulente entra in Ecomatico, sistema quello che non va e trasmette al RENTRI. Ecomatico è "molto arcaico": ogni auto in ingresso va registrata a mano con una schermata lunga (causale, codice, classi di pericolo, produttore, trasportatore, destinatario, R13…).

Il gestionale ha già quasi tutti questi dati, perché li genera dagli eventi (ingresso, bonifica, formulari). L'obiettivo è **fare a meno di Ecomatico**: la consulente lavora dentro il gestionale, su una sola pagina, una volta al mese.

## Obiettivi
- Ogni movimento del registro nasce da solo e già completo: chi, cosa, quanto, da dove, verso dove.
- La consulente ha un **accesso suo** e una pagina **"Periodo da trasmettere"**: vede il mese, trova evidenziato solo ciò che manca o non torna, corregge, approva, trasmette.
- Le registrazioni numerate non si modificano mai: si rettificano o si annullano con una registrazione nuova.
- Scadenze giuste nella coda Da fare: bozze da completare entro **2 giorni lavorativi**, trasmissione **entro la fine del mese successivo**.

## Non obiettivi (ora)
Collegamento vero alle API RENTRI (resta simulato, ambiente demo RENTRI in Fase 2) · firma digitale dei formulari · emissione dei formulari da parte dell'autodemolizione · lettura del QR del formulario · conservazione a norma · MUD · gestione di più impianti.

## Anti-obiettivi
- Rifare Ecomatico: niente schermate con 40 campi da compilare a mano. Se un dato si può ricavare, si ricava.
- Trasmettere un periodo con errori noti senza che la consulente lo veda.
- Modificare una registrazione già numerata (la legge chiede rettifica o annullamento).

## Vincoli (verificati sulle fonti ufficiali il 17/11/2026)
- **Trasmissione al RENTRI**: "con cadenza mensile, entro la fine del mese successivo a quello in cui è stata effettuata l'annotazione"; se nel mese non ci sono annotazioni "la trasmissione non è dovuta"; i soggetti delegati (art. 18) entro la fine del **secondo** mese successivo. DM 4 aprile 2023 n. 59, art. 15 c. 2 (G.U. n. 126 del 31/5/2023).
- **Annotazione nel registro**: per chi fa operazioni di recupero e smaltimento "entro due giorni lavorativi dalla presa in carico dei rifiuti" (art. 190 c. 3 lett. d D.Lgs. 152/2006, testo in allegato al DM 59/2023).
- **Una registrazione confermata riceve un numero progressivo e "non può essere modificata"**: si corregge solo "con apposita registrazione" di **rettifica** o **annullamento**; le nuove registrazioni non possono avere data precedente all'ultima (Manuale RENTRI gestione registro, v.2, §3.2.1 e §4.2).
- **Veicoli fuori uso**: per gli impianti del D.Lgs. 209/2003 il carico va segnato come "VEICOLI FUORI USO" con **data e numero del certificato di rottamazione** assegnato dal Registro unico telematico (RVFU, D.P.R. 177/2022) (Manuale RENTRI, §3.3.1).
- **Causali per un impianto** (Manuale RENTRI §3.3): carico **\*T ricevuto da terzi**, carico **NP nuovo produttore** (rifiuti generati dal trattamento), scarico **I interno** (richiama il carico), scarico **aT a terzi**. Dati del carico: codice EER, stato fisico, classi di pericolo, peso in kg, attività a destinazione (es. R13).
- **Formulario**: "emesso dal produttore, o dal detentore"; "può essere emesso e compilato a cura del trasportatore, a seguito di richiesta del produttore o del detentore", che resta responsabile delle informazioni di sua competenza (DM 59/2023, art. 5 c. 2-3). È il caso del cliente.
- **Bonifica (messa in sicurezza)**: per legge "entro 10 giorni lavorativi dall'ingresso del veicolo nel centro di raccolta" (art. 6 c. 2 D.Lgs. 209/2003 come modificato dal D.Lgs. 119/2020). Il gestionale oggi avvisa a **7 giorni di calendario**, come indicato dal cliente: da decidere se tenerli come obiettivo interno.
- Dati veri visti in Ecomatico per il cliente: carico auto con 16 01 04*, HP14, stato S, provenienza speciale, produttore = privato che conferisce (con codice fiscale), trasportatore e destinatario = l'autodemolizione (aut. art. 208), operazione R13. Uscita carcasse = formulario 16 01 06 verso centro di recupero (R13), con intermediario.

## Strade valutate
1. **Consulente dentro il gestionale, trasmissione dal gestionale** — scelta dal cliente. Un solo programma, Ecomatico si disdice. Richiede (in Fase 2) il certificato RENTRI dell'azienda o la delega alla consulente.
2. Il gestionale prepara il mese, la consulente scarica un file e lo trasmette col suo strumento — più semplice ma lascia un passaggio a mano. Resta come **riserva**: un riepilogo scaricabile del periodo.

## Cosa si costruisce
1. **Ruolo "Consulente ambientale"**: vede solo l'area Ambiente (registro, periodo, formulari, giacenze). Accesso simulato dal selettore ruolo come gli altri.
2. **Registrazioni complete, che nascono dagli eventi**:
   - ogni registrazione ha numero progressivo (per anno), data di registrazione, data dell'operazione, causale RENTRI (\*T, NP, I, aT), codice EER, stato fisico, classi di pericolo (dal codice), kg, attività a destinazione (R13);
   - carico auto (\*T): spunta "veicoli fuori uso" con **numero e data del certificato di rottamazione** (dalla pratica), produttore = conferente con codice fiscale, peso della pesa;
   - bonifica: scarico **I interno** del veicolo che richiama il suo carico, carichi **NP** delle parti tolte e della carcassa;
   - uscita: scarico **aT** legato al formulario ricevuto.
   - **Bozza → registrata**: se all'evento manca un dato obbligatorio (codice fiscale, certificato di rottamazione, peso della pesa) la registrazione resta in **bozza, senza numero**, con scadenza **2 giorni lavorativi** dalla presa in carico, in Da fare per chi accetta i veicoli. Completata la bozza, riceve il numero e da lì **non si modifica più**.
3. **Pagina "Periodo da trasmettere"** (`/ambiente/periodo`), il lavoro mensile della consulente:
   - mese scelto (di serie: il primo mese non ancora trasmesso), scadenza di trasmissione ben visibile;
   - totali del mese per codice: carichi, scarichi, giacenza a fine mese, confronto con i limiti dell'autorizzazione;
   - elenco delle registrazioni del mese con i **controlli**: bozze ancora aperte (bloccano la trasmissione), formulari senza esito del destinatario, kg accettati diversi, giacenza oltre il limite (avvisi);
   - per correggere: **Rettifica** (nuova registrazione che richiama l'originale, con i dati giusti) o **Annulla** (registrazione di annullamento), entrambe con motivo, chi e quando. Nessuna modifica silenziosa;
   - **"Trasmetti il periodo al RENTRI"** quando non ci sono bozze del mese: ricevuta simulata, mese chiuso;
   - "Scarica riepilogo" del periodo (la riserva della strada 2).
4. **Coda Da fare**: per consulente e responsabile, "Periodo di ottobre da trasmettere entro il 30 novembre" (gialla dall'ultima settimana, rossa se scaduta); la voce di oggi "trasmetti entro 2 giorni" sparisce.
5. **Formulari ricevuti** (aggiunto il 17/11 dopo le foto di un formulario vero, JNMPC 00262 JC):
   - **Il formulario lo compila e lo vidima la ditta che ritira**; l'autodemolizione lo firma. Lo scarico nel registro deve **combaciare** con quel formulario (numero, data, codice, kg, destinatario).
   - **Anagrafica soggetti**, compilata una volta: l'impianto (denominazione, codice fiscale, sede, autorizzazione art. 208), destinatari (autorizzazione, operazione R13), trasportatori (n° Albo), intermediari (n° Albo).
   - "Registra formulario ricevuto": numero del formulario, data di emissione, codice rifiuto (stato fisico e pericolosità si ricavano), kg, "alla rinfusa", destinatario / trasportatore / intermediario scelti dall'anagrafica, targa, conducente, data e ora di inizio trasporto, annotazioni.
   - Con la firma si scrive da solo lo scarico nel registro, legato al numero del formulario.
   - Al ritorno: esito del destinatario (accettato per intero, in parte, respinto), kg accettati, data di arrivo.
   - Controlli nel periodo: scarico verso l'esterno senza formulario; formulario senza esito del destinatario; kg accettati diversi da quelli partiti (avviso); carico respinto (serve una rettifica); numero formulario in un formato insolito (avviso: il formato `AAAAA 00000 AA` è dedotto da un solo esempio).
   - Lo scarico interno della bonifica (veicolo → parti e carcassa) non richiede formulario.
   - In Fase 2 i dati del formulario si potranno scaricare dal RENTRI col numero, invece di ricopiarli.
6. **Dati demo**: un mese passato già trasmesso, il mese scorso da trasmettere con 2–3 problemi da sistemare, il mese corrente aperto.

## Scelte mie (da correggere se serve)
- Periodo = **mese di calendario** (non 30 giorni mobili): lo dice il DM 59/2023.
- Numerazione del registro per anno solare.
- La consulente non crea registrazioni da zero e non modifica quelle registrate: fa rettifiche e annullamenti; le registrazioni nascono dagli eventi.
- Giorni lavorativi = lunedì–venerdì; le festività non sono considerate (da aggiungere).

## Lasciato a chi costruisce
Codici esatti delle causali RENTRI e tracciato del file di riepilogo; come presentare le rettifiche nell'elenco; testi dei controlli.

## Fonti
- DM 4 aprile 2023 n. 59 (G.U. n. 126 del 31/5/2023), artt. 5 e 15 e testo dell'art. 190 D.Lgs. 152/2006 in allegato: copia G.U. https://www.anci.it/wp-content/uploads/Decreto-MASE-n.-59-tracciamento-rifiuti.pdf · Normattiva https://normattiva.it/atto/caricaDettaglioAtto?atto.codiceRedazionale=23G00065&atto.dataPubblicazioneGazzetta=2023-05-31
- Manuale RENTRI "Gestione del Registro cronologico di carico e scarico", versione 2: https://www.rentri.gov.it/default/media/manuali/manuale-gestione-registro-carico-scarico.pdf
- Camera di Commercio di Firenze, "Veicoli fuori uso – adempimenti" (D.Lgs. 119/2020): https://www.fi.camcom.gov.it/sites/default/files/uploads/Registri_Albi_Certificazioni/Ambiente/VFU%20E%20ADEMPIMENTI%20focus.pdf
- Camera di Commercio di Bolzano, trasmissione dei dati al RENTRI: https://www.camcom.bz.it/it/servizi/tutela-dellambiente/rentri/registro-di-carico-e-scarico/registro-di-carico-e-scarico-digitale-trasmissione-dei-dati-al-rentri
