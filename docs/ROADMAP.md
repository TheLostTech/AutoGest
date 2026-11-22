# Roadmap del prodotto

Il prototipo diventa un prodotto da vendere ad altre autodemolizioni. Obiettivo: coprire tutto quello che offrono i gestionali di settore (riferimento: GestCAR di Ecodat, Systema Ecoeuro, Cobat Cyclus), compresa la parte normativa, ma con un'esperienza d'uso moderna e ordinata.

Data: 16 novembre 2026. Stato: proposta da validare.

**Già nel prototipo (in forma dimostrativa, servizi esterni simulati):** H1 coda "Da fare", H2 ricerca globale, H4 navigazione per aree con moduli attivabili (Magazzino base + Accettazione, Ambiente, Vendite; spec `docs/superpowers/specs/2026-11-19-moduli-a-pagamento-design.md`); C1–C2 conferente e documenti, C4 visura con fermo, C6 presa in carico e certificato, C8 radiazione, C9 fascicolo, C10 peso in ingresso; D1–D3 bonifica e registro automatico, D4 trasmissione RENTRI, D5–D7 formulari e uscite, D8 limiti dell'autorizzazione; E4 prezzo del nuovo e suggerito, E5 listini, E9 inventario a rotazione (con creazione magazzini e provenienza da pratiche passate), B7 inventario di avvio; F2 preventivi, F3 scontrino o fattura al banco, F6 nota di credito sul reso; G1 documenti.

---

## 1. Come restiamo sobri pur facendo tutto

I gestionali di settore espongono ogni modulo come una voce di menu: registri, formulari, MUD, fatture, pratiche, visure. Il risultato è un "mappazzone" dove l'utente deve sapere dove andare e cosa compilare. Noi ribaltiamo l'approccio.

### Principi

1. **I registri si scrivono da soli.** L'operatore registra fatti operativi (veicolo arrivato, bonifica fatta, rottame caricato sul camion, pezzo venduto). Registro rifiuti, fascicolo veicolo, documenti fiscali e dichiarazioni annuali sono *conseguenze* di quei fatti. L'ufficio controlla e conferma, non ricopia.
2. **Si lavora da una coda, non da un menu.** "Oggi" raccoglie tutto ciò che va fatto con la sua scadenza: radiazioni in scadenza, formulari da firmare, registri da trasmettere, limiti dell'autorizzazione vicini, ordini da spedire. Ogni voce porta direttamente all'azione.
3. **Al massimo sei aree.** Ogni funzione nuova entra in un'area esistente, non apre una voce di menu nuova.
4. **Dettaglio a richiesta.** Liste pulite; i dati completi stanno in schede laterali (come la scheda ricambio nelle vendite) e nelle pagine di dettaglio.
5. **Ognuno vede il suo lavoro.** Smontatore, piazzale, magazzino, banco e ufficio hanno viste diverse. I moduli non acquistati compaiono bloccati, con la spiegazione e la richiesta d'attivazione.
6. **Una ricerca per tutto.** Una sola barra trova targa, telaio, ID veicolo, ID ricambio, codice OE, vecchio codice, cliente, pratica, formulario, fattura.
7. **Telefono per il campo, computer per l'ufficio.** Stessi componenti e stesso linguaggio visivo (DESIGN.md).

### Struttura delle aree

| Area | Cosa contiene | Chi la usa |
|---|---|---|
| **Oggi** | Coda "Da fare" con scadenze, attività del giorno, indicatori essenziali | Tutti, ognuno con la sua coda |
| **Veicoli** | Ingresso, pratica, documenti, radiazione, bonifica, smontaggio, deposito giudiziario | Accettazione, piazzale, smontatori, ufficio |
| **Ricambi** | Magazzino, ubicazioni, inventario, catalogo, pubblicazione | Magazzino, smontatori |
| **Vendite** | Banco, preventivi, ordini, clienti, canali online, spedizioni, resi | Banco, ufficio |
| **Ambiente** | Registro rifiuti, formulari, uscite materiali, limiti dell'autorizzazione, dichiarazioni annuali | Ufficio, responsabile |
| **Ufficio** | Documenti fiscali, scadenziario, prima nota, report, impostazioni | Ufficio, titolare |

