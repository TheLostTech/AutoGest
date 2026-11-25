import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { connection } from "next/server";
import { Suspense } from "react";
import { BRAND, PRODUTTORE } from "@/lib/config";
import { ORDINE_MODULI } from "@/lib/moduli";
import { LISTINO, euro } from "@/lib/listino";
import { DEMO, Piede, SITO, Testata } from "@/components/sito/Sito";
import { modalitaStripe } from "@/lib/stripe/server";
import { EtichettaStampata, EtichettaPiccola, Percorso } from "./parti";
import { Offerta } from "./offerta";
import "./scopri.css";

export const metadata: Metadata = {
  title: `${BRAND.azienda} · Il gestionale per autodemolizioni`,
  description:
    `Il gestionale per autodemolizioni che ti tiene a norma mentre lavori: bonifica entro i termini, registro rifiuti e RENTRI, formulari digitali, pratica RVFU e radiazione. Poi smontaggio, etichette, magazzino e vendita al banco e online. A moduli, da ${euro(LISTINO.magazzino.mese)} al mese.`,
};

// Solo con le chiavi di prova di Stripe. Si legge alla richiesta (connection): il resto della pagina resta preparato.
async function AvvisoProva() {
  await connection();
  if (modalitaStripe() !== "prova") return null;
  return <p className="mt-2 text-[14px] text-ink-3">Ambiente di prova: nessun addebito vero</p>;
}

const FERMATE = [
  {
    nome: "Accettazione",
    titolo: "Fotografi la targa. Al resto pensa il gestionale.",
    testo:
      "Dalla foto il gestionale legge la targa e recupera marca, modello e telaio. Se un carattere non è sicuro lo evidenzia, così lo controlli prima di salvare. Se il veicolo è già entrato una volta, te lo dice. Il numero della pratica di demolizione resta separato dal numero interno del veicolo: non si confondono mai.",
    oggetto: "targa",
  },
  {
    nome: "Cosa smontare",
    titolo: "Smonti quello che ti manca in magazzino, il sistema te lo dice.",
    testo:
      "Prima di toccare la macchina il gestionale confronta i pezzi recuperabili con lo scaffale e con le soglie che hai deciso tu. Chi smonta vede la lista sul telefono, in ordine di utilità.",
    oggetto: "recupero",
  },
  {
    nome: "Etichetta",
    titolo: "Foto, salva, l'etichetta è già in stampa.",
    testo:
      "Il pezzo eredita marca, modello, targa e pratica dal veicolo: nessuno li riscrive. L'etichetta 100×50 porta un codice solo, con QR e codice a barre. La ristampa tiene lo stesso codice e resta nel registro.",
    oggetto: "etichetta",
  },
  {
    nome: "Scaffale",
    titolo: "Scansioni il pezzo, poi il ripiano. Finito.",
    testo:
      "Magazzino, corsia, scaffale, ripiano, contenitore. Con la fotocamera del telefono o con la pistola laser. Il gestionale ti dice anche il primo posto libero per quel tipo di pezzo.",
    oggetto: "scaffale",
  },
  {
    nome: "Online",
    titolo: "Va online solo quando è completo.",
    testo:
      "Prezzo, foto e provenienza verificata, se no non si pubblica. Il testo dell'annuncio si scrive da solo, i pezzi uguali finiscono nello stesso annuncio. Esce su eBay e sul tuo negozio online.",
    oggetto: "annuncio",
  },
  {
    nome: "Venduto",
    titolo: "Lo stesso pezzo non si vende due volte.",
    testo:
      "Al banco, sul negozio o su eBay: quando qualcuno lo prende, il pezzo è riservato ovunque nello stesso istante. Scontrino o fattura, reso con nota di credito, e la storia del pezzo resta tutta lì.",
    oggetto: "scontrino",
  },
] as const;

