# Collegamenti reali: link, registrazione, API e costi

Ricerca del 16 novembre 2026. Ogni dato ha la sua fonte; **(da confermare)** = trovato solo su fonti secondarie, in contrasto tra fonti, oppure non pubblicato. Prezzi IVA esclusa se non indicato. Le norme vanno validate con consulente ambientale, studio di pratiche auto e commercialista prima di andare in produzione.

**In sintesi**
- Si può integrare subito, con API pubbliche: **RENTRI** (registro e formulari), **fatturazione elettronica** via intermediario, **pagamenti** (Stripe), **spedizioni** (Sendcloud), **eBay**, **Ovoko**, **dati da targa** (Openapi), **OCR targhe** (Plate Recognizer), **firma** (Openapi eSignature).
- Serve un contatto con l'ente o il fornitore prima di sviluppare: **RVFU** (specifiche riservate, VPN ACI), **banca dati ricambi** (Kromeda, Infocar, TecDoc: licenze su preventivo), **B-Parts**, **RicambiPro/Multibreves**, **corrispettivi** (soluzioni software certificate in arrivo).
- Senza API, solo file o portale: **MUD** (file da caricare), **Albo gestori**, **COBAT**, **O.R.S.O.**

---

## 0. Riepilogo: chi paga cosa e come si entra (17/11/2026)

Tutti i collegamenti nell'app sono oggi **simulati**. Costi e fonti nelle sezioni 1–5.

**Come si entra**
- **SPID titolare**: SPID, CIE o CNS **personale** del titolare o legale rappresentante dell'autodemolizione. Il portale controlla la carica sul Registro Imprese, poi il titolare abilita i collaboratori. Non serve uno SPID intestato alla società.
- **Registrazione**: account online con email, dati della società e partita IVA. Per incassi e WhatsApp anche verifica dell'azienda con documenti (non SPID).
- **Contratto**: preventivo e licenza firmata con il fornitore.

**Chi si registra**: *Tu* = chi sviluppa il gestionale (account tecnico, unico per tutti i clienti). *Cliente* = l'autodemolizione, che resta titolare dei dati e degli obblighi di legge.

### A. Obbligatori per legge (si pagano comunque, con o senza gestionale)
| Servizio | Nell'app | Costo | Accesso | Chi |
|---|---|---|---|---|
| RVFU (presa in carico, CRD, radiazione) | Pratica | 32 € bollo + 13,50 € emolumenti per radiazione (+10,20 € diritti MIT, da confermare); VPN e firma remota ACI: costo non pubblicato | SPID titolare, accreditamento per sede | Cliente. API riservate: Tu le chiedi ad ACI |
| RENTRI (registro e formulari) | Ambiente | Iscrizione 10 €; 100 € il primo anno, poi 60 €/anno per sede. **API gratuite** | SPID titolare + certificato .p12 per le API | Cliente (certificato suo). Tu: ambiente demo |
| MUD | Ambiente | 10 €/anno | SPID titolare + firma digitale (o consulente con delega) | Cliente. Il gestionale prepara il file |
| Firma digitale qualificata (RVFU, MUD, formulari) | — | Da 29 € il certificato (Openapi); quella ACI per RVFU non ha prezzo pubblico | Riconoscimento dal prestatore | Cliente (la persona che firma) |
| Fatture e Corrispettivi (Agenzia Entrate) | Vendite | **Gratis**, anche la conservazione delle fatture | SPID titolare o incaricato | Cliente |
| Registratore telematico | Scontrino | 150–600 € o canone | Rivenditore e tecnico abilitato | Cliente |
| O.R.S.O. (regionale) | Ambiente | Gratis (da verificare per regione) | SPID o credenziali regionali | Cliente |

### B. A consumo, con registrazione normale
| Servizio | Nell'app | Costo | Chi |
|---|---|---|---|
| Openapi, dati tecnici da targa | Accettazione | 0,40 €/chiamata (fino a 0,18 € con abbonamento); sandbox gratis | Tu |
| Openapi, visura PRA | Pratica | 10,90 o 16,70 € (da confermare) | Tu |
| *Alternativa*: ACI Visurenet | Pratica | 6 € | Chiunque con SPID, max 3 al giorno, **senza API**: solo a mano |
| Plate Recognizer, targa da foto | Accettazione | Gratis 2.500/mese (prova), poi da 50 $/mese | Tu |
| Modello IA con visione, pezzo da foto | Campo, inventario | A consumo, pochi centesimi a foto (da stimare) | Tu |
| Fattura elettronica: Openapi o Invoicetronic | Vendite | 0,02–0,10 € a fattura | Tu. Il cliente imposta il codice destinatario sul portale Agenzia (SPID titolare) |
| Openapi eSignature | Firma documenti | Firma avanzata 0,69 € | Tu |
| Sendcloud | Spedizioni | 28 €/mese + 0,10 € a etichetta | Cliente (con i suoi contratti BRT, GLS, Poste) |
| WhatsApp (Meta) | Avvisi ai clienti | Circa 0,03 $ ad avviso | Tu: verifica aziendale Meta. Cliente: suo numero e carta |

### C. Entrata gratuita, si paga una commissione sul venduto
| Servizio | Nell'app | Costo | Chi |
|---|---|---|---|
| Stripe Connect + Terminal | Incassi banco e online | Nessun canone; 1,5% + 0,25 € online, 1,4% + 0,10 € al POS; lettori da 59 € | Tu (piattaforma) + Cliente (account collegato, verifica con documento del legale rappresentante) |
| eBay | Marketplace | Sviluppatore gratis; vendita 12,5% + 0,35 € a ordine; negozio facoltativo da 24,95 €/mese | Tu: Developers Program. Cliente: account venditore professionale |
| Ovoko | Marketplace | Nessun canone; commissione (circa 10%, da confermare) | Cliente |
| Google Merchant Center | Negozio online | Schede gratuite; annunci a pagamento | Cliente (account Google e dominio) |

