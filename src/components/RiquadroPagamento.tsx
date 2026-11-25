"use client";

// Riquadro di pagamento: copre il gestionale quando l'abbonamento blocca (finita la prova gratuita di 15 giorni, oppure
// a scadenza). Non si chiude: fuori restano solo "Esci" e, in assistenza, la fascia del super admin. Spec
// registrazione-pagamento, sezione 3; prova-15-giorni, sezione 4: a fine prova partono spuntati i moduli usati davvero.
// La scelta (SceltaModuli) serve anche alla pagina Abbonamento per pagare durante la prova.
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { Check } from "lucide-react";
import type { Abbonamento } from "@/lib/abbonamento";
import { fetchAzienda } from "@/lib/accesso/azienda-client";
import { esci } from "@/lib/accesso/client";
import { CARTE_DI_PROVA } from "@/lib/carte-prova";
import { BRAND } from "@/lib/config";
import { euro, LISTINO, prezzo, risparmioAnnuale, totale, type Periodo } from "@/lib/listino";
import { ORDINE_MODULI, type Modulo } from "@/lib/moduli";
import { moduliUsati } from "@/lib/moduli-usati";
import { useStore } from "@/lib/store";
import type { ModalitaStripe } from "@/lib/stripe/chiavi";
import { ricaricaAbbonamento } from "@/lib/use-abbonamento";
import { Button } from "./ui";

const TITOLO_SCADUTO = "Il tuo abbonamento è finito. I tuoi dati sono al sicuro: riattivalo per continuare";
const AGGIUNTIVI = ORDINE_MODULI.filter((m) => m !== "magazzino");
const perPeriodo = (p: Periodo) => (p === "anno" ? "/ anno" : "/ mese");
// Mentre il riquadro è aperto per il titolare lo stato si richiede a Stripe ogni 10 secondi (il server ne fa al massimo
// una ogni 15 per azienda): un pagamento finito in un'altra scheda, o arrivato in ritardo, chiude il riquadro da solo.
const RICONTROLLA_MS = 10_000;

// I moduli usati davvero durante la prova (dati salvati che solo quel modulo scrive), dall'archivio nel browser
function useModuliUsati(): Modulo[] {
  const vehicles = useStore((s) => s.vehicles);
  const wasteMoves = useStore((s) => s.wasteMoves);
  const firs = useStore((s) => s.firs);
  const orders = useStore((s) => s.orders);
  const docs = useStore((s) => s.docs);
  return useMemo(() => moduliUsati({ vehicles, wasteMoves, firs, orders, docs }), [vehicles, wasteMoves, firs, orders, docs]);
}

// Moduli spuntati in partenza (il magazzino c'è sempre): con lo stato scaduto quelli che il cliente aveva, altrimenti
// (fine prova, o pagamento durante la prova) quelli usati nella prova
function moduliIniziali(a: Abbonamento | null, usati: Modulo[]): Set<Modulo> {
  const da = a?.stato === "scaduto" ? a.moduli : usati;
  return new Set(da.filter((m) => m !== "magazzino"));
}

// La prova gratuita è partita ed è finita senza pagare
const provaFinita = (a: Abbonamento | null) => a?.stato === "nuovo" && a.fineProva !== null;