// Gli obblighi di legge e chi fa cosa. Termini e fonti come nel codice (periodo.ts, pratica.ts) e nelle news.
const OBBLIGHI = [
  {
    cifra: "10",
    unita: "giorni lavorativi",
    obbligo: "Messa in sicurezza del veicolo dall'ingresso",
    norma: "D.Lgs. 209/2003, art. 6",
    tu: "Fotografi la targa quando il veicolo entra.",
    lui: "Conta i giorni da subito e porta il veicolo in cima alla lista della bonifica prima che scada il termine.",
    modulo: "Magazzino",
  },
  {
    cifra: "2",
    unita: "giorni lavorativi",
    obbligo: "Annotazione nel registro di carico e scarico",
    norma: "D.Lgs. 152/2006, art. 190",
    tu: "Segni la bonifica dal telefono. Le quantità tipiche del modello sono già scritte.",
    lui: "Scrive il carico numerato, con il codice EER e il peso. Le righe ancora da completare te le ricorda.",
    modulo: "Ambiente",
  },
  {
    cifra: "M+1",
    unita: "entro la fine del mese dopo",
    obbligo: "Trasmissione del registro al RENTRI",
    norma: "DM 59/2023, art. 15",
    tu: "Controlli il mese e confermi.",
    lui: "Chiude il periodo, controlla che non manchi niente e prepara l'invio.",
    modulo: "Ambiente",
  },
  {
    cifra: "FIR",
    unita: "solo digitale dal 16/09/2026",
    obbligo: "Formulario di identificazione dei rifiuti",
    norma: "DM 59/2023, art. 7",
    tu: "Firmi il formulario quando passa il trasportatore.",
    lui: "Compila trasportatore e destinatario già salvati, scarica il registro e abbassa la giacenza.",
    modulo: "Ambiente",
  },
  {
    cifra: "kg",
    unita: "per ogni codice EER",
    obbligo: "Quantità massime dell'autorizzazione",
    norma: "D.Lgs. 152/2006, art. 208",
    tu: "Niente.",
    lui: "Mostra quanto manca a ogni limite e ti dice quando programmare il ritiro, prima di sforare.",
    modulo: "Ambiente",
  },
  {
    cifra: "30",
    unita: "giorni dalla consegna",
    obbligo: "Certificato di rottamazione e radiazione dal PRA",
    norma: "RVFU, D.P.R. 177/2022",
    tu: "Fotografi i documenti di chi consegna.",
    lui: "Ti dà l'elenco dei documenti giusto per chi consegna, controlla il fermo amministrativo e conta i 30 giorni.",
    modulo: "Pratiche",
  },
] as const;

const ATTIVAZIONE = [
  { titolo: "Ti registri", testo: "Crei l'account della tua azienda dal sito. Gli accessi dei dipendenti li crei tu, uno per ruolo." },
  { titolo: "Inserisci il primo veicolo", testo: "Fotografi la targa e vedi come lavora sul tuo piazzale, senza pagare niente." },
  { titolo: "Scegli e paghi", testo: "Scegli i moduli e se pagare al mese o all'anno. Paghi con carta su Stripe e i moduli si attivano subito." },
] as const;

// Listino per i motori di ricerca: un'offerta mensile per modulo, IVA esclusa
const OFFERTA_LD = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: BRAND.azienda,
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web",
  url: `${SITO}/scopri`,
  offers: ORDINE_MODULI.map((m) => ({
    "@type": "Offer",
    name: `${BRAND.azienda} ${LISTINO[m].nome}`,
    priceCurrency: "EUR",
    price: (LISTINO[m].mese / 100).toFixed(2),
    priceSpecification: { "@type": "UnitPriceSpecification", price: (LISTINO[m].mese / 100).toFixed(2), priceCurrency: "EUR", billingDuration: "P1M", valueAddedTaxIncluded: false },
  })),
};