Su telefono la barra in basso mostra le 3–4 voci del ruolo (es. smontatore: Smontaggio, Scansiona, Ricambi; piazzale: Ingressi, Bonifica, Scansiona).

---

## 2. Macro gruppi e task

Legenda:
- **Dimensione:** S = giorni, M = 1–3 settimane, L = oltre 3 settimane.
- **Esterno:** serve un accordo, una licenza o un'abilitazione presso un ente o un fornitore.
- 🔁 = già presente nel prototipo in forma simulata, da rendere reale.

L'ordine dei gruppi è l'ordine consigliato: i primi sono prerequisiti dei successivi. L'Industria 4.0 è l'ultimo gruppo, da avviare dopo il censimento dei macchinari del cliente.

### A. Fondamenta del prodotto

Senza questo il prodotto non si può vendere: oggi il prototipo salva i dati solo nel browser.

| ID | Task | Dim. | Note |
|---|---|---|---|
| A1 | Database centrale e API documentate (sostituisce il salvataggio locale) | L | Base di tutto |
| A2 | Più aziende sulla stessa piattaforma, dati separati per azienda | M | In parte fatto (18 nov 2026): ogni azienda ha archivio, foto, collegamenti e richieste in una cartella propria e l'azienda si ricava sempre dalla sessione. Resta: database vero al posto dei file, più sedi (A3) |
| A3 | Più sedi e più magazzini per azienda | M | |
| A4 | Accesso utenti, ruoli e permessi configurabili | M | In parte fatto (18 nov 2026): login con Better Auth, ruoli combinabili, accesso nome+PIN sui dispositivi condivisi, blocco dopo 5 minuti. **Limite noto:** Il server controlla l'accesso, la separazione tra aziende e, per ruolo, alcune azioni delicate (collegamenti, collegamento e politiche eBay, richiesta della visura PRA, ripristino dei dati, gestione dei dispositivi, Piattaforma); tutto il resto è limitato per ruolo solo nelle schermate fino al database dei dati (A1). Il pagamento del negozio è simulato solo nell'azienda demo |
| A5 | Registro attività immutabile (chi, cosa, quando, da quale dispositivo) | M | 🔁 |
| A6 | App per il campo che funziona anche senza rete e sincronizza al ritorno | L | Piazzali con copertura scarsa |
| A7 | Stampa etichette su stampanti reali (Bluetooth, Wi-Fi, USB) | M | Esterno: modelli di stampante; 🔁 |
| A8 | Archivio documenti e foto con conservazione a norma | M | Esterno: fornitore di conservazione |
| A9 | Firma dei documenti: firma su tablet del cliente e firma digitale dell'impianto | M | Esterno: fornitore di firma |
| A10 | Backup, ripristino, monitoraggio, gestione errori delle integrazioni con nuovi tentativi | M | |
| A11 | Privacy (GDPR): informative, tempi di conservazione, esportazione e cancellazione dati | S | Con consulente |
| A12 | Abbonamenti dei nostri clienti: piani, moduli attivabili, fatturazione del servizio | M | In parte fatto (22 nov 2026, ramo `registrazione-pagamento`): registrazione con codice invito, abbonamento per azienda con Stripe (solo sandbox di prova), moduli accesi dal pagamento, blocco a scadenza con dati visibili. Vedi `docs/PAGAMENTI.md`. Mancano: chiavi live, fattura elettronica verso lo SDI, email, periodo di prova a tempo |
| A13 | Pannello interno per noi: attivazione clienti, supporto, stato delle integrazioni | M | In parte fatto (18 nov 2026): area Piattaforma per il super admin (codice dal telefono obbligatorio) con creazione aziende, utenti con richiesta scritta, dispositivi e ingresso di assistenza (2 ore, con motivo e riga nel registro dell'azienda). Mancano: stato delle integrazioni (attivazione e piani: vedi A12) |

### B. Avvio di un nuovo cliente e migrazione

Ogni cliente arriva da un altro gestionale: se non importiamo i suoi dati, non cambia software.

| ID | Task | Dim. | Note |
|---|---|---|---|
| B1 | Importazione guidata da Excel/CSV con abbinamento delle colonne e anteprima | M | |
| B2 | Importatori pronti per i gestionali più diffusi (es. GestCAR, Ecoeuro) | M | Esterno: formati di esportazione |
| B3 | Conservazione dei vecchi codici (es. K000KRJ01) e ricerca anche per vecchio codice | S | 🔁 |
| B4 | Importazione delle ubicazioni esistenti nel formato del cliente (Mag/Corsia, Scaffale, Ripiano, Contenitore) | S | 🔁 formato già gestito |
| B5 | Controllo duplicati e dati mancanti dopo l'import, con lista di cose da sistemare | M | |
| B6 | Configurazione iniziale guidata: dati azienda, autorizzazione, magazzini, utenti, stampanti, listini | M | |
| B7 | Inventario di avvio: campagna di etichettatura con avanzamento (pilota su 50–100 pezzi) | M | Dalla specifica |

### C. Ingresso veicolo e pratica di demolizione

Area **Veicoli**. Oggi il prototipo copre targa, telaio, dati tecnici e numero pratica.

| ID | Task | Dim. | Note |
|---|---|---|---|
| C1 | Anagrafica di chi conferisce il veicolo (privato, concessionaria, assicurazione, ente) | S | |
| C2 | Documenti in ingresso: carta di circolazione, certificato di proprietà, documento d'identità, targhe consegnate; lista di controllo per tipo di conferimento | M | |
| C3 | Lettura automatica dei documenti dalla foto (carta di circolazione, documento d'identità) | M | 🔁 oggi solo la targa |
| C4 | Visura al registro automobilistico (PRA) per targa o telaio, con verifica del fermo amministrativo che blocca la presa in carico | M | Esterno: servizio ACI tramite intermediario |
| C5 | Dati tecnici reali da targa e telaio, con allestimento esatto | M | Esterno: banca dati veicoli; 🔁 |
| C6 | Presa in carico e certificato di rottamazione generato, firmato e stampato | M | Esterno: modelli ufficiali da verificare |
| C7 | Collegamento al Registro Unico Telematico e al portale ministeriale: ricevuta di presa in carico digitale e fascicolo digitale del veicolo | L | Esterno: abilitazione e documentazione tecnica |
| C8 | Radiazione: stato della pratica, scadenza, esito, aggiornamento automatico degli estremi; invio tramite agenzia partner o sportello telematico | L | Esterno: agenzia o sportello abilitato |
| C9 | Fascicolo veicolo: tutti i documenti, le foto e la cronologia in un'unica scheda | S | 🔁 in parte |
| C10 | Peso del veicolo in ingresso (manuale ora, dalla bilancia con il gruppo I) | S | Alimenta il registro rifiuti |
| C11 | Ritiri programmati: calendario, carro attrezzi, indirizzo, conferma al cliente | M | |
| C12 | Deposito giudiziario: veicoli in custodia, giorni, tariffe, autorità di riferimento, rilascio o rottamazione | M | Modulo separato attivabile |
| C13 | Rottamazione per conto terzi (concessionarie): pratiche raggruppate e fatturazione cumulativa | S | Collegato a F3 |

### D. Bonifica e ambiente

Area **Ambiente**, con la bonifica dentro la scheda del veicolo. Qui vale il principio "i registri si scrivono da soli".

| ID | Task | Dim. | Note |
|---|---|---|---|
| D1 | Scheda di bonifica per veicolo: carburante, oli, liquido freni, antigelo, gas del climatizzatore, batteria, filtri, airbag, catalizzatore, pneumatici; quantità e operatore | M | Pensata per il telefono |
| D2 | Codici rifiuto (EER) precompilati per ogni voce di bonifica e di smontaggio, configurabili dall'impianto | S | |
| D3 | Registro di carico e scarico generato dagli eventi: ingresso veicolo, bonifica, smontaggio, uscita materiali | L | Il cuore della parte ambientale |
| D4 | Collegamento al RENTRI: invio dei registri, controlli di coerenza e completezza prima dell'invio, gestione degli esiti | L | Esterno: credenziali e accreditamento |
| D5 | Formulari digitali (xFIR): creazione, firma dal gestionale, trasmissione, quarta copia; formulari cartacei dove ancora servono | L | Esterno: RENTRI |
| D6 | Uscite di materiale: carcasse pressate, rottame, catalizzatori, batterie, verso destinatari e trasportatori in anagrafica | M | Genera formulario e scarico |
| D7 | Anagrafica di trasportatori e destinatari con autorizzazioni e scadenze | S | |
| D8 | Limiti dell'autorizzazione in tempo reale: giacenze per codice rifiuto rispetto ai massimi, avvisi prima del superamento | M | Va nella coda "Da fare" |
| D9 | Percentuali di reimpiego e recupero per veicolo e per anno | M | Utile anche in vendita |
| D10 | Dichiarazione annuale MUD (rifiuti, veicoli fuori uso, intermediazione, apparecchiature elettriche) generata dai dati dell'anno | M | |
| D11 | Esportazioni per COBAT, osservatorio regionale (O.R.S.O.) e UNRAE | M | Esterno: tracciati |
| D12 | Archiviazione a norma dei registri e dei formulari trasmessi | S | Usa A8 |

### E. Magazzino ricambi evoluto

Area **Ricambi**. Il prototipo ha già: provenienza ereditata, ubicazioni gerarchiche, mappa del magazzino, etichette con QR, ricambi da recuperare confrontati con le scorte, controlli prima della pubblicazione.

| ID | Task | Dim. | Note |
|---|---|---|---|
| E1 | Banca dati ricambi reale: codice OE, costruttore, compatibilità tra veicoli | L | Esterno: licenza (es. TecDoc o Collins-Kromeda); 🔁 |
| E2 | Codici OE sostituiti ed equivalenti aftermarket, per la ricerca | M | Da E1 |
| E3 | Esploso grafico del veicolo per individuare il pezzo, consultabile anche durante lo smontaggio | M | Da E1 |
| E4 | Prezzo del ricambio nuovo durante la catalogazione e prezzo suggerito dell'usato (in base a condizioni e giacenza) | M | Esterno: listini |
| E5 | Listini multipli per ricambio, ad esempio le fasce L/T/B/2/3/4 del gestionale attuale del cliente | S | Significato delle fasce da chiarire |
| E6 | Foto migliorate in automatico: ritaglio, sfondo neutro, luce; numero minimo di foto per pubblicare | M | Esterno: servizio di elaborazione immagini |
| E7 | Riconoscimento del pezzo dalla foto reso reale | M | 🔁 |
| E8 | Schede di smontaggio personalizzabili per categoria (campi obbligatori, foto richieste) | M | |
| E9 | Inventario a rotazione: scansione di uno scaffale alla volta, differenze evidenziate, rettifiche tracciate | M | |
| E10 | Movimenti tra ubicazioni, sedi e magazzini con scansione | S | 🔁 in parte |
| E11 | Ricambi fermi da tempo: giacenza per età, proposte di ribasso o di smaltimento | S | |
| E12 | Regole di vendibilità per categoria (es. componenti di sicurezza con vincoli di vendita) | S | Da validare con consulente |
| E13 | Richieste di ricambi in arrivo: "ce l'ho?" per targa o codice, con prenotazione del pezzo anche ancora da smontare | M | Utile per officine e ricambisti |
| E14 | Kit e lotti (es. set di cerchi, gruppo motore completo) venduti come un solo articolo | S | |

### F. Vendite e canali

Area **Vendite**. Il prototipo ha già: vendita al banco, riserva unica tra canali, negozio online, prova di doppia vendita, scheda dettaglio del ricambio.

| ID | Task | Dim. | Note |
|---|---|---|---|
| F1 | Anagrafica clienti privati e aziende, con listino e condizioni dedicate | S | |
| F2 | Preventivi trasformabili in ordine con un tocco | S | |
| F3 | Vendita al banco con documento commerciale (registratore telematico) o fattura | M | Esterno: registratore o servizio di corrispettivi |
| F4 | Pagamenti reali online e al banco (POS) | M | Esterno: fornitore di pagamenti; 🔁 |
| F5 | Spedizioni: tariffe, etichetta del corriere, tracciamento, imballo suggerito per categoria | M | Esterno: corrieri o aggregatore |
| F6 | Resi e garanzia: motivazione, rientro in magazzino, nota di credito | M | 🔁 in parte |
| F7 | Pubblicazione su più marketplace con un tocco e giacenza sincronizzata (es. eBay, Ovoko) | L | Esterno: API e accordi; 🔁 simulata |
| F8 | Negozio online per ogni cliente, con il suo marchio e il suo dominio, pronto in pochi giorni | M | 🔁 negozio unico oggi |
| F9 | Area clienti professionali (officine, ricambisti): ricerca per targa, ordini ripetuti, prezzi riservati | M | |
| F10 | API pubbliche per collegare siti e sistemi del cliente | M | Usa A1 |

### G. Amministrazione

Area **Ufficio**. Non serve un gestionale contabile completo: documenti, incassi e un'esportazione pulita per il commercialista.

| ID | Task | Dim. | Note |
|---|---|---|---|
| G1 | Documenti: preventivo, documento di trasporto, fattura, nota di credito, ricevuta; modelli personalizzabili | M | |
| G2 | Fattura elettronica: invio e ricezione tramite intermediario | M | Esterno: intermediario per il Sistema di Interscambio |
| G3 | Fatturazione cumulativa di pratiche, formulari, ritiri e custodie | S | |
| G4 | Tariffario dei servizi: rottamazione, ritiro, custodia giornaliera, radiazione | S | |
| G5 | Scadenziario di incassi e pagamenti con solleciti | M | |
| G6 | Prima nota ed esportazione per il commercialista | M | |
| G7 | Redditività per veicolo: costo di acquisto e lavorazione contro ricavi da ricambi e rottame | M | Nostro punto di forza in vendita |
| G8 | Cruscotto del titolare: vendite, margini, giacenza, rotazione, veicoli in lavorazione | M | |
| G9 | Regimi IVA corretti per ricambi usati e servizi | S | Con commercialista |

### H. Esperienza trasversale

Sono le cose che ci distinguono dai concorrenti. Vanno fatte insieme ai gruppi precedenti, non alla fine.

| ID | Task | Dim. | Note |
|---|---|---|---|
| H1 | Coda "Da fare" unica con scadenze normative e operative, filtrata per ruolo | M | Riprogetta la pagina "Oggi" |
| H2 | Ricerca globale da qualsiasi pagina (anche da tastiera) | M | |
| H3 | Notifiche: in app, email, WhatsApp per i clienti (ritiro, ordine spedito) | M | Esterno: WhatsApp Business |
| H4 | Navigazione a sei aree con moduli attivabili per piano | S | Sostituisce il menu attuale |
| H5 | Guida contestuale e assistenza dall'app | S | |
| H6 | Accessibilità, uso con guanti, contrasto per l'esterno | S | Già nei principi di design |

### I. Industria 4.0 (ultimo gruppo)

Da avviare solo dopo aver censito i macchinari del cliente. L'interconnessione è anche il requisito delle agevolazioni fiscali sull'acquisto dei macchinari: va verificato con il commercialista se e come si applicano oggi.

| ID | Task | Dim. | Note |
|---|---|---|---|
| I1 | Censimento dei macchinari: modello, interfaccia dati, protocollo | S | Presso il cliente |
| I2 | Bilancia: peso automatico in ingresso veicolo e in uscita materiali | M | Alimenta C10, D3, D6 |
| I3 | Isola di bonifica: quantità estratte per veicolo direttamente nella scheda di bonifica | M | Alimenta D1 |
| I4 | Pressa: carcasse pressate registrate e collegate ai veicoli | M | |
| I5 | Lettore di targhe al cancello: ingresso veicolo aperto in automatico | M | |
| I6 | Carrelli elevatori: movimenti di pallet e motori con scansione | S | |
| I7 | Documentazione tecnica dell'interconnessione per la perizia richiesta dalle agevolazioni | S | Esterno: perito |

---

## 3. Primo rilascio vendibile

Proposta di perimetro minimo per vendere a un primo cliente pilota. È ciò che un'autodemolizione non può non avere più ciò che la convince a cambiare:

- **Fondamenta:** A1–A5, A7, A8, A10, A11.
- **Migrazione:** B1, B3, B4, B6.
- **Pratica:** C1, C2, C4, C6, C9, C10.
- **Ambiente:** D1–D5, D7, D8.
- **Magazzino:** E1, E4, E5, E9.
- **Vendite:** F1, F3, F4.
- **Amministrazione:** G1, G2.
- **Esperienza:** H1, H2, H4.

Il resto entra per rilasci successivi, in ordine di richiesta dei clienti.

---

## 4. Da verificare prima di sviluppare

Questi punti decidono costi, tempi e fattibilità. Nessuno va dato per scontato.

1. **Abilitazioni ufficiali:** come un software di terzi si collega a RENTRI, Registro Unico Telematico, portale ministeriale e radiazioni (sportello telematico o agenzia partner).
2. **Visure e fermo amministrativo:** quale intermediario ACI usare e a che costo per visura.
3. **Banca dati veicoli e ricambi:** licenza, copertura, costo per azienda o per interrogazione.
4. **Intermediari:** fattura elettronica, conservazione a norma, firma digitale, registratore telematico, pagamenti, corrieri.
5. **Normativa di dettaglio:** modelli e tempi della presa in carico, regole di vendibilità dei componenti, regimi IVA. Va validata con consulente ambientale e commercialista.
6. **Marketplace:** API disponibili, commissioni, categorie.
7. **Industria 4.0:** macchinari del cliente, protocolli, stato delle agevolazioni.
8. **Gestionale attuale del cliente:** quale usa e in che formato esporta i dati.
9. **Fasce di prezzo L/T/B/2/3/4:** cosa rappresentano nel gestionale attuale.

---

## 5. Riferimenti

- [GestCAR – Ecodat](https://www.ecodat.it/gestcar/)
- [Banca dati e vendita ricambi online – Ecodat](https://www.ecodat.it/banca-dati-e-vendita-ricambi-online/)
- [Radiazioni Express – Ecodat](https://www.ecodat.it/radiazioni-express/)
- [Visure – Ecodat](https://www.ecodat.it/visure/)
- [Ecoeuro, sistema digitale per i veicoli a fine vita – Sicurauto](https://www.sicurauto.it/b2b-auto-flotte/dalla-demolizione-al-riuso-ecoeuro-digitalizza-la-filiera-dei-veicoli-a-fine-vita/)
- [Cobat Cyclus – Sicurauto](https://www.sicurauto.it/b2b-auto-flotte/cobat-presenta-cyclus-la-rete-certificata-per-i-veicoli-fuori-uso)
- Specifiche funzionali v0.1 del cliente (fasi 0–5, requisiti di accettazione, questioni aperte)
