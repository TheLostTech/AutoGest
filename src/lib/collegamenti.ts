// Impostazioni → Collegamenti: i servizi esterni del gestionale e cosa serve per collegarli.
// Usato sia dalla pagina sia dal server (che accetta solo i campi elencati qui).
// Costi e fonti: docs/INTEGRAZIONI.md, sezione 0. Nel prototipo è attiva solo la visura PRA di Openapi (visura-server.ts):
// per gli altri si salvano i dati, le chiamate vere arrivano con l'integrazione di ogni servizio.

export type CampoTipo = "testo" | "segreto" | "file" | "scelta" | "multipla";

export interface Campo {
  key: string;
  label: string;
  tipo: CampoTipo;
  hint?: string;
  placeholder?: string;
  opzioni?: string[]; // per "scelta" e "multipla"
  accept?: string; // per "file"
  facoltativo?: boolean;
}

// Come si entra nel servizio
export type Accesso = "spid" | "registrazione" | "fornitore";
// Come lavora il gestionale con il servizio
export type Modo = "api" | "portale" | "file" | "dispositivo";

export interface Servizio {
  id: string;
  nome: string;
  gruppo: "legge" | "consumo";
  uso: string; // dove serve nell'app
  costo: string;
  accesso: Accesso;
  modo: Modo;
  link?: { label: string; href: string };
  nota: string;
  campi: Campo[];
}

export const ACCESSO: Record<Accesso, { label: string; spiega: string }> = {
  spid: {
    label: "SPID del titolare",
    spiega: "Si entra con SPID, CIE o CNS personale del titolare o legale rappresentante. Lo SPID non si salva nel gestionale.",
  },
  registrazione: { label: "Registrazione", spiega: "Account online con email e partita IVA." },
  fornitore: { label: "Dal fornitore", spiega: "Si acquista da un fornitore, che rilascia i dati di accesso." },
};

export const MODO: Record<Modo, string> = {
  api: "Collegamento via API",
  portale: "Solo dal portale",
  file: "File da caricare sul portale",
  dispositivo: "Apparecchio in sede",
};

const AMBIENTE = (prova: string): Campo => ({
  key: "ambiente",
  label: "Ambiente",
  tipo: "scelta",
  opzioni: [prova, "Produzione"],
  hint: "Si parte sempre dall'ambiente di prova.",
});