export default function ScopriPage() {
  return (
    <div className="scopri min-h-dvh bg-ground text-ink">
      <Testata />

      <main id="contenuto">
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(OFFERTA_LD).replace(/</g, "\\u003c") }} />
        {/* Apertura */}
        <section className="relative overflow-hidden">
          <div className="mx-auto grid max-w-[1240px] gap-2 px-4 pb-20 md:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)] md:gap-12 md:px-8 md:pb-28">
            <div className="order-2 pt-2 md:order-1 md:pt-24">
              <h1 className="scopri-titolo max-w-[13ch] text-balance">Lavori in piazzale. Le carte si fanno da sole.</h1>
              <p className="mt-6 max-w-[54ch] text-[18px] leading-[1.55] text-ink-2 md:text-[20px]">
                Il gestionale per autodemolizioni che ti tiene a norma con il lavoro di tutti i giorni. Fotografi la targa, segni la bonifica, firmi il formulario: pratica,
                registro rifiuti e scadenze si compilano mentre lavori. Nessuna ora persa davanti a un vecchio gestionale a ricopiare dati.
              </p>
              <div className="mt-9 flex flex-wrap gap-3">
                <a href={DEMO} className="inline-flex h-14 items-center rounded-md bg-band px-6 text-[17px] font-semibold text-white hover:bg-band-deep">
                  Apri la demo
                </a>
                <a href="#in-regola" className="inline-flex h-14 items-center rounded-md border border-hair bg-label px-6 text-[17px] font-semibold text-ink hover:border-ink-3">
                  Come ti tiene in regola
                </a>
              </div>
              <p className="mt-6 max-w-[52ch] text-[15px] text-ink-3">
                Gira nel browser: telefono in piazzale, computer al banco, pistola laser in magazzino. Niente da installare sui telefoni.
              </p>
              <Suspense fallback={null}>
                <AvvisoProva />
              </Suspense>
            </div>

            <div className="order-1 md:order-2">
              <div className="scopri-bocca" aria-hidden />
              <div className="scopri-uscita">
                <EtichettaStampata />
              </div>
            </div>
          </div>
        </section>

        {/* In regola: ogni obbligo, cosa fai tu e cosa fa il gestionale */}
        <section id="in-regola" className="scroll-mt-4 border-t border-hair">
          <div className="mx-auto max-w-[1240px] px-4 py-20 md:px-8 md:py-28">
            <div className="grid gap-12 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
              <div>
                <h2 className="scopri-h2 max-w-[15ch]">A norma con il lavoro di tutti i giorni.</h2>
                <p className="mt-5 max-w-[52ch] text-[18px] leading-[1.6] text-ink-2">
                  Ogni gesto in piazzale diventa la riga di registro, il passo della pratica o il promemoria che la legge ti chiede. Nessuno ricopia niente la sera in ufficio.
                </p>
                <p className="mt-4 max-w-[52ch] text-[18px] leading-[1.6] text-ink-2">
                  Le scadenze le conta il gestionale e ti avvisa prima, non dopo. Tu lavori, e quando arriva un controllo è già tutto in ordine.
                </p>
              </div>
              <Registro />
            </div>

            <ul className="mt-16 border-b border-hair">
              {OBBLIGHI.map((o) => (
                <li key={o.obbligo} className="grid gap-x-10 gap-y-4 border-t border-hair py-8 md:grid-cols-[150px_minmax(0,1fr)] lg:grid-cols-[170px_minmax(0,1.1fr)_minmax(0,1fr)_minmax(0,1.2fr)]">
                  <div>
                    <div className="code text-[56px] font-bold leading-[0.9] text-band md:text-[64px]">{o.cifra}</div>
                    <div className="mt-1.5 text-[14px] font-semibold leading-snug text-ink-3">{o.unita}</div>
                  </div>
                  <div>
                    <h3 className="text-[21px] font-bold leading-snug tracking-[-0.01em]">{o.obbligo}</h3>
                    <p className="mt-1.5 text-[15px] text-ink-3">{o.norma}</p>
                    <p className="mt-3 inline-flex h-7 items-center rounded-[4px] bg-band-tint px-2.5 text-[14px] font-semibold text-band">Modulo {o.modulo}</p>
                  </div>
                  <div className="md:col-start-2 lg:col-start-auto">
                    <p className="text-[15px] font-semibold text-ink-3">Tu</p>
                    <p className="mt-1 text-[17px] leading-[1.5] text-ink">{o.tu}</p>
                  </div>
                  <div className="md:col-start-2 lg:col-start-auto">
                    <p className="text-[15px] font-semibold text-ink-3">{BRAND.azienda}</p>
                    <p className="mt-1 text-[17px] leading-[1.5] text-ink">{o.lui}</p>
                  </div>
                </li>
              ))}
            </ul>

            <div className="mt-8 flex flex-wrap items-baseline justify-between gap-x-10 gap-y-4">
              <p className="max-w-[62ch] text-[16px] leading-[1.6] text-ink-2">
                Firme e invii restano a nome tuo, con le tue credenziali RENTRI e RVFU: il gestionale prepara tutto, tu confermi.
              </p>
              <Link href="/news" className="text-[16px] font-semibold text-band underline decoration-band/40 underline-offset-4 hover:decoration-band">
                Le norme spiegate, con le fonti
              </Link>
            </div>
          </div>
        </section>

        {/* Il percorso di un pezzo */}
        <section id="percorso" className="scroll-mt-4 border-t border-hair bg-carton">
          <div className="mx-auto max-w-[1240px] px-4 py-20 md:px-8 md:py-28">
            <h2 className="scopri-h2 max-w-[18ch]">Un faro, dalla targa allo scontrino.</h2>
            <p className="mt-5 max-w-[60ch] text-[18px] leading-[1.55] text-ink-2">
              Ogni ricambio sa da che macchina viene. Segui il faro anteriore sinistro di una Grande Punto: sei fermate, un solo codice, nessun dato ricopiato a mano.
            </p>

            <Percorso>
              {FERMATE.map((f, i) => (
                <li key={f.nome} className="scopri-fermata" data-fermata={i}>
                  <span className="scopri-stazione" aria-hidden>
                    <span />
                  </span>
                  <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:gap-14">
                    <div className="max-w-[50ch]">
                      <p className="code text-[17px] font-semibold text-band">
                        {i + 1}. {f.nome}
                      </p>
                      <h3 className="mt-2 text-[26px] font-bold leading-[1.15] tracking-[-0.02em] text-ink md:text-[32px]">{f.titolo}</h3>
                      <p className="mt-4 text-[17px] leading-[1.6] text-ink-2">{f.testo}</p>
                    </div>
                    <div className="min-w-0">
                      <Oggetto tipo={f.oggetto} />
                    </div>
                  </div>
                </li>
              ))}
            </Percorso>
          </div>
        </section>

        {/* Quanto costa: la base, i moduli che si aggiungono e come si attivano */}
        <section id="costo" className="scroll-mt-4 border-t border-hair bg-carton">
          <div className="mx-auto max-w-[1240px] px-4 py-20 md:px-8 md:py-28">
            <h2 className="scopri-h2 max-w-[17ch]">Paghi il magazzino. Il resto quando ti serve.</h2>
            <p className="mt-5 max-w-[62ch] text-[18px] leading-[1.6] text-ink-2">
              Il Magazzino è la base e c&apos;è sempre: veicoli, smontaggio, etichette, scaffali e vendita online. Pratiche, Ambiente e Banco si aggiungono uno per uno, quando ti
              servono. Quelli che non hai li vedi nel gestionale, bloccati, e li attivi da lì.
            </p>
            <Offerta />

            <div className="mt-20 grid gap-12 border-t border-hair pt-14 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
              <div>
                <h3 className="text-[28px] font-bold tracking-[-0.02em]">Come si attiva</h3>
                <ol className="mt-6 grid gap-6 md:grid-cols-3">
                  {ATTIVAZIONE.map((p, i) => (
                    <li key={p.titolo}>
                      <span className="code grid size-10 place-items-center rounded-full bg-band text-[20px] font-bold text-white" aria-hidden>
                        {i + 1}
                      </span>
                      <h4 className="mt-3 text-[20px] font-bold leading-snug">{p.titolo}</h4>
                      <p className="mt-1.5 text-[16px] leading-[1.55] text-ink-2">{p.testo}</p>
                    </li>
                  ))}
                </ol>
              </div>
              <div>
                <h3 className="text-[28px] font-bold tracking-[-0.02em]">E sui pezzi venduti</h3>
                <p className="mt-4 text-[17px] leading-[1.6] text-ink-2">
                  Il prezzo del pezzo lo decidi tu. Quando esce online, su eBay o sul tuo negozio, il gestionale ci aggiunge l&apos;8%: lo fatturiamo solo sui pezzi venduti, e se
                  il pezzo torna indietro si storna. Su un faro da 120,00 € il prezzo online è 129,60 €.
                </p>
                <p className="mt-3 text-[17px] leading-[1.6] text-ink-2">Al banco non aggiungiamo niente.</p>
              </div>
            </div>
          </div>
        </section>

        {/* Chiusura: la scatola */}
        <section className="relative overflow-hidden bg-band text-white">
          <div className="mx-auto grid max-w-[1240px] items-center gap-6 px-4 pt-20 md:px-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:py-24">
            <div className="relative z-10">
              <h2 className="scopri-h2 max-w-[15ch] text-white">Vieni a vederlo su una macchina vera.</h2>
              <p className="mt-5 max-w-[50ch] text-[18px] leading-[1.6] text-white/85">
                Portiamo il gestionale nel tuo piazzale: un veicolo in accettazione, i pezzi etichettati e messi a scaffale, uno venduto. Poi decidi.
              </p>
              <div className="mt-9 flex flex-wrap gap-3">
                <a href={DEMO} className="inline-flex h-14 items-center rounded-md bg-label px-6 text-[17px] font-semibold text-band hover:bg-band-tint">
                  Apri la demo
                </a>
                <a
                  href={PRODUTTORE.sito}
                  target="_blank"
                  rel="noopener"
                  className="inline-flex h-14 items-center rounded-md border border-white/40 px-6 text-[17px] font-semibold text-white hover:bg-white/10"
                >
                  Contatta {PRODUTTORE.nome}
                </a>
              </div>
            </div>
            <div className="relative -mx-4 md:mx-0">
              <Image
                src="/renders/scatola-wide.png"
                alt="Scatola ricambio bianca con la fascia blu e l'etichetta"
                width={1600}
                height={900}
                className="w-full max-w-none translate-x-[6%] lg:w-[125%] lg:translate-x-[4%]"
                priority={false}
              />
            </div>
          </div>
        </section>
      </main>

      <Piede />
    </div>
  );
}