export function RiquadroPagamento({
  abbonamento,
  modalita,
  titolare,
  negata,
  assistenza,
}: {
  abbonamento: Abbonamento | null;
  modalita: ModalitaStripe;
  titolare: boolean;
  negata: string | null; // entrati con il PIN: si sceglie, ma per pagare serve l'accesso con email e password
  assistenza: boolean; // la fascia del super admin resta visibile sopra il riquadro
}) {
  const titoloId = useId();
  const titoloRef = useRef<HTMLHeadingElement>(null);
  const [uscendo, setUscendo] = useState(false);
  // Il titolo del titolare si sceglie sullo stato appena letto da Stripe: quello in memoria può essere vecchio
  // (per esempio quando il riquadro si apre per un rifiuto 402 della sincronizzazione)
  const [fresco, setFresco] = useState(false);
  const scaduto = abbonamento?.stato === "scaduto";

  useEffect(() => {
    if (!titolare) return;
    let vivo = true;
    void ricaricaAbbonamento(true).then(() => vivo && setFresco(true));
    const t = setInterval(() => {
      if (document.visibilityState === "visible") void ricaricaAbbonamento(true);
    }, RICONTROLLA_MS);
    return () => {
      vivo = false;
      clearInterval(t);
    };
  }, [titolare]);

  // Il fuoco entra nel riquadro: il resto della pagina è inerte (vedi AppShell)
  useEffect(() => {
    titoloRef.current?.focus();
  }, []);

  const esciOra = () => {
    setUscendo(true);
    void esci();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={titoloId}
      className={`no-print fixed inset-x-0 bottom-0 z-40 overflow-y-auto bg-ink/70 px-4 py-6 backdrop-blur-[2px] md:py-12 ${assistenza ? "top-11" : "top-0"}`}
    >
      <div className="mx-auto w-full max-w-[34rem] rounded-xl bg-label text-ink shadow-[0_24px_60px_-20px_rgb(0_0_0/0.5)]">
        <div className="flex items-start justify-between gap-4 border-b border-hair-soft px-5 pb-4 pt-5 md:px-7 md:pt-6">
          <h2 ref={titoloRef} id={titoloId} tabIndex={-1} className="text-[22px] font-bold leading-tight outline-none md:text-[24px]">
            {!titolare || !fresco ? (
              "L'abbonamento non è attivo."
            ) : scaduto ? (
              TITOLO_SCADUTO
            ) : provaFinita(abbonamento) ? (
              <>
                La prova gratuita è finita.
                <span className="mt-1 block text-[17px] font-medium text-ink-2">I tuoi dati restano qui: scegli i moduli per continuare.</span>
              </>
            ) : (
              <>
                Scegli i moduli per continuare.
                <span className="mt-1 block text-[17px] font-medium text-ink-2">I tuoi dati restano qui, con {BRAND.azienda}.</span>
              </>
            )}
          </h2>
          <button onClick={esciOra} disabled={uscendo} className="shrink-0 rounded border border-hair px-3 py-1.5 text-[14px] font-semibold text-ink-2 hover:border-ink-3 hover:text-ink">
            Esci
          </button>
        </div>
        {titolare ? (
          // Con lo stato nuovo (per esempio diventato scaduto) la scelta riparte da quello che il cliente aveva
          <SceltaModuli key={abbonamento?.stato ?? "nessuno"} abbonamento={abbonamento} modalita={modalita} negata={negata} />
        ) : (
          <p className="px-5 py-6 text-[17px] md:px-7">Chiedi al titolare di attivarlo.</p>
        )}
      </div>
    </div>
  );
}