### D. Solo su contratto o preventivo
- **Catalogo ricambi e prezzo del nuovo** (oggi "catalogo simulato"): Kromeda, Infocar, TecDoc, DAT. Licenza per uso multi-cliente da negoziare.
- **Altri marketplace**: B-Parts (rete chiusa), RicambiPro, Multibreves.
- **Dati in blocco**: ACI forniture PRA, MIT Archivio Nazionale Veicoli (contratto e VPN), COBAT.
- partslink24 (23–29 €/mese) si usa solo a mano: non ha API.

### Regole per restare a norma
1. **Credenziali del cliente, non tue.** RVFU, RENTRI, Agenzia Entrate ed eBay agiscono a nome dell'autodemolizione: tu non usi il tuo SPID per i loro adempimenti. Serve un contratto che lo autorizzi.
2. **Non automatizzare portali fatti per l'uso a mano**: Visurenet (3 al giorno), "Documento commerciale online" (i "velocizzatori" saranno bloccati dal MEF), portale RVFU senza le specifiche ufficiali.
3. **GDPR**: tu sei responsabile del trattamento per ogni cliente (art. 28). Accordo sui dati (DPA) con Openapi, Plate Recognizer, firma, Meta e fornitore IA; per i fornitori extra UE va verificato il trasferimento dei dati.
4. **Conservazione**: RENTRI non conserva i documenti; registri, formulari e CRD vanno conservati a norma.

---

## 1. Pratiche veicolo

### RVFU – Registro unico telematico dei veicoli fuori uso (CRD e radiazione)
- **Cos'è**: obbligatorio dal **7/6/2024** (art. 5 c. 10 D.Lgs. 209/2003, DPR 177/2022). Presa in carico, **Certificato di Rottamazione Digitale (CRD)** con codice univoco nazionale (annullabile solo in giornata, copia stampata al detentore), fascicolo digitale, radiazione.
- **Link**
  - Accreditamento: https://www.ilportaledellautomobilista.it/web/portale-automobilista/registrazione-cittadino → "Accreditamento al Registro Telematico dei Veicoli Fuori Uso"
  - Applicativo e "Manuali e specifiche ws" (area privata): https://www.ilportaledeltrasporto.it/web/ptr/
  - Circolare MIT-ACI prot. 15356 del 29/05/2024: https://prefettura.interno.gov.it/sites/default/files/93/2024-07/2024.06.25-registro-telematico-veicoli-fuori-uso_avvio-della-procedura_0.pdf (sostituita dalla circolare MIT n. 15 del 17/02/2025, da leggere)
  - Manuale MIT gestione utenze: https://dylog.it/wp-content/uploads/2024/05/MIT-Gestione-Utenze_Registro-Unico-Telematico-Veicoli-Fuori-Uso-RVFU.pdf
  - Assistenza software house: Supporto.Swhouse@informatica.aci.it