/* Gli oggetti di ogni fermata: disegnati come nel gestionale */

function Oggetto({ tipo }: { tipo: (typeof FERMATE)[number]["oggetto"] }) {
  switch (tipo) {
    case "targa":
      return <Targa />;
    case "recupero":
      return <Recupero />;
    case "etichetta":
      return <EtichettaPiccola />;
    case "scaffale":
      return <Scaffale />;
    case "annuncio":
      return <Annuncio />;
    case "scontrino":
      return <Venduto />;
  }
}

function Targa() {
  return (
    <div className="label-sheet p-5 md:p-6">
      <div className="flex flex-wrap items-center gap-5">
        <div className="scopri-targa" aria-label="Targa GH 482 KL">
          <span className="scopri-targa-lato" aria-hidden>
            I
          </span>
          <span className="code px-4 text-[44px] font-bold leading-none tracking-[0.04em] md:text-[52px]">
            GH 482 K<span className="scopri-incerto">L</span>
          </span>
          <span className="scopri-targa-lato" aria-hidden />
        </div>
        <div>
          <div className="code text-[34px] font-bold leading-none">V-000118</div>
          <div className="mt-1 text-[15px] font-semibold text-ink-2">Fiat Grande Punto 1.3 Multijet · 2011</div>
        </div>
      </div>
      <dl className="mt-5 grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 border-t border-hair-soft pt-4 text-[15px]">
        <dt className="font-semibold text-ink-3">Telaio</dt>
        <dd className="code text-[17px] font-semibold">ZFA19900001234567</dd>
        <dt className="font-semibold text-ink-3">Da controllare</dt>
        <dd className="text-ink-2">
          Ultimo carattere: <b className="code text-[17px] text-warn">L</b> o <b className="code text-[17px] text-warn">I</b>?
        </dd>
        <dt className="font-semibold text-ink-3">Già entrato</dt>
        <dd className="text-ink-2">No, targa e telaio nuovi</dd>
      </dl>
    </div>
  );
}

