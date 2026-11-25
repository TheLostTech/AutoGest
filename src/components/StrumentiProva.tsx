"use client";

// Strumenti di prova sulla pagina Abbonamento, solo con le chiavi di prova. Due casi:
// - durante la prova gratuita (stato "nuovo" con la prova partita; spec prova-15-giorni, sezione 4) il cliente Stripe
//   non c'è ancora: "+1 giorno" e "+1 settimana" spostano l'orologio dell'app (POST /api/abbonamento/prova/sposta) e
//   la risposta aggiorna subito fascia e blocco;
// - dopo il pagamento (spec registrazione-pagamento, sezione 7), con un orologio di prova di Stripe: i pulsanti fanno
//   avanzare l'orologio (POST /api/abbonamento/prova/avanza); poi ogni 2 secondi, per al massimo un minuto, si rilegge
//   lo stato con quello dell'orologio finché Stripe ha finito: il server sincronizza appena l'orologio è pronto e il
//   conto alla rovescia si aggiorna.
// In tutti e due i casi l'orologio va solo avanti.
import { useEffect, useRef, useState, type ReactNode } from "react";
import { avanzamentoPermesso, oraProva, type Abbonamento, type Passo, type PassoProva } from "@/lib/abbonamento";
import { fetchAzienda } from "@/lib/accesso/azienda-client";
import { controllaOrologio, mettiAbbonamento } from "@/lib/use-abbonamento";
import { useOra } from "@/lib/use-ora";
import { Button } from "@/components/ui";

const PASSI: { passo: Passo; etichetta: string }[] = [
  { passo: "giorno", etichetta: "+1 giorno" },
  { passo: "settimana", etichetta: "+1 settimana" },
  { passo: "mese", etichetta: "+1 mese" },
  { passo: "anno", etichetta: "+1 anno" },
];
const OGNI_MS = 2_000;
const AL_MASSIMO_MS = 60_000;
const DATA = new Intl.DateTimeFormat("it-IT", { timeZone: "Europe/Rome", day: "2-digit", month: "2-digit", year: "numeric" });
const pausa = (ms: number) => new Promise((r) => setTimeout(r, ms));

// Ricontrolla ogni 2 secondi finché Stripe ha finito: orologio pronto e, se si sa, ora salvata arrivata ad `arrivo` (ms).
// "via": la pagina è stata chiusa nel frattempo.
async function aspettaOrologio(arrivo: number | null, vivo: { current: boolean }): Promise<"pronto" | "tardi" | "via"> {
  const fine = Date.now() + AL_MASSIMO_MS;
  while (Date.now() < fine) {
    await pausa(OGNI_MS);
    if (!vivo.current) return "via";
    const d = await controllaOrologio();
    const ora = d?.abbonamento?.oraOrologio ?? null;
    if (d?.orologioPronto === true && (arrivo === null || (ora !== null && ora >= arrivo))) return "pronto";
  }
  return vivo.current ? "tardi" : "via";
}

const TARDI = "Stripe sta ancora facendo avanzare l'orologio: ricarica la pagina tra poco.";

type RispostaAvanza = { frozenTime?: number; error?: string };
type Messaggio = { tono: "ok" | "warn" | "danger"; testo: string };
const TONI: Record<Messaggio["tono"], string> = { ok: "text-ok", warn: "text-warn", danger: "bg-danger-bg text-danger" };

// La prova gratuita è partita e non è ancora stata pagata: si sposta l'orologio dell'app, non quello di Stripe
export const conProvaGratuita = (a: Abbonamento) => a.stato === "nuovo" && a.fineProva !== null;

// negata: entrati con il PIN, l'orologio si guarda ma non si fa avanzare (serve l'accesso con email e password)
export function StrumentiProva({ abbonamento, negata }: { abbonamento: Abbonamento; negata: string | null }) {
  return conProvaGratuita(abbonamento) ? <StrumentiProvaGratuita abbonamento={abbonamento} negata={negata} /> : <StrumentiOrologio abbonamento={abbonamento} negata={negata} />;
}

function Sezione({ data, spiegazione, negata, pulsanti, stato }: { data: string; spiegazione: string; negata: string | null; pulsanti: ReactNode; stato: ReactNode }) {
  return (
    <section className="mt-5 rounded-md border border-dashed border-hair bg-carton px-4 py-4 md:px-5" aria-labelledby="strumenti-prova">
      <h2 id="strumenti-prova" className="code text-[12px] font-bold uppercase tracking-[0.14em] text-ink-3">
        Strumenti di prova
      </h2>
      <p className="mt-2 text-[17px] font-semibold">
        Data di prova: <span className="code tabular-nums">{data}</span>
      </p>
      <p className="mt-1 text-[14px] text-ink-3">{spiegazione}</p>
      {negata ? <p className="mt-3 text-[15px] font-semibold text-warn">{negata}</p> : <div className="mt-3 flex flex-wrap gap-2">{pulsanti}</div>}
      <div aria-live="polite" className="mt-2 min-h-6 text-[15px]">
        {stato}
      </div>
    </section>
  );
}

function Esito({ messaggio }: { messaggio: Messaggio | null }) {
  if (!messaggio) return null;
  return (
    <p role={messaggio.tono === "danger" ? "alert" : undefined} className={`rounded-md font-medium ${messaggio.tono === "danger" ? "px-3 py-2" : ""} ${TONI[messaggio.tono]}`}>
      {messaggio.testo}
    </p>
  );
}

const PASSI_PROVA: { passo: PassoProva; etichetta: string }[] = [
  { passo: "giorno", etichetta: "+1 giorno" },
  { passo: "settimana", etichetta: "+1 settimana" },
];