// Periodo, moduli e "Paga con Stripe" (Checkout). Il Magazzino è sempre incluso e non si toglie; gli altri partono
// spuntati come da moduliIniziali e il cliente li toglie o li aggiunge.
export function SceltaModuli({ abbonamento, modalita, negata }: { abbonamento: Abbonamento | null; modalita: ModalitaStripe; negata: string | null }) {
  const path = usePathname();
  const usati = useModuliUsati();
  const [periodo, setPeriodo] = useState<Periodo>(() => (abbonamento?.stato === "scaduto" ? (abbonamento.periodo ?? "mese") : "mese"));
  // null finché il cliente non tocca nulla: la partenza segue l'archivio, anche se arriva dopo l'apertura del riquadro
  const [scelti, setScelti] = useState<Set<Modulo> | null>(null);
  const extra = scelti ?? moduliIniziali(abbonamento, usati);
  const [attesa, setAttesa] = useState(false);
  const [errore, setErrore] = useState("");
  const moduli = ORDINE_MODULI.filter((m) => m === "magazzino" || extra.has(m));
  const somma = totale(moduli, periodo);
  const risparmio = moduli.reduce((s, m) => s + risparmioAnnuale(m), 0);

  const cambia = (m: Modulo, on: boolean) => {
    const s = new Set(extra);
    if (on) s.add(m);
    else s.delete(m);
    setScelti(s);
  };

  async function paga() {
    setErrore("");
    setAttesa(true);
    try {
      const r = await fetchAzienda("/api/abbonamento/checkout", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ periodo, moduli, da: path + window.location.search }),
      });
      const j = (await r.json().catch(() => null)) as { url?: string; error?: string } | null;
      if (r.ok && j?.url) {
        // Stessa scheda: Stripe riporta su /abbonamento/fatto, oppure qui se si annulla
        window.location.assign(j.url);
        return;
      }
      setErrore(j?.error ?? "Non è stato possibile aprire il pagamento. Riprova.");
      // Già attivo o pagamento già in corso: lo stato si rilegge da Stripe, e se è pagato il riquadro si chiude
      if (r.status === 409) void ricaricaAbbonamento(true);
    } catch {
      setErrore("Non riesco a collegarmi al server. Controlla la rete e riprova.");
    }
    setAttesa(false);
  }

  const opzione = (p: Periodo, etichetta: string) => (
    <label
      className={`flex min-h-12 flex-1 cursor-pointer items-center justify-center rounded-md border px-3 text-center text-[15px] font-semibold transition-colors has-[:focus-visible]:outline has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-band ${
        periodo === p ? "border-band bg-band text-white" : "border-hair bg-label text-ink hover:border-ink-3"
      }`}
    >
      <input type="radio" name="periodo" value={p} checked={periodo === p} onChange={() => setPeriodo(p)} className="sr-only" />
      {etichetta}
    </label>
  );

  return (
    <div className="px-5 pb-6 pt-5 md:px-7">
      <fieldset>
        <legend className="sr-only">Periodo di pagamento</legend>
        <div className="flex gap-2">
          {opzione("mese", "Mensile")}
          {opzione("anno", "Annuale · risparmi il 10%")}
        </div>
      </fieldset>

      <fieldset className="mt-5">
        <legend className="sr-only">Moduli</legend>
        <ul className="divide-y divide-hair-soft">
          <li className="flex min-h-12 items-center gap-3">
            <span className="grid size-6 shrink-0 place-items-center rounded bg-band text-white" aria-hidden>
              <Check className="size-4" strokeWidth={3} />
            </span>
            <span className="flex-1 font-semibold">
              {LISTINO.magazzino.nome} <span className="text-[13px] font-medium text-ink-3">incluso</span>
            </span>
            <span className="code whitespace-nowrap text-[15px] tabular-nums">
              {euro(prezzo("magazzino", periodo))} {perPeriodo(periodo)}
            </span>
          </li>
          {AGGIUNTIVI.map((m) => (
            <li key={m}>
              <label className="flex min-h-12 cursor-pointer items-center gap-3">
                <input type="checkbox" checked={extra.has(m)} onChange={(e) => cambia(m, e.target.checked)} className="size-6 shrink-0 accent-band" />
                <span className="flex-1 font-semibold">{LISTINO[m].nome}</span>
                <span className="code whitespace-nowrap text-[15px] tabular-nums text-ink-2">
                  {euro(prezzo(m, periodo))} {perPeriodo(periodo)}
                </span>
              </label>
            </li>
          ))}
        </ul>
      </fieldset>

      <div className="mt-2 border-t-2 border-ink pt-3" aria-live="polite">
        <div className="flex items-baseline justify-between gap-3">
          <span className="text-[17px] font-bold">Totale</span>
          <span className="code whitespace-nowrap text-[20px] font-bold tabular-nums">
            {euro(somma)} {perPeriodo(periodo)}
          </span>
        </div>
        <p className="text-[14px] text-ink-3">IVA esclusa{periodo === "anno" && risparmio > 0 ? ` · risparmi ${euro(risparmio)} rispetto al mensile` : ""}</p>
      </div>

      {negata ? (
        <p className="mt-5 rounded-md bg-warn-bg px-4 py-3 text-[16px] font-semibold text-warn">{negata}</p>
      ) : (
        <Button size="lg" className="mt-5 w-full" onClick={paga} disabled={attesa}>
          {attesa ? "Apro Stripe…" : "Paga con Stripe"}
        </Button>
      )}
      {errore && (
        <p role="alert" className="mt-3 rounded-md bg-danger-bg px-4 py-3 text-[15px] font-medium text-danger">
          {errore}
        </p>
      )}

      {modalita === "prova" && (
        <div className="mt-5 rounded-md border border-dashed border-hair bg-carton px-4 py-3 text-[14px]">
          <p className="code text-[12px] font-bold uppercase tracking-[0.14em] text-ink-3">Carte di prova</p>
          <ul className="mt-1.5 space-y-1">
            {CARTE_DI_PROVA.map((c) => (
              <li key={c.numero}>
                <span className="code font-semibold tabular-nums">{c.numero}</span>: {c.cosa}
              </li>
            ))}
          </ul>
          <p className="mt-1.5 text-ink-3">Ambiente di prova: nessun addebito vero.</p>
        </div>
      )}
    </div>
  );
}