function Recupero() {
  const righe = [
    { pezzo: "Faro anteriore sx", scorta: 0, min: 2, stato: "Da recuperare", cls: "bg-band text-white" },
    { pezzo: "Specchietto dx", scorta: 1, min: 2, stato: "Da recuperare", cls: "bg-band text-white" },
    { pezzo: "Alternatore", scorta: 4, min: 3, stato: "Se c'è tempo", cls: "bg-label text-ink-2 border border-hair" },
    { pezzo: "Cerchio in lega", scorta: 11, min: 4, stato: "Pieno", cls: "bg-label text-ink-3 border border-dashed border-hair" },
  ];
  return (
    <div className="label-sheet overflow-hidden">
      <div className="flex items-baseline justify-between gap-3 bg-band px-5 py-3 text-white">
        <span className="code whitespace-nowrap text-[22px] font-bold leading-none">V-000118</span>
        <span className="truncate text-[14px] font-semibold text-white/80">Grande Punto · GH 482 KL</span>
      </div>
      <ul>
        {righe.map((r) => (
          <li key={r.pezzo} className="flex flex-wrap items-center gap-x-3 gap-y-1.5 border-t border-hair-soft px-5 py-3.5 first:border-t-0">
            <span className="min-w-0 basis-full text-[16px] font-semibold sm:flex-1 sm:basis-auto">{r.pezzo}</span>
            <span className="code text-[17px] text-ink-2 sm:w-[72px] sm:text-right">
              <b className="text-ink">{r.scorta}</b> / {r.min}
            </span>
            <span className={`code ml-auto inline-flex h-7 w-[118px] items-center sm:ml-0 justify-center rounded-[4px] text-[14px] font-semibold ${r.cls}`}>{r.stato}</span>
          </li>
        ))}
      </ul>
      <p className="border-t border-hair-soft bg-carton px-5 py-2.5 text-[13px] text-ink-3">A scaffale / scorta minima che hai deciso tu</p>
    </div>
  );
}