export const SERVIZI: Servizio[] = [
  // ── Obbligatori per legge: l'accesso è con lo SPID del titolare ──
  {
    id: "rvfu",
    nome: "RVFU · Registro veicoli fuori uso",
    gruppo: "legge",
    uso: "Pratica: presa in carico, certificato di rottamazione, radiazione",
    costo: "32 € di bollo + 13,50 € di emolumenti a radiazione (+10,20 € di diritti MIT, da confermare). VPN e firma remota ACI: prezzo non pubblico",
    accesso: "spid",
    modo: "api",
    link: { label: "Portale del Trasporto", href: "https://www.ilportaledeltrasporto.it/web/ptr/" },
    nota: "Le specifiche dei web service sono riservate: utenza e indirizzo li fornisce ACI dopo l'accreditamento della sede (Supporto.Swhouse@informatica.aci.it). Il collegamento passa dalla VPN ACI.",
    campi: [
      { key: "cfTitolare", label: "Codice fiscale del titolare", tipo: "testo", placeholder: "RSSMRA70A01H501U" },
      { key: "sede", label: "Codice della sede accreditata", tipo: "testo", hint: "Un accreditamento per ogni sede." },
      { key: "utente", label: "Utenza web service", tipo: "testo", hint: "Rilasciata da ACI." },
      { key: "password", label: "Password web service", tipo: "segreto" },
      { key: "endpoint", label: "Indirizzo del servizio", tipo: "testo", placeholder: "https://…", hint: "Dalle specifiche ACI." },
      AMBIENTE("Test ACI"),
    ],
  },
  {
    id: "rentri",
    nome: "RENTRI · Registro e formulari",
    gruppo: "legge",
    uso: "Ambiente: registro di carico e scarico, formulari digitali",
    costo: "Iscrizione 10 €; 100 € il primo anno, poi 60 €/anno per sede. Le API sono gratuite",
    accesso: "spid",
    modo: "api",
    link: { label: "Area operatori RENTRI", href: "https://operatori.rentri.gov.it" },
    nota: "Il certificato di interoperabilità si scarica dall'area operatori, sezione Interoperabilità. Serve per le API ma non firma i formulari: per quelli serve la firma digitale.",
    campi: [
      { key: "cfOperatore", label: "Codice fiscale dell'operatore", tipo: "testo", hint: "Della società iscritta." },
      { key: "unita", label: "Numero di iscrizione dell'unità locale", tipo: "testo" },
      { key: "certificato", label: "Certificato di interoperabilità", tipo: "file", accept: ".p12,.pfx", hint: "File .p12 o .pfx." },
      { key: "passwordCertificato", label: "Password del certificato", tipo: "segreto" },
      AMBIENTE("Demo RENTRI"),
    ],
  },
  {
    id: "mud",
    nome: "MUD · Comunicazione veicoli fuori uso",
    gruppo: "legge",
    uso: "Ambiente: dichiarazione annuale",
    costo: "10 €/anno. Serve anche la firma digitale",
    accesso: "spid",
    modo: "file",
    link: { label: "MUD Telematico", href: "https://www.mudtelematico.it" },
    nota: "Nessuna API: il gestionale prepara il file e chi dichiara lo carica sul portale con SPID e firma digitale. Può inviarlo anche un consulente con delega.",
    campi: [
      { key: "cfDichiarante", label: "Codice fiscale del dichiarante", tipo: "testo" },
      { key: "consulente", label: "Consulente che invia", tipo: "testo", placeholder: "Nome e PEC", facoltativo: true },
    ],
  },
  {
    id: "agenzia-entrate",
    nome: "Agenzia Entrate · Fatture e Corrispettivi",
    gruppo: "legge",
    uso: "Vendite: ricezione fatture e conservazione",
    costo: "Gratis, compresa la conservazione delle fatture",
    accesso: "spid",
    modo: "portale",
    link: { label: "Fatture e Corrispettivi", href: "https://ivaservizi.agenziaentrate.gov.it/portale/" },
    nota: "Sul portale il titolare registra il codice destinatario del servizio di fatturazione e aderisce alla conservazione gratuita. L'invio delle fatture passa dal servizio scelto (es. Openapi).",
    campi: [
      { key: "piva", label: "Partita IVA", tipo: "testo", placeholder: "01234567890" },
      { key: "codiceDestinatario", label: "Codice destinatario registrato", tipo: "testo", placeholder: "7 caratteri", hint: "Quello del servizio che invia e riceve le fatture." },
      { key: "conservazione", label: "Conservazione gratuita", tipo: "scelta", opzioni: ["Non attivata", "Attivata sul portale"] },
    ],
  },
  {
    id: "orso",
    nome: "O.R.S.O. · Osservatorio rifiuti regionale",
    gruppo: "legge",
    uso: "Ambiente: dichiarazione regionale",
    costo: "Gratis (da verificare per regione)",
    accesso: "spid",
    modo: "file",
    nota: "Applicativo regionale: si carica lo stesso file del MUD. Accesso e scadenze cambiano da regione a regione.",
    campi: [
      { key: "regione", label: "Regione", tipo: "testo" },
      { key: "codiceImpianto", label: "Codice impianto in O.R.S.O.", tipo: "testo" },
    ],
  },
  {
    id: "firma",
    nome: "Firma digitale qualificata",
    gruppo: "legge",
    uso: "RVFU, MUD e formulari",
    costo: "Da 29 € il certificato",
    accesso: "fornitore",
    modo: "api",
    link: { label: "Openapi eSignature", href: "https://console.openapi.com/apis/esignature/pricing" },
    nota: "PIN e codice OTP non si salvano: chi firma li inserisce ogni volta, perché la firma resta sotto il suo controllo esclusivo.",
    campi: [
      { key: "fornitore", label: "Fornitore", tipo: "scelta", opzioni: ["Openapi / Namirial", "Aruba", "InfoCert", "ACI (per il RVFU)", "Altro"] },
      { key: "cfFirmatario", label: "Codice fiscale di chi firma", tipo: "testo" },
      { key: "utente", label: "Utente della firma remota", tipo: "testo" },
      { key: "scadenza", label: "Scadenza del certificato", tipo: "testo", placeholder: "gg/mm/aaaa", facoltativo: true },
    ],
  },
  {
    id: "rt",
    nome: "Registratore telematico",
    gruppo: "legge",
    uso: "Vendite: scontrino al banco",
    costo: "150–600 € o canone",
    accesso: "fornitore",
    modo: "dispositivo",
    nota: "Lo installa e lo attiva un tecnico abilitato. Dal 2026 il POS va collegato al registratore. Il gestionale gli manda lo scontrino sulla rete del negozio.",
    campi: [
      { key: "modello", label: "Marca e modello", tipo: "testo" },
      { key: "matricola", label: "Matricola", tipo: "testo" },
      { key: "indirizzo", label: "Indirizzo nella rete del negozio", tipo: "testo", placeholder: "192.168.1.50" },
    ],
  },

  // ── A consumo, con registrazione normale ──
  {
    id: "openapi",
    nome: "Openapi",
    gruppo: "consumo",
    uso: "Dati da targa, visura PRA, fattura elettronica, firma",
    costo: "Targa 0,40 € a chiamata; visura PRA 10,90 o 16,70 € (da confermare); fattura 0,02–0,07 €; firma avanzata 0,69 €",
    accesso: "registrazione",
    modo: "api",
    link: { label: "Console Openapi", href: "https://console.openapi.com" },
    nota: "Un solo account per tutti i servizi. Il token si crea nella console; la prova (sandbox) è gratuita. La visura PRA è già collegata: con \"Visura PRA\" tra i servizi si richiede dal passo 2 della pratica.",
    campi: [
      { key: "email", label: "Email dell'account", tipo: "testo" },
      { key: "token", label: "Token API", tipo: "segreto" },
      { key: "servizi", label: "Servizi da usare", tipo: "multipla", opzioni: ["Dati tecnici da targa", "Visura PRA", "Fattura elettronica (SdI)", "Firma elettronica"] },
      AMBIENTE("Sandbox"),
    ],
  },
  {
    id: "platerecognizer",
    nome: "Plate Recognizer",
    gruppo: "consumo",
    uso: "Accettazione: lettura della targa dalla foto",
    costo: "Gratis fino a 2.500 al mese in prova, poi da 50 $/mese",
    accesso: "registrazione",
    modo: "api",
    link: { label: "Plate Recognizer", href: "https://platerecognizer.com/pricing/" },
    nota: "Conserva le immagini 30 giorni di serie: va firmato l'accordo sul trattamento dei dati (GDPR).",
    campi: [{ key: "token", label: "Token API", tipo: "segreto" }],
  },
  {
    id: "ia",
    nome: "IA per riconoscere i pezzi",
    gruppo: "consumo",
    uso: "Smontaggio e inventario: pezzo riconosciuto dalla foto",
    costo: "Pochi centesimi a foto (da stimare)",
    accesso: "registrazione",
    modo: "api",
    nota: "Per un fornitore fuori dall'UE va verificato il trasferimento dei dati (GDPR).",
    campi: [
      { key: "fornitore", label: "Fornitore", tipo: "scelta", opzioni: ["Anthropic (Claude)", "OpenAI", "Google (Gemini)"] },
      { key: "chiave", label: "Chiave API", tipo: "segreto" },
      { key: "modello", label: "Modello", tipo: "testo", hint: "Il nome del modello indicato dal fornitore." },
    ],
  },
  {
    id: "sendcloud",
    nome: "Sendcloud",
    gruppo: "consumo",
    uso: "Vendite: etichette di spedizione",
    costo: "28 €/mese + 0,10 € a etichetta",
    accesso: "registrazione",
    modo: "api",
    link: { label: "Sendcloud", href: "https://www.sendcloud.com/it/prezzi/" },
    nota: "Le chiavi si creano in Impostazioni → Integrazioni di Sendcloud. I contratti con BRT, GLS e Poste restano dell'azienda.",
    campi: [
      { key: "publicKey", label: "Chiave pubblica", tipo: "testo" },
      { key: "secretKey", label: "Chiave segreta", tipo: "segreto" },
    ],
  },
  {
    id: "ebay",
    nome: "eBay",
    gruppo: "consumo",
    uso: "Vendite: annunci su eBay Italia",
    costo: "Il Developers Program è gratuito; su eBay si pagano le commissioni di vendita",
    accesso: "registrazione",
    modo: "api",
    link: { label: "eBay Developers Program", href: "https://developer.ebay.com/" },
    nota: "Simulato finché non scegli Sandbox e inserisci le chiavi di prova (Sandbox) del Developers Program; poi tocca «Collega account eBay» qui sotto e accedi con un utente di prova di eBay.",
    campi: [
      { key: "ambiente", label: "Ambiente", tipo: "scelta", opzioni: ["Simulato", "Sandbox"] },
      { key: "appId", label: "App ID (Client ID)", tipo: "testo" },
      { key: "certId", label: "Cert ID (Client Secret)", tipo: "segreto" },
      { key: "ruName", label: "RuName (nome dell'indirizzo di ritorno)", tipo: "testo", facoltativo: true, hint: "Facoltativo con l'ambiente Simulato. Su eBay deve rimandare a https://<indirizzo del tunnel>/api/ebay/ritorno." },
    ],
  },
  {
    id: "whatsapp",
    nome: "WhatsApp Business",
    gruppo: "consumo",
    uso: "Avvisi ai clienti (ritiro, spedizione)",
    costo: "Circa 0,03 $ ad avviso",
    accesso: "registrazione",
    modo: "api",
    link: { label: "Meta per sviluppatori", href: "https://developers.facebook.com/docs/whatsapp/cloud-api" },
    nota: "Meta verifica l'azienda con i documenti, non con lo SPID. Servono un numero dedicato e una carta collegata.",
    campi: [
      { key: "numero", label: "Numero WhatsApp", tipo: "testo", placeholder: "+39…" },
      { key: "phoneId", label: "ID del numero (Phone number ID)", tipo: "testo" },
      { key: "wabaId", label: "ID account WhatsApp Business", tipo: "testo" },
      { key: "token", label: "Token di accesso", tipo: "segreto" },
    ],
  },
  {
    id: "visurenet",
    nome: "ACI Visurenet",
    gruppo: "consumo",
    uso: "Pratica: visura PRA fatta a mano",
    costo: "6 € a visura",
    accesso: "spid",
    modo: "portale",
    link: { label: "Visurenet", href: "https://aci.gov.it/servizio/visurenet-visura-della-banca-dati-del-pubblico-registro-automobilistico-pra/" },
    nota: "Entra con lo SPID di chiunque, massimo 3 visure al giorno, senza API: si fa a mano e il PDF si allega alla pratica. Per farle dal gestionale si usa Openapi.",
    campi: [],
  },
];

export const servizioById = (id: string) => SERVIZI.find((s) => s.id === id);

// Quello che il server restituisce: i segreti e i file non tornano mai indietro, solo se ci sono
export interface StatoServizio {
  valori: Record<string, string | string[]>;
  segreti: Record<string, boolean>;
  file: Record<string, { nome: string; byte: number }>;
  aggiornato?: string;
}

export function completo(s: Servizio, st?: StatoServizio) {
  if (!s.campi.length) return true;
  if (!st) return false;
  return s.campi.every((c) => {
    if (c.tipo === "segreto") return !!st.segreti[c.key];
    if (c.tipo === "file") return !!st.file[c.key];
    if (c.facoltativo) return true;
    const v = st.valori[c.key];
    return Array.isArray(v) ? v.length > 0 : !!v?.trim();
  });
}