- **Per registrarsi**: titolare o legale rappresentante con **SPID o CIE personale** (carica verificata su InfoCamere), un accreditamento **per sede**; poi ACI fornisce **VPN** e **firma digitale remota** (obbligatorie). Il titolare crea le utenze dei collaboratori.
- **API**: esistono "specifiche ws" per software house, **riservate** all'area privata; accesso via VPN ACI. Già integrato da Dylog ed Ecoeuro. **Da chiedere ad ACI**: se un SaaS in cloud può scrivere (presa in carico, CRD, radiazione) per conto dei clienti, con quali credenziali, se esiste un ambiente di test.
- **Radiazione**: entro **30 giorni dalla consegna**, pratica DU **C05332** (C05333 esente con provvedimento PA), fascicolo pagato e inoltrato entro le 16:00 del secondo giorno lavorativo; anche cumulativa (stessa giornata, stesso tipo di veicolo e targa). In alternativa tramite agenzia pratiche auto (STA). Targhe e documenti si distruggono non prima di 120 giorni dal CRD.
- **Fascicolo digitale** (un PDF): carta di circolazione o DU; certificato di proprietà (cartaceo o digitale) se manca il DU; CRD; istanza unificata; con C05333 il provvedimento della PA. Il PRA può chiedere un'integrazione (preavviso di ricusazione).
- **Prova della radiazione**: la **ricevuta di avvenuta radiazione** emessa dal PRA, che "si acquisisce automaticamente al RVFU" (con l'agenzia la manda l'agenzia). Non esiste un certificato di radiazione separato; al detentore resta il CRD. Dopo, nel RVFU si annotano le date di distruzione di targhe e documenti e di cancellazione da ANV e PRA. Fonte: guida Sicurauto sul RVFU (https://www.sicurauto.it/guide-utili/pratiche-auto/registro-dei-veicoli-fuori-uso-quando-e-come-si-usa/); da confermare sull'Allegato A della circolare MIT 15/2025 (par. 5.3-5.4), non letto perché a pagamento.
- **Nell'app** (passi 4 e 5 della pratica): codice, canale e fascicolo da spuntare; invio simulato; la ricevuta si registra a mano (numero, data, PDF in `DATI_DIR/allegati`); poi la distruzione con data, che compare nel Da fare una settimana prima dei 120 giorni.
- **Costi**: imposta di bollo **32,00 €** + emolumenti PRA **13,50 €** a pratica; cumulativa: un bollo da 32 € + 13,50 € per veicolo (circolare 2024). Diritti MIT 10,20 €: indicati da ACI, non dalla circolare (da confermare). Accreditamento, VPN e firma remota ACI: costi non trovati.
- **Fermo amministrativo**: dal **20/02/2026** (L. 14/2026) non impedisce la radiazione per demolizione se c'è l'**attestazione di inutilizzabilità** (art. 5 c. 8-bis/8-ter D.Lgs. 209/2003; lettera circolare ACI 9626 del 19/02/2026; circolare MIT 9948 del 01/04/2026). Il proprietario perde gli incentivi; non vale per l'esportazione. La pagina ACI sul fermo non è ancora aggiornata.

### Visura PRA (intestatario, fermi, ipoteche)
| Canale | Link | Per registrarsi | API | Costo |
|---|---|---|---|---|
| ACI Visurenet | https://aci.gov.it/servizio/visurenet-visura-della-banca-dati-del-pubblico-registro-automobilistico-pra/ | SPID/CIE/CNS; **max 3 visure al giorno per codice fiscale** | No | **6,00 €** (pagoPA) |
| ACI per professionisti (PEC) | https://aci.gov.it/pratica-auto/visura-nominativa/ | Categorie abilitate (avvocati, notai…); i demolitori non hanno un canale dedicato | No | 6,00 € (storica 25,63 €) |
| Verifica vincoli ACI (gratis, dice solo *se* c'è un vincolo) | https://aci.gov.it/servizio/verifica-tipo-documento-e-vincoli/ | Nessuna | No | Gratis |
| **Openapi – PRA License Plate Report** | https://openapi.com/products/pra-license-plate-report-italy · docs https://console.openapi.com/apis/docuengine/documentation | Registrazione su console.openapi.com | **Sì**, asincrona (entro 24 ore lavorative, PDF) | 10,90 € o 16,70 € (la pagina è in contrasto: da confermare) |
| ACI forniture massive | https://aci.gov.it/servizio/fornitura-dati-pra/ · aci-fdautomotive@aci.it | Convenzione | File | Su preventivo |

### Dati tecnici da targa e telaio
| Fornitore | Link | API | Costo |
|---|---|---|---|
| **Openapi Automotive IT-car** | https://openapi.com/products/license-plate · docs https://console.openapi.com/it/apis/automotive/documentation | REST sincrona, sandbox gratuita; marca, modello, versione, kW, alimentazione, **KType** (il VIN nell'esempio è vuoto) | 0,40 €/chiamata; abbonamento da 0,37 € (1.000) a 0,18 € (200.000) |
| MIT – Archivio Nazionale Veicoli | https://www.mit.gov.it/documentazione/accesso-al-sistema-informativo-motorizzazione-civile | Web service con contratto, VPN | Fissato da contratto |
| Infocar / Quattroruote Professional | professional@quattroruotepro.it | Web service (specifiche non pubbliche) | Su preventivo |
| DAT Italia (da VIN) | www.dat-italia.com | Partnership API | A transazione, su preventivo |

### Lettura targhe da foto (OCR)
| Fornitore | Link | Costo | Note |
|---|---|---|---|
| **Plate Recognizer** | https://platerecognizer.com/pricing/ | Free 2.500/mese (prova); $50/mese 50.000; $150 250.000 | Italia con `regions=it`; conserva 30 giorni di default (valutare DPA GDPR) |
| Rekor CarCheck | https://docs.rekor.ai/developers/carcheck/create-an-account | $40/mese 2.500 crediti | Copertura Italia non dichiarata |

---

## 2. Ambiente

### RENTRI – registro di carico e scarico e formulari digitali
- **Link**: portale https://www.rentri.gov.it · area operatori https://operatori.rentri.gov.it · **API** https://api.rentri.gov.it/docs · **demo** https://demoapi.rentri.gov.it/docs e https://www.rentri.gov.it/demo · verifica FIR https://operatori.rentri.gov.it/public/verifica-fir
- **Per registrarsi**: il rappresentante legale con SPID/CNS/CIE (verifica sul Registro Imprese), poi nomina gli incaricati. Per le API: "Accreditamento operatori" e download del **certificato di interoperabilità (.p12)** nella sezione "Interoperabilità" (oppure un certificato eIDAS qualificato dell'impresa o di un incaricato).
- **API**: REST, OpenAPI 3, pubbliche. `anagrafiche`, `codifiche`, `dati-registri`, `formulari`, `vidimazione-formulari`, `ca-rentri`. Autenticazione con JWT firmato (pattern AgID ID_AUTH_REST_02) + integrità (INTEGRITY_REST_01); chiamate asincrone con polling o callback. **Ambiente demo libero**: una software house simula produttore, trasportatore e destinatario sotto un unico codice fiscale.
- **Modello SaaS**: non esiste accreditamento della software house; ogni chiamata è dell'operatore → **un certificato per cliente** (o il certificato di una persona incaricata da ogni cliente). Da confermare con un consulente e da coprire con nomina a responsabile del trattamento.
- **Formulari (xFIR)**: obbligatori dal **16/09/2026** per i produttori di rifiuti pericolosi (sanzioni dal 15/09/2026). Firma in due passi (hash → firma XAdES). Firmano: firma qualificata, sigillo, CNS o firma remota RENTRI (richiede app mobile abbinata). **Il .p12 di interoperabilità non firma i FIR.** La firma si annulla entro 30 minuti se nessun altro ha firmato.
- **Registro**: il gestionale numera i movimenti; schemi XSD `rentri-registri`, `rentri-movimenti`; RENTRI **non conserva** i documenti (conservazione a carico dell'operatore). Trasmissione: cadenza da verificare sul DD 143/2023.
- **Costi**: diritto di segreteria 10 € all'iscrizione e a ogni variazione; contributo annuo impianti **100 € il primo anno, poi 60 €** per unità locale (scadenza 30 aprile). Nessun costo per chiamata API.

### MUD – Comunicazione veicoli fuori uso
- **Link**: invio https://www.mudtelematico.it · DPCM e allegati https://www.mase.gov.it/portale/-/mud-modello-unico-di-dichiarazione-ambientale-per-l-anno-2026 · tracciato record su https://www.ecocerved.it
- **Per inviare**: SPID/CIE/CNS + **firma digitale**; consulenti e associazioni possono inviare con delega.
- **Formato**: nessuna API. Il gestionale genera il **file di testo multirecord** (moduli AUT, ROT, FRA e sotto-moduli VEIC), una provincia per file, da caricare sul portale.
- **Costi**: 10 € di diritti per dichiarazione. MUD 2026 (dati 2025): scadenza 3/07/2026.

### Albo Nazionale Gestori Ambientali
- https://www.albonazionalegestoriambientali.it · elenco iscritti https://www.albonazionalegestoriambientali.it/Public/ElenchiIscritti
- Serve per i **trasportatori** dei formulari (verifica iscrizione). Se l'impianto ritira veicoli con mezzi propri: categoria da confermare con il consulente (probabile cat. 5). Nessuna API trovata.

### COBAT / Cyclus e O.R.S.O.
- COBAT ritiri: https://ritiri.cobat.it (da verificare). Cyclus: rete di autodemolitori su piattaforma Cobat. **Nessuna API pubblica**: contatto commerciale.
- O.R.S.O.: applicativo regionale (ARPA); si carica lo stesso file MUD. Obblighi diversi per regione.

---

## 3. Ricambi: banche dati

| Fornitore | Cosa dà | Link | API | Costo |
|---|---|---|---|---|
| **Kromeda (Solera Italia)** – consigliato | OE con sostituzioni, cross-reference, **listini OE italiani** (prezzo del nuovo), esplosi, identificazione da targa | https://soleraitalia.it/en/kromeda-en/ · WebService https://platform.softwareone.com/product/kromeda-webservice/PCP-1368-1192 | REST/JSON (i listini OE non si scaricano in blocco) | Su preventivo |
| Infocar / Quattroruote "Ricambi & Tempari" – alternativa | Originali ed equivalenti, consultazione **da targa**, dichiara gli autodemolitori tra i clienti | professional@quattroruotepro.it | Web service (non pubblico) | Su preventivo |
| **TecAlliance TecDoc** | Aftermarket, OE↔IAM, **KType** per la compatibilità eBay, ricerca da VIN/targa | https://www.tecalliance.net/products/cards/tecdoc-web-service | Web service + data package | Su preventivo; uso SaaS multi-cliente da negoziare (licenza non sublicenziabile) |
| DAT Italia | Identificazione da VIN, ricambi in ottica preventivo | www.dat-italia.com | Partnership | Su preventivo |
| partslink24 | Cataloghi originali multimarca (uso interattivo del demolitore) | https://www.partslink24.com | No | 23 €/mese (annuale), 29 €/mese (mensile) |
| Collins | Editore (non è un fornitore dati verificato) | — | — | Chiedere a Collins |

---

## 4. Canali di vendita

| Canale | Link | Per registrarsi | API | Costi |
|---|---|---|---|---|
| **eBay.it** | Inventory API https://developer.ebay.com/api-docs/sell/static/inventory/managing-product-compatibility.html · tariffe https://www.ebay.it/help/selling/fees-credits-invoices/servizi-di-pagamento-tariffe-per-venditori-professionali?id=4809 | Noi: eBay Developers Program; ogni cliente: account **venditore professionale** collegato via OAuth | REST, sandbox; compatibilità per **KType** o proprietà del veicolo | Ricambi auto: **12,5% + 0,35 €/ordine**; negozio 24,95 / 49,95 / 179,95 €/mese |
| **Ovoko** | API http://api.rrr.lt/docs/ · venditori https://join.ovoko.com/ | Account venditore; credenziali + `user_token` per cliente (programma per software house da chiedere) | OpenAPI 3, webhook (anche "venduto su eBay") | Nessun canone; commissione (10% su fonte non confermata) |
| B-Parts (Stellantis) | https://b-parts.com | Rete chiusa: solo centri autorizzati selezionati | Nessuna pubblica (via app o Multibreves) | Su contratto |
| RicambiPro.it | https://www.ricambipro.it | Affiliazione venditori | "Integrazioni software" citata, pagina non trovata | Non pubblici |
| Multibreves (aggregatore) | https://www.multibreves.com/en/partners | Contratto | Connettori verso eBay, B-Parts, Ovoko, Neryus, marketplace iberici | Non pubblici |
| Google Merchant Center (negozio proprio) | https://support.google.com/merchants/answer/6324469 | Account del cliente con dominio verificato | **Merchant API v1** (la Content API è dismessa dal 18/08/2026); `condition=used`, `mpn` = codice OE | Schede gratuite; annunci a CPC |
| Subito.it | — | — | Nessuna API ufficiale | — |

### eBay: dal ricambio all'annuncio con un tocco (ricerca del 18/11/2026)

**Strada consigliata: API REST "Sell" di eBay chiamate dal nostro server, testo dell'annuncio scritto dal nostro modello IA.** Nessun plugin o connettore pronto fa il lavoro al posto nostro per un gestionale fatto su misura.

**Cosa usare**
| Pezzo | API eBay | A cosa serve |
|---|---|---|
| Accesso del cliente | OAuth "authorization code grant" https://developer.ebay.com/api-docs/static/oauth-authorization-code-grant.html | Il titolare accede a eBay una volta e autorizza il gestionale. Token di accesso di 2 ore, rinnovo per circa 18 mesi, poi si riautorizza. Libreria ufficiale: https://github.com/eBay/ebay-oauth-nodejs-client |
| Condizioni di vendita | Account API (business policies, `inventory_location`) | Una volta per cliente: spedizione, pagamento, reso e magazzino. Senza l'adesione alle business policies l'Inventory API non pubblica |
| Foto | Media API `createImageFromFile` https://developer.ebay.com/api-docs/commerce/media/resources/image/methods/createImageFromFile | Carica le foto su eBay e restituisce l'URL da mettere nell'annuncio. JPG, PNG, WEBP, HEIC; 50 caricamenti ogni 5 secondi; fino a 24 foto |
| Categoria e caratteristiche | Taxonomy API: `getCategorySuggestions`, `getItemAspectsForCategory`, `getCompatibilityProperties` (eBay Italia = albero **101**) https://developer.ebay.com/api-docs/sell/taxonomy/resources/category_tree/methods/getCompatibilityProperties | Categoria giusta e caratteristiche obbligatorie (marca, codice OE, lato…) |
| Annuncio | Inventory API: `createOrReplaceInventoryItem` (SKU = R-000000) → `createOffer` → `publishOffer` https://developer.ebay.com/api-docs/sell/static/inventory/publishing-offers.html | Tre chiamate e il pezzo è online sul profilo del cliente. Alcuni campi facoltativi in creazione diventano obbligatori alla pubblicazione |
| Compatibilità veicoli | Inventory API `createOrReplaceProductCompatibility` https://developer.ebay.com/api-docs/sell/inventory/resources/inventory_item/product_compatibility/methods/createOrReplaceProductCompatibility | Elenco dei veicoli su cui monta il pezzo, in due modi: `compatibilityProperties` (marca, modello, anno, versione, motore, con i valori presi dalla Taxonomy `getCompatibilityPropertyValues`, gratis) oppure `productIdentifier.ktype`. **KType confermato su eBay.it** dalla specifica ufficiale: "Only the AU, DE, ES, FR, IT, and UK marketplaces support the use of K Type Numbers". Note per veicolo fino a 500 caratteri (es. posizione del pezzo) |
| Venduto o ritirato | `withdrawOffer`, `deleteInventoryItem`; quantità a 0 | Il pezzo venduto al banco o su un altro canale sparisce da eBay |
| Ordini eBay | Notification API, argomento "Order Confirmation" (dal 1/12/2025) + Fulfillment API `getOrders` | Il pezzo venduto su eBay passa a "venduto" nel gestionale, con riserva unica tra canali. Il vecchio `ITEM_SOLD` non esiste più nelle API nuove (da fonte non ufficiale) |
| Alternativa in blocco | Feed API, file XML `LMS_ADD_FIXED_PRICE_ITEM` (con `LMS_VERIFY_…` per la prova) https://developer.ebay.com/api-docs/sell/static/feed/lms-feeds-overview.html | Per caricare il magazzino migrato tutto insieme |

**Cosa NON usare (per ora)**
- **Inventory Mapping API** (l'IA di eBay che crea l'annuncio da foto e titolo, GraphQL): solo eBay USA e **esclude Ricambi e accessori**. https://developer.ebay.com/develop/api/sell/inventory_mapping.md
- **Server MCP per eBay**: quello ufficiale (`@ebay/npm-public-api-mcp`, https://github.com/eBay/npm-public-api-mcp) è in sola lettura e senza sandbox; quelli completi (es. `ebay-mcp` di YosefHayim) sono progetti non ufficiali. Servono a un assistente IA, non a un gestionale che pubblica per i clienti.
- **Moduli per e-commerce** (M2E Pro per Magento, Prestalia FastBay per PrestaShop, bindCommerce, Marketrock, Base.com): funzionano solo dentro quelle piattaforme. Utili come riferimento su come trattano compatibilità e KType.
- **Ovoko e Multibreves**: pubblicano anche su eBay, ma il cliente pagherebbe un secondo intermediario. Restano utili per gli altri marketplace (sezione 4).

**L'annuncio scritto in automatico**
Il gestionale ha già tutto: tipo di pezzo, veicolo d'origine (marca, modello, versione, anno, alimentazione, km), codice OE, lato, condizione, difetti, foto, prezzo, ubicazione. Il nostro modello IA con visione compone titolo (massimo 80 caratteri, con marca, modello, pezzo, codice OE), descrizione e caratteristiche eBay; la Taxonomy API dice quali caratteristiche sono obbligatorie per la categoria. L'operatore vede l'anteprima e tocca "Pubblica su eBay".

**Nostra commissione: sovrapprezzo dell'8% (decisione del 18/11/2026)**
Ogni annuncio pubblicato dal gestionale esce a **prezzo dell'autodemolizione + 8%**. L'8% è la nostra commissione per la gestione del venduto. Vale per **tutti i canali online**: eBay, Ovoko e gli altri marketplace, negozio online del cliente. Al banco resta il prezzo dell'autodemolizione, con i suoi listini. eBay però paga il conto del venditore, cioè l'autodemolizione, e non noi: la commissione si fattura al cliente sui pezzi venduti, per esempio una volta al mese, e si storna se il pezzo viene reso.

Esempio con 100 € (IVA inclusa) fissati dall'autodemolizione:
| | Senza gestionale | Con l'8% |
|---|---|---|
| Prezzo su eBay | 100,00 € | 108,00 € |
| Commissione eBay (12,5% + 0,35 €) | 12,85 € | 13,85 € |
| Nostra commissione | — | 8,00 € |
| Resta all'autodemolizione | 87,15 € | 86,15 € |

- **eBay prende la sua percentuale anche sul nostro 8%**: 1 € ogni 100 €, oggi a carico dell'autodemolizione. Per coprirlo il sovrapprezzo dovrebbe essere circa 9,14%.
- **IVA**: gli 8 € pagati dall'acquirente contengono 1,44 € di IVA che l'autodemolizione versa. Per un costo netto di 8 € la nostra fattura va fatta così: 6,56 € + 22% IVA = 8,00 €. Fatturare invece 8 € + IVA = 9,76 € le costerebbe 1,44 € in più. Se il cliente vende l'usato in regime del margine, il calcolo cambia. **Da validare col commercialista** e da scrivere nel contratto.

**Obblighi da rispettare nell'annuncio**
- **GPSR** (sicurezza dei prodotti UE): vale anche per l'usato venduto da professionisti. Nell'Inventory API sono i campi `regulatory.manufacturer`, `regulatory.responsiblePersons` (fino a 5, sede UE) e `regulatory.productSafety`. Se mancano dove servono, l'annuncio resta invisibile o non acquistabile nell'UE finché non si completano. Vedi le risposte qui sotto.
- **Garanzia e reso** per i privati: garanzia legale di 2 anni, riducibile a 1 sull'usato con accordo; recesso di 14 giorni nelle vendite a distanza (Codice del consumo). La politica di reso eBay del cliente deve rispettarli. Da validare col commercialista.
- **Account del cliente**: venditore professionale (account aziendale), con le business policies attive.

**Risposte ai dubbi (18/11/2026)**
1. **KType su eBay.it: sì.** Lo dice la specifica ufficiale dell'Inventory API (https://developer.ebay.com/develop/api/spec/inventory_api.json, tipo `ProductIdentifier`) e la guida della Trading API (Italia, sito 101: https://developer.ebay.com/api-docs/user-guides/static/trading-user-guide/manually-specify-compatibility.html). Se il KType non è nel catalogo eBay, quel veicolo viene scartato. **Si può partire senza KType**: per il veicolo d'origine bastano marca, modello, anno e motore, presi con la Taxonomy API, gratis. Per allargare la compatibilità ad altri veicoli servono KType e codici OE da una banca dati a licenza (TecDoc, sezione 3).
2. **GPSR sui ricambi usati: quasi sempre basta poco.** Secondo eBay (https://www.ebay.com/sellercenter/resources/general-product-safety-regulation · https://www.ebay.de/verkaeuferportal/gesetzliche-steuerliche-vorgaben/verordnung-produktsicherheit), i prodotti messi sul mercato UE **prima del 13/12/2024** e conformi alla direttiva precedente non hanno bisogno dei dati GPSR (art. 51). Per un pezzo smontato, conta l'anno del veicolo: auto immatricolate prima di quella data → esenti, secondo eBay. Per le auto più recenti: produttore = casa auto (tabella marca → sede UE, da compilare una volta). Esclusi anche i pezzi "da riparare o riciclare" dichiarati come tali. eBay avverte che altri interpretano la norma diversamente: va validato col consulente. Quali categorie chiedono i dati su eBay.it lo dice la Metadata API `getRegulatoryPolicies`.
3. **Negozio eBay: non serve per le API.** I requisiti ufficiali sono un account del Developers Program (nostro) e il conto venditore con le business policies attive. Il negozio è richiesto solo dalla Stores API (categorie della vetrina), che non ci serve. La pagina eBay.it sugli strumenti in blocco elenca Inventory, Trading e Feed API senza chiedere un negozio (https://www.ebay.it/help/selling/listings/listing-tips/bulk-listing-tool?id=4160). Il vincolo "Pro Basic e superiori" esiste solo su eBay Australia (https://www.ebay.com.au/sellercentre/integration-tools). Il negozio conviene comunque per le tariffe e le inserzioni gratuite.
4. **Limiti di chiamate: bastano quelli di base.** Inventory API 2 milioni di chiamate al giorno per applicazione; foto 50 caricamenti ogni 5 secondi per utente (il limite giornaliero è indicato in modo diverso da due pagine eBay: 200.000 o 1 milione). Con 10 clienti e 100 pezzi al giorno ciascuno siamo intorno a 10.000 chiamate al giorno. Oltre si chiede l'"Application Growth Check", gratis (https://developer.ebay.com/api-docs/static/gs_request-an-application-growth.html).

**Resta da fare dal vivo, con la sandbox**: una pubblicazione di prova su eBay Italia con KType e con marca/modello/anno, per vedere quali campi obbligatori chiede `publishOffer` nelle categorie dei ricambi.

**Cosa è costruito (prototipo, 18/11/2026)**

- **Annunci con più pezzi uguali.** I pezzi con stesso tipo, codice verificato, lato, condizione, spedibilità e prezzo stanno in un solo annuncio con una quantità. Il prezzo è unico per annuncio: se lo cambi da un pezzo, il gestionale chiede conferma per tutti.
- **Negozio online ed eBay leggono la stessa giacenza.** Un pezzo venduto al banco, sul negozio o su eBay scala la quantità ovunque. A zero l'annuncio resta come "esaurito" (sul negozio con il telefono, su eBay nascosto dalle ricerche) e torna online quando rientra un pezzo uguale.
- **Vendite eBay importate** ogni 5 minuti, solo in modo Sandbox con il conto collegato (in Simulato si usa "Simula vendita su eBay"); in ogni modo c'è anche il pulsante "Controlla vendite eBay". Ogni controllo riguarda anche l'ora prima dell'ultimo, così un ordine che eBay mostra in ritardo non si perde; quelli già importati si riconoscono dal numero d'ordine. Se eBay vende un pezzo che da noi non c'è più, l'ordine è segnato "da gestire: manca 1 pezzo" in Vendite e in Da fare, finché non lo segni come gestito.
- **Quantità e prezzo si riallineano da soli** ogni minuto (subito dopo un cambiamento), anche se due dispositivi hanno scritto insieme: il gestionale confronta quantità e prezzo di adesso con quelli mandati a eBay. Parte solo dopo che il dispositivo ha letto i dati aggiornati dagli altri.
- **Categoria eBay.** La sceglie eBay alla prima pubblicazione, dalla parola del tipo di pezzo. Se eBay la rifiuta, o ne vuoi un'altra, scrivi il numero della categoria nell'anteprima o in "Modifica testo" dell'elenco annunci.
- **Foto rimaste nel telefono non vanno su eBay.** Se il caricamento sul server non è riuscito, la foto resta solo nel telefono: il negozio la mostra, eBay no, e l'annuncio porta l'avviso "foto non ancora caricate sul server". Rifai la foto con la rete per mandarla.
- **"Ripristina dati demo" non tocca eBay.** Gli annunci già mandati alla sandbox e l'archivio del ponte (`ebay.json` nella cartella dati del server, `.demo-data/` se non indicata: collegamento, politiche, foto, categorie, ordini già letti) restano. Ritira da eBay gli annunci prima del ripristino, o toglili dalla sandbox a mano.
- **Modo Simulato (predefinito).** Senza chiavi eBay il gestionale usa un eBay finto, con la pagina `/ebay-simulato/<annuncio>` e il pulsante "Simula vendita su eBay". Serve a provare tutto senza account.
- **Modo Sandbox.** Con le chiavi di prova il gestionale parla con le API vere di eBay (ambiente di prova): accesso OAuth, foto, categoria, caratteristiche, compatibilità veicoli, politiche, pubblicazione, ritiro e lettura ordini. Non esiste ancora il modo Produzione. Il codice non è mai stato eseguito contro eBay: la prova qui sotto serve a questo.

**Prova in sandbox (guida per Alessandro)**

1. Crea l'account sviluppatore gratuito su https://developer.ebay.com (eBay Developers Program).
2. Nel portale, in "Application Keys", crea le chiavi **Sandbox**: ottieni **App ID** e **Cert ID**. Crea anche un utente di prova venditore in "Sandbox Users".
3. Nelle impostazioni delle chiavi Sandbox, in "User Tokens", crea un **RuName** e, come indirizzo di accettazione ("Auth accepted URL"), metti l'indirizzo HTTPS del tunnel del prototipo seguito da `/api/ebay/ritorno`, per esempio `https://<tunnel>/api/ebay/ritorno`. eBay accetta solo HTTPS: `localhost` non va bene.
4. Apri il gestionale dal tunnel, come Responsabile, in Impostazioni → Collegamenti → eBay. Scegli l'ambiente **Sandbox** e inserisci App ID, Cert ID e RuName. Il riquadro "Conto eBay" mostra l'indirizzo di ritorno da usare.
5. Tocca **Collega account eBay**, accedi con l'utente di prova venditore e consenti l'accesso. Torni in Collegamenti con "Collegato". Al primo collegamento il gestionale crea le politiche (spedizione, pagamento, reso) e la sede; puoi cambiarle dai sei menu sotto "Conto eBay" e toccare "Salva scelte".
6. In Pubblicazione tocca **Pubblica su eBay** su un annuncio pronto. Controlla poi su https://www.sandbox.ebay.it (o sandbox.ebay.com) con l'utente di prova: titolo, foto, prezzo (base +8%), quantità, caratteristiche e compatibilità. Gli avvisi dicono cosa eBay non ha accettato.
7. Prova anche: una vendita al banco (la quantità su eBay scende), "Ritira da eBay" e un acquisto con un secondo utente di prova (compare in Vendite dopo il controllo).

**Da verificare in sandbox** (ipotesi lette nelle specifiche eBay, non ancora provate)

1. Nomi delle proprietà dei veicoli su eBay.it (marca, modello, anno, motore): se sono diversi, la compatibilità viene saltata con un avviso.
2. Il motore (per esempio "1.6 JTDm 105 CV") probabilmente non coincide con i valori di eBay: viene scartato con un avviso.
3. Valori di "Posizionamento sul veicolo" (Destra, Sinistra, Anteriore) e nomi di altre caratteristiche ("Numero ricambio produttore", "Tipo") nella categoria scelta.
4. Servizi di spedizione (`IT_ExpressCourier` con costi di esempio 12 € e 45 €; ritiro con `IT_Pickup`).
5. Adesione alle politiche di vendita (opt-in) e tempo di attivazione.
6. Politica di reso: "14 giorni" potrebbe scontrarsi con la regola dei ricambi auto (30 giorni, reso a carico del venditore, errori 25123 e 25124).
7. Ripubblicazione di un annuncio terminato da eBay e risposta quando per un SKU non esiste ancora un'offerta.
8. Caricamento foto (risposta con l'indirizzo dell'immagine) e categoria suggerita dalla Taxonomy sull'albero 101.
9. Condizioni "Usato ottimo" e "Per ricambi o non funzionante" ammesse nelle categorie dei ricambi.
10. Dove compare l'annuncio di prova: `sandbox.ebay.it` o `sandbox.ebay.com`.
11. Posizione dei dati GPSR (nell'offerta, non nell'articolo).
12. Indirizzo della sede: quello predefinito è fittizio (Roma 00118), va cambiato.

---

## 5. Fisco, pagamenti, spedizioni, firma, conservazione, messaggi

### Fatturazione elettronica (SdI)
Accreditarsi direttamente all'Agenzia ha senso solo con volumi molto alti (certificati, test, conservazione, notifiche per tutte le partite IVA). Meglio un intermediario API:

| Intermediario | Link | API | Costo |
|---|---|---|---|
| **Openapi SDI** | https://console.openapi.com/apis/sdi/pricing | REST, simulazione; firma e conservazione come opzioni | **0,022 €/fattura** con abbonamento (0,070 € base); firma+conservazione 0,052 € |
| **Invoicetronic** | https://invoicetronic.com/pricing/ | REST, webhook, sandbox illimitata; ogni cliente registra il codice destinatario **7HD37X0** | Crediti: 0,10 € → 0,02 €/transazione |
| A-Cube | https://docs.acubeapi.com | Una sola API per SdI, corrispettivi, conservazione, cassetto fiscale; configurazione per partita IVA | Su preventivo |
| Aruba | https://fatturazioneelettronica.aruba.it/apidoc/docs_EN.html | REST, account Premium "multicedente" | Premium/API non pubblico |
| Fatture in Cloud | https://www.fattureincloud.it/costo/ | OAuth2, ma un abbonamento per ogni cliente | 12–51 €/mese per azienda |

### Scontrino al banco (corrispettivi telematici)
- **Registratore telematico (RT)**: oggi la via sicura; dal 1/1/2026 il **POS va collegato all'RT** (servizio attivo dal 5/3/2026). Costo indicativo 150–600 € o abbonamento.
- **Da evitare**: app e API che automatizzano la procedura web "Documento commerciale online" ("velocizzatori"). Il MEF il 4/11/2026 ha detto che non sono autorizzati e che saranno bloccati.
- **In arrivo**: soluzioni software certificate MF1/MF2 (provv. 111204 del 7/3/2025), attese tra fine 2026 e 2027. A-Cube si presenta come produttore: https://docs.acubeapi.com/documentation/italy/ereceipts (verificare l'approvazione).
- **Alternativa sempre lecita**: fattura elettronica B2C per ogni vendita al banco (serve il codice fiscale del cliente).

### Pagamenti
| Fornitore | Link | Commissioni Italia | Note |
|---|---|---|---|
| **Stripe Connect + Terminal** | https://stripe.com/it/pricing · https://stripe.com/it/connect/pricing | Online carte SEE 1,5% + 0,25 €; POS 1,4% + 0,10 €; lettori da 59 € | Connect "Stripe gestisce i prezzi": 0 € per la piattaforma, KYC fatto da Stripe; Satispay attivabile dentro Stripe |
| Nexi | nexi.it | XPay da 1,25% + 0,29 €; SmartPOS 1,89% | Contratto per ogni azienda (da confermare) |
| SumUp | https://www.sumup.com/it-it/tariffe/ | 1,95% in presenza, 2,5% online | — |
| Satispay Business | https://developers.satispay.com | 0,95% sopra 10 € (da confermare) | Sandbox |

### Spedizioni
| Fornitore | Link | Costo | Note |
|---|---|---|---|
| **Sendcloud** | https://www.sendcloud.com/it/prezzi/ | Lite 28 €/mese + 0,10 €/etichetta … Pro 639 € + 0,07 € | API su tutti i piani; ogni cliente carica i propri contratti BRT, GLS, Poste |
| ShippyPro | https://www.shippypro.com/it/prezzi | Da 49 €/mese | API completa solo Enterprise |
| GLS / BRT diretti | gls-group.com · filiale BRT | Contratto del cliente | Per motori, cambi, portiere: servizi pallet; batterie e fluidi sono merci ADR |

### Firma elettronica
| Fornitore | Link | Costo | Note |
|---|---|---|---|
| **Openapi eSignature** (Namirial) | https://console.openapi.com/apis/esignature/pricing | Avanzata (AES) 0,69 € con abbonamento; qualificata da 0,0065 € + certificato 29 € | Firma remota via API |
| Youtrust (ex Yousign) | https://youtrust.com/it-it/prezzi-api | Da 104 €/mese | Sandbox 40 giorni |
| Namirial GraphoKit | — | Su preventivo | Firma grafometrica su tablet: servono informativa, accettazione del firmatario e polizza RC da 500.000 € |

### Conservazione a norma
- Fatture SdI: **servizio gratuito dell'Agenzia** (adesione sul portale Fatture e Corrispettivi, 15 anni) o opzione dell'intermediario (Openapi +0,035 €/fattura).
- Registri, formulari, certificati, contratti firmati: conservatore con API (A-Cube, InfoCert, Aruba DocFly da 25 €/anno), su preventivo.

### WhatsApp (avvisi ai clienti)
- **Meta Cloud API come Tech Provider**: https://developers.facebook.com/docs/whatsapp/solution-providers/get-started-for-tech-providers
- Noi: verifica aziendale Meta, App Review, Embedded Signup. Ogni cliente: proprio account WhatsApp Business e numero, con carta collegata.
- Costo a messaggio (https://developers.facebook.com/docs/whatsapp/pricing); messaggi "utility" (ritiro, spedizione) circa 0,03 $ (da confermare sulla tabella in euro). Dal 1/10/2026 le utility non sono più gratuite nella finestra di 24 ore.

---

## 6. Ordine consigliato

1. **RENTRI** (ambiente demo subito) e **Openapi** (targa, visura, SdI, firma): API pubbliche, sandbox, costi a consumo.
2. **Contatto ACI per il RVFU** (Supporto.Swhouse@informatica.aci.it): senza le specifiche ws la pratica resta manuale sul portale.
3. **Kromeda** (o Infocar): preventivo per uso SaaS multi-cliente.
4. **eBay + Ovoko**, poi Multibreves per B-Parts e altri.
5. **Stripe Connect**, **Sendcloud**.
6. Scontrino: integrazione con l'RT del cliente; soluzione software certificata quando sarà approvata.

## 7. Domande aperte (da chiudere con enti, fornitori e consulenti)
1. RVFU: un SaaS in cloud può scrivere nel registro per conto dei clienti? VPN per cliente? Ambiente di test? Testo della circolare MIT 15/2025 e istruzioni dopo la L. 14/2026.
2. RENTRI: custodia sul server del certificato .p12 di ogni cliente (lecita? con quali garanzie?); firma dei FIR da web app; cadenza esatta di trasmissione del registro per un impianto.
3. Diritti MIT 10,20 € nella radiazione C05332: si pagano o no.
4. Openapi: prezzo reale della visura PRA e utilizzo professionale ripetuto.
5. Licenze SaaS di Kromeda, Infocar, TecDoc; programma per software house di Ovoko; condizioni di B-Parts e API di RicambiPro.
6. Albo: categoria richiesta per ritirare veicoli con carro attrezzi proprio.
7. MUD: tracciato 2026 ufficiale e futuro rispetto a RENTRI. O.R.S.O.: regioni e scadenze.
8. Corrispettivi: registro delle soluzioni software approvate e data di blocco dei "velocizzatori".
9. GDPR: DPA con ogni fornitore (OCR in cloud, visure, firma), nomina a responsabile del trattamento per ogni cliente.