function Scaffale() {
  const passi = [
    ["Magazzino", "3"],
    ["Corsia", "T03"],
    ["Scaffale", "104"],
    ["Ripiano", "B"],
    ["Contenitore", "1"],
  ];
  return (
    <div className="label-sheet @container p-5 md:p-6">
      <div className="code whitespace-nowrap text-[min(15cqw,88px)] font-bold leading-[0.9] tracking-[-0.01em]">3/T03-104-B-1</div>
      <ol className="mt-5 grid grid-cols-3 gap-1.5 sm:grid-cols-5">
        {passi.map(([n, v]) => (
          <li key={n} className="rounded-[4px] bg-band-tint px-2 py-2">
            <div className="code text-[20px] font-bold leading-none text-band">{v}</div>
            <div className="mt-1 truncate text-[12px] font-semibold text-ink-2">{n}</div>
          </li>
        ))}
      </ol>
      <p className="mt-4 flex items-center gap-2 text-[15px] font-semibold text-ok">
        <span className="inline-block size-2.5 rounded-full bg-ok" aria-hidden />
        R-000417 caricato sul ripiano B
      </p>
    </div>
  );
}

function Annuncio() {
  const controlli = ["Prezzo", "3 foto", "Provenienza verificata", "Compatibilità confermata"];
  return (
    <div className="label-sheet grid overflow-hidden sm:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
      <div className="relative bg-white">
        <Image src="/renders/faro.png" alt="Faro anteriore sinistro" width={1024} height={1024} className="aspect-[4/3] w-full object-cover sm:aspect-square" />
      </div>
      <div className="flex flex-col p-5">
        <p className="text-[17px] font-bold leading-snug">Faro anteriore sinistro Fiat Grande Punto 2005–2012</p>
        <p className="code mt-1 text-[15px] text-ink-3">R-000417 · Usato, condizioni B</p>
        <div className="code mt-3 text-[40px] font-bold leading-none">129,60 €</div>
        <ul className="mt-4 space-y-1.5 text-[15px]">
          {controlli.map((c) => (
            <li key={c} className="flex items-center gap-2">
              <svg viewBox="0 0 16 16" className="size-4 shrink-0 text-ok" aria-hidden>
                <path d="M3 8.5l3.2 3L13 4.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              {c}
            </li>
          ))}
        </ul>
        <div className="mt-auto flex flex-wrap gap-2 pt-4">
          <span className="inline-flex h-7 items-center gap-1.5 rounded-[4px] bg-band-tint px-2.5 text-[14px] font-semibold text-band">
            <span className="size-2 rounded-full bg-band" aria-hidden />
            eBay
          </span>
          <span className="inline-flex h-7 items-center gap-1.5 rounded-[4px] bg-band-tint px-2.5 text-[14px] font-semibold text-band">
            <span className="size-2 rounded-full bg-band" aria-hidden />
            {BRAND.negozio}
          </span>
        </div>
      </div>
    </div>
  );
}