type RispostaSposta = { abbonamento?: Abbonamento; error?: string };
// La data con cui si conta la prova in questo momento (ora del browser più lo spostamento)
const dataProvaAdesso = (a: Abbonamento) => DATA.format(new Date(oraProva(a, Date.now())));

function StrumentiProvaGratuita({ abbonamento: a, negata }: { abbonamento: Abbonamento; negata: string | null }) {
  const ora = useOra();
  const [invio, setInvio] = useState(false);
  const [messaggio, setMessaggio] = useState<Messaggio | null>(null);

  async function sposta(passo: PassoProva) {
    setMessaggio(null);
    setInvio(true);
    try {
      const r = await fetchAzienda("/api/abbonamento/prova/sposta", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ passo }) });
      const j = (await r.json().catch(() => null)) as RispostaSposta | null;
      if (r.ok && j?.abbonamento) {
        // La copia condivisa si aggiorna subito: se la prova è finita si apre il riquadro di pagamento
        mettiAbbonamento(j.abbonamento);
        setMessaggio({ tono: "ok", testo: `Data di prova portata al ${dataProvaAdesso(j.abbonamento)}.` });
      } else setMessaggio({ tono: "danger", testo: j?.error ?? "Non è stato possibile spostare la data di prova. Riprova." });
    } catch {
      setMessaggio({ tono: "danger", testo: "Non riesco a collegarmi al server. Controlla la rete e riprova." });
    }
    setInvio(false);
  }

  return (
    <Sezione
      data={ora ? DATA.format(new Date(oraProva(a, ora))) : "—"}
      spiegazione="Fa passare i giorni della prova gratuita senza aspettare: conto alla rovescia, avvisi e blocco a fine prova. Solo nel gestionale, Stripe non c'entra. La data va solo avanti."
      negata={negata}
      pulsanti={PASSI_PROVA.map((p) => (
        <Button key={p.passo} size="sm" variant="secondary" disabled={invio} onClick={() => void sposta(p.passo)}>
          {p.etichetta}
        </Button>
      ))}
      stato={invio ? <p className="text-ink-2">Sposto la data…</p> : <Esito messaggio={messaggio} />}
    />
  );
}

function StrumentiOrologio({ abbonamento: a, negata }: { abbonamento: Abbonamento; negata: string | null }) {
  const [attesa, setAttesa] = useState<"invio" | "avanza" | null>(null);
  const [messaggio, setMessaggio] = useState<Messaggio | null>(null);
  const vivo = useRef(true);
  useEffect(() => {
    vivo.current = true;
    return () => {
      vivo.current = false;
    };
  }, []);

  async function aspetta(arrivo: number | null): Promise<boolean> {
    setAttesa("avanza");
    const esito = await aspettaOrologio(arrivo, vivo);
    if (esito === "via") return false;
    setAttesa(null);
    if (esito === "tardi") setMessaggio({ tono: "warn", testo: TARDI });
    return esito === "pronto";
  }

  // Aprendo la pagina mentre l'orologio sta ancora avanzando (per esempio dopo un ricaricamento) si riprende ad aspettare
  useEffect(() => {
    void controllaOrologio().then(async (d) => {
      if (!vivo.current || d?.orologioPronto !== false) return;
      setAttesa("avanza");
      const esito = await aspettaOrologio(null, vivo);
      if (esito === "via") return;
      setAttesa(null);
      if (esito === "tardi") setMessaggio({ tono: "warn", testo: TARDI });
    });
  }, []);

  async function avanza(passo: Passo) {
    setMessaggio(null);
    setAttesa("invio");
    let r: Response;
    let j: RispostaAvanza | null;
    try {
      r = await fetchAzienda("/api/abbonamento/prova/avanza", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ passo }) });
      j = (await r.json().catch(() => null)) as RispostaAvanza | null;
    } catch {
      setAttesa(null);
      setMessaggio({ tono: "danger", testo: "Non riesco a collegarmi al server. Controlla la rete e riprova." });
      return;
    }
    if (r.status !== 202 || typeof j?.frozenTime !== "number") {
      setAttesa(null);
      setMessaggio({ tono: "danger", testo: j?.error ?? "Non è stato possibile far avanzare l'orologio. Riprova." });
      // Già in avanzamento (un'altra scheda): si aspetta che finisca
      if (r.status === 409) void aspetta(null);
      return;
    }
    const arrivo = j.frozenTime;
    if (await aspetta(arrivo)) setMessaggio({ tono: "ok", testo: `Orologio di prova portato al ${DATA.format(new Date(arrivo))}.` });
  }

  const passi = PASSI.filter((p) => avanzamentoPermesso(a, p.passo));
  return (
    <Sezione
      data={a.oraOrologio != null ? DATA.format(new Date(a.oraOrologio)) : "—"}
      spiegazione="Fa passare il tempo su Stripe: rinnovi, carte rifiutate e fine della disdetta senza aspettare. L'orologio va solo avanti."
      negata={negata}
      pulsanti={passi.map((p) => (
        <Button key={p.passo} size="sm" variant="secondary" disabled={attesa !== null} onClick={() => void avanza(p.passo)}>
          {p.etichetta}
        </Button>
      ))}
      stato={
        attesa === "invio" ? (
          <p className="text-ink-2">Chiedo a Stripe…</p>
        ) : attesa === "avanza" ? (
          <p className="text-ink-2">L&apos;orologio sta avanzando…</p>
        ) : (
          <Esito messaggio={messaggio} />
        )
      }
    />
  );
}