function Venduto() {
  return (
    <div className="flex flex-wrap items-start gap-5">
      <div className="label-sheet w-full max-w-[360px] p-5">
        <div className="flex items-center justify-between gap-3">
          <span className="code text-[28px] font-bold leading-none">R-000417</span>
          <span className="code inline-flex h-7 items-center rounded-[4px] bg-ink px-2.5 text-[14px] font-semibold text-white">Venduto</span>
        </div>
        <ol className="mt-4 space-y-2 text-[15px]">
          <li className="flex justify-between gap-3">
            <span className="text-ink-2">Ordine eBay pagato</span>
            <span className="code text-ink-3">10:42:07</span>
          </li>
          <li className="flex justify-between gap-3">
            <span className="text-ink-2">Riservato su banco e negozio</span>
            <span className="code text-ink-3">10:42:07</span>
          </li>
          <li className="flex justify-between gap-3 text-danger">
            <span>Banco: già venduto, non aggiunto</span>
            <span className="code">10:42:09</span>
          </li>
        </ol>
      </div>
      <p className="max-w-[28ch] pt-2 text-[15px] leading-[1.55] text-ink-3">
        Due secondi dopo, al banco, qualcuno prova a battere lo stesso faro. Il gestionale lo ferma.
      </p>
    </div>
  );
}

function Registro() {
  const righe = [
    { eer: "13 02 05*", cosa: "Olio motore esausto", kg: 1240, limite: 3000 },
    { eer: "16 06 01*", cosa: "Batterie al piombo", kg: 2890, limite: 3500 },
    { eer: "16 01 07*", cosa: "Filtri dell'olio", kg: 180, limite: 600 },
    { eer: "16 01 14*", cosa: "Liquido antigelo", kg: 410, limite: 1500 },
  ];
  return (
    <div className="label-sheet self-start overflow-hidden">
      <div className="flex items-baseline justify-between gap-3 border-b border-hair-soft px-5 py-3.5">
        <span className="text-[16px] font-bold">Giacenze rispetto all&apos;autorizzazione</span>
        <span className="text-[13px] text-ink-3">Dati di esempio</span>
      </div>
      <ul>
        {righe.map((r) => {
          const p = r.kg / r.limite;
          const vicino = p > 0.8;
          return (
            <li key={r.eer} className="border-t border-hair-soft px-5 py-4 first:border-t-0">
              <div className="flex flex-wrap items-baseline gap-x-3">
                <span className="code w-[92px] shrink-0 text-[18px] font-bold">{r.eer}</span>
                <span className="order-last min-w-0 basis-full text-[15px] font-semibold text-ink-2 sm:order-none sm:flex-1 sm:basis-auto">{r.cosa}</span>
                <span className={`code ml-auto text-[17px] sm:ml-0 ${vicino ? "font-bold text-warn" : "text-ink-2"}`}>
                  {r.kg.toLocaleString("it-IT")} / {r.limite.toLocaleString("it-IT")} kg
                </span>
              </div>
              <div className="mt-2 h-2 rounded-full bg-hair-soft" aria-hidden>
                <div className={`h-2 rounded-full ${vicino ? "bg-warn" : "bg-band"}`} style={{ width: `${Math.round(p * 100)}%` }} />
              </div>
              {vicino && <p className="mt-1.5 text-[14px] font-semibold text-warn">Vicino al limite: programma il ritiro.</p>}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
