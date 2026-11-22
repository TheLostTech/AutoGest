"use client";

// Pagina Abbonamento (spec registrazione-pagamento, sezione 6): stato e conto alla rovescia, prossimo addebito,
// moduli da aggiungere (con l'anteprima di Stripe) o togliere (con il lavoro aperto), portale clienti di Stripe.
// Solo il titolare (o l'assistenza) di un'azienda registrata; per le altre i moduli restano in Impostazioni → Moduli.
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { CreditCard } from "lucide-react";
import { moduliDaAbbonamento, type Abbonamento, type Conto, type StatoAbbonamento } from "@/lib/abbonamento";
import { fetchAzienda } from "@/lib/accesso/azienda-client";
import { useSessione } from "@/lib/accesso/client";
import { euro, LISTINO, prezzo, totale, type Periodo } from "@/lib/listino";
import { ORDINE_MODULI, type Modulo } from "@/lib/moduli";
import { lavoroAperto } from "@/lib/moduli-lavoro";
import { useStore } from "@/lib/store";
import type { ModalitaStripe } from "@/lib/stripe/chiavi";
import { useAbbonamento } from "@/lib/use-abbonamento";
import { StrumentiProva } from "@/components/StrumentiProva";
import { Button, Notice, PageTitle, Panel } from "@/components/ui";

const STATO: Record<StatoAbbonamento, string> = {
  nuovo: "Non ancora attivo",
  attivo: "Attivo",
  "in-ritardo": "Pagamento non riuscito",
  disdetto: "Disdetto",
  scaduto: "Scaduto",
};
const PERIODO: Record<Periodo, string> = { mese: "Mensile", anno: "Annuale" };
const perPeriodo = (p: Periodo) => (p === "anno" ? "/ anno" : "/ mese");
const DATA = new Intl.DateTimeFormat("it-IT", { timeZone: "Europe/Rome", day: "2-digit", month: "2-digit", year: "numeric" });
// Moduli che si cambiano da qui: con lo stato attivo o disdetto (lo stesso controllo lo fa il server)
const cambiabile = (a: Abbonamento) => (a.stato === "attivo" || a.stato === "disdetto") && !!a.periodo;

type Conferma =
  | { tipo: "aggiungi"; modulo: Modulo; importo: number | null; errore?: string; invio?: boolean }
  | { tipo: "togli"; modulo: Modulo; aperto: string[]; errore?: string; invio?: boolean };

type Risposta<T> = { ok: true; dati: T } | { ok: false; errore: string };

async function chiama<T>(url: string, corpo: unknown): Promise<Risposta<T>> {
  try {
    const r = await fetchAzienda(url, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(corpo) });
    const j = (await r.json().catch(() => null)) as (T & { error?: string }) | null;
    if (r.ok && j) return { ok: true, dati: j };
    return { ok: false, errore: j?.error ?? "Non è stato possibile completare l'operazione. Riprova." };
  } catch {
    return { ok: false, errore: "Non riesco a collegarmi al server. Controlla la rete e riprova." };
  }
}

export default function AbbonamentoView() {
  const { accesso } = useSessione();
  const { dati, ricarica } = useAbbonamento();
  // All'apertura si rilegge da Stripe (al massimo una volta ogni 15 secondi): anche al ritorno dal portale
  useEffect(() => {
    void ricarica(true);
  }, [ricarica]);

  if (!accesso || !dati) return <p className="mx-auto max-w-3xl text-ink-3">Carico l&apos;abbonamento…</p>;
  const titolare = accesso.ruoli.includes("responsabile") || !!accesso.assistenza;
  if (!titolare) {
    return (
      <div className="mx-auto max-w-3xl">
        <PageTitle title="Abbonamento" />
        <Notice>L&apos;abbonamento lo gestisce il titolare dell&apos;azienda.</Notice>
      </div>
    );
  }
  if (!accesso.azienda.registrata || !dati.registrata || !dati.abbonamento) {
    return (
      <div className="mx-auto max-w-3xl">
        <PageTitle title="Abbonamento" />
        <Notice>
          Questa azienda non ha un abbonamento da pagare: i moduli si accendono da{" "}
          <Link href="/impostazioni/moduli" className="font-semibold underline">
            Moduli
          </Link>
          .
        </Notice>
      </div>
    );
  }
  return <Pagina abbonamento={dati.abbonamento} conto={dati.conto} modalita={dati.modalita} ricarica={ricarica} />;
}

function Pagina({
  abbonamento: a,
  conto,
  modalita,
  ricarica,
}: {
  abbonamento: Abbonamento;
  conto: Conto | null;
  modalita: ModalitaStripe;
  ricarica: (sincronizza?: boolean) => Promise<void>;
}) {
  const router = useRouter();
  const path = usePathname();
  const sp = useSearchParams();
  const richiesto = sp.get("aggiungi");
  const attivi = moduliDaAbbonamento(a);
  const [conferma, setConferma] = useState<Conferma | null>(null);
  const [esito, setEsito] = useState<{ tono: "ok" | "danger"; testo: string } | null>(null);
  const [attesa, setAttesa] = useState<"portale" | "riattiva" | null>(null);

  // Arrivando da "Attiva" (?aggiungi=<modulo>) si apre la conferma di quel modulo appena l'abbonamento lo permette:
  // lo stato in memoria può essere vecchio, e la rilettura da Stripe all'apertura arriva dopo.
  const [pendente, setPendente] = useState<Modulo | null>(() => ORDINE_MODULI.find((x) => x !== "magazzino" && x === richiesto) ?? null);
  if (pendente && conferma === null && cambiabile(a)) {
    setPendente(null);
    if (!attivi.includes(pendente)) setConferma({ tipo: "aggiungi", modulo: pendente, importo: null });
  }

  // Il modulo richiesto non resta nell'indirizzo: ricaricando la pagina la conferma non si riapre
  useEffect(() => {
    if (richiesto) router.replace(path, { scroll: false });
  }, [richiesto, router, path]);

  // L'importo dell'aggiunta lo calcola Stripe (anteprima della fattura): la parte fino al rinnovo, IVA esclusa
  const anteprimaDi = conferma?.tipo === "aggiungi" && conferma.importo === null && !conferma.errore ? conferma.modulo : null;
  useEffect(() => {
    if (!anteprimaDi) return;
    let attivo = true;
    void chiama<{ importo: number }>("/api/abbonamento/moduli", { anteprima: anteprimaDi }).then((r) => {
      if (!attivo) return;
      setConferma((c) => (c?.tipo === "aggiungi" && c.modulo === anteprimaDi ? (r.ok ? { ...c, importo: r.dati.importo } : { ...c, errore: r.errore }) : c));
    });
    return () => {
      attivo = false;
    };
  }, [anteprimaDi]);

  const periodo = a.periodo ?? "mese";
  const puoCambiare = cambiabile(a);

  async function confermaCambio() {
    if (!conferma) return;
    const c = conferma;
    setConferma({ ...c, invio: true, errore: undefined });
    const r = await chiama<{ abbonamento: Abbonamento }>("/api/abbonamento/moduli", c.tipo === "aggiungi" ? { aggiungi: c.modulo } : { togli: c.modulo });
    if (!r.ok) {
      setConferma({ ...c, invio: false, errore: r.errore });
      return;
    }
    await ricarica();
    setConferma(null);
    setEsito({ tono: "ok", testo: c.tipo === "aggiungi" ? `${LISTINO[c.modulo].nome} è attivo.` : `${LISTINO[c.modulo].nome} è stato tolto.` });
  }

  async function riattiva() {
    setAttesa("riattiva");
    setEsito(null);
    const r = await chiama<{ abbonamento: Abbonamento }>("/api/abbonamento/moduli", { riattiva: true });
    if (r.ok) {
      await ricarica();
      setEsito({ tono: "ok", testo: "Abbonamento riattivato: si rinnova alla scadenza." });
    } else setEsito({ tono: "danger", testo: r.errore });
    setAttesa(null);
  }

  async function portale() {
    setAttesa("portale");
    setEsito(null);
    const r = await chiama<{ url: string }>("/api/abbonamento/portale", {});
    if (r.ok && r.dati.url) {
      // Stessa scheda: Stripe riporta qui
      window.location.assign(r.dati.url);
      return;
    }
    setEsito({ tono: "danger", testo: r.ok ? "Non è stato possibile aprire il portale. Riprova." : r.errore });
    setAttesa(null);
  }

  const tonoConto = conto?.tono === "errore" ? "text-danger" : conto?.tono === "avviso" ? "text-warn" : "text-ink";

  return (
    <div className="mx-auto max-w-3xl">
      <PageTitle
        title="Abbonamento"
        actions={
          <span className="code inline-flex min-h-9 items-center rounded-full border border-hair bg-label px-3.5 text-[14px] font-semibold text-ink-2">
            {a.periodo ? `${PERIODO[a.periodo]} · ` : ""}
            {STATO[a.stato]}
          </span>
        }
      />

      <Panel>
        <div className="space-y-3 px-4 py-4 md:px-5">
          {conto ? (
            <p className={`text-[18px] font-semibold ${tonoConto}`}>{conto.testo}</p>
          ) : a.stato === "nuovo" ? (
            <p className="text-[17px] text-ink-2">Stai provando il gestionale: l&apos;abbonamento si paga dopo il primo veicolo.</p>
          ) : (
            <p className="text-[17px] text-ink-2">L&apos;abbonamento è finito. I dati restano: riattivalo per continuare.</p>
          )}
          {(a.stato === "attivo" || a.stato === "in-ritardo") && (
            <p className="text-[16px]">
              Prossimo addebito:{" "}
              <span className="code font-semibold tabular-nums">
                {euro(totale(attivi, periodo))} + IVA
              </span>
            </p>
          )}
          {a.stato === "disdetto" && (
            <div className="flex flex-wrap items-center gap-3">
              <p className="text-[16px] text-ink-2">Nessun altro addebito: l&apos;abbonamento non si rinnova.</p>
              <Button size="sm" onClick={riattiva} disabled={attesa !== null}>
                {attesa === "riattiva" ? "Riattivo…" : "Riattiva"}
              </Button>
            </div>
          )}
        </div>
      </Panel>

      {esito && (
        <div className="mt-4" role={esito.tono === "danger" ? "alert" : "status"}>
          <Notice tone={esito.tono}>{esito.testo}</Notice>
        </div>
      )}

      <Panel title="Moduli" className="mt-5">
        {!puoCambiare && (
          <p className="border-b border-hair-soft px-4 py-3 text-[15px] text-ink-3">
            {a.stato === "in-ritardo" ? "Aggiorna la carta prima di cambiare i moduli." : "I moduli si cambiano con l'abbonamento attivo."}
          </p>
        )}
        <ul className="divide-y divide-hair-soft">
          {ORDINE_MODULI.map((m) => {
            const acceso = attivi.includes(m);
            const aperta = conferma?.modulo === m ? conferma : null;
            return (
              <li key={m} className="px-4 py-3 md:px-5">
                <div className="flex min-h-12 flex-wrap items-center gap-x-4 gap-y-2">
                  <span className="min-w-28 flex-1 text-[17px] font-semibold">{LISTINO[m].nome}</span>
                  <span className="code whitespace-nowrap text-[15px] tabular-nums text-ink-2">
                    {euro(prezzo(m, periodo))} {perPeriodo(periodo)}
                  </span>
                  <span className="flex w-28 justify-end">
                    {m === "magazzino" ? (
                      <span className="text-[14px] font-semibold text-ok">incluso</span>
                    ) : acceso ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={!puoCambiare || !!conferma}
                        onClick={() => {
                          setEsito(null);
                          setConferma({ tipo: "togli", modulo: m, aperto: lavoroAperto(m, useStore.getState()) });
                        }}
                      >
                        Togli
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        disabled={!puoCambiare || !!conferma}
                        onClick={() => {
                          setEsito(null);
                          setConferma({ tipo: "aggiungi", modulo: m, importo: null });
                        }}
                      >
                        Aggiungi
                      </Button>
                    )}
                  </span>
                </div>
                {aperta && <Riquadro c={aperta} a={a} periodo={periodo} onConferma={confermaCambio} onAnnulla={() => setConferma(null)} />}
              </li>
            );
          })}
        </ul>
      </Panel>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <Button variant="secondary" onClick={portale} disabled={attesa !== null || !a.customerId}>
          <CreditCard className="size-5" aria-hidden />
          {attesa === "portale" ? "Apro Stripe…" : "Carta, fatture e disdetta"}
        </Button>
        <span className="text-[14px] text-ink-3">Si apre il portale clienti di Stripe.</span>
      </div>

      {/* Solo con le chiavi di prova e l'orologio di prova di Stripe (spec, sezione 7) */}
      {modalita === "prova" && a.prova && a.orologioId && <StrumentiProva abbonamento={a} />}
    </div>
  );
}

// La conferma sotto la riga del modulo: per l'aggiunta l'importo di Stripe, per la rimozione il lavoro aperto
function Riquadro({ c, a, periodo, onConferma, onAnnulla }: { c: Conferma; a: Abbonamento; periodo: Periodo; onConferma: () => void; onAnnulla: () => void }) {
  const nome = LISTINO[c.modulo].nome;
  const rinnovo = a.rinnovo ? ` del ${DATA.format(new Date(a.rinnovo))}` : "";
  const pronto = c.tipo === "togli" || c.importo !== null;
  return (
    <div className="mt-3 rounded-md border border-band/40 bg-band-tint/60 px-4 py-3" role="group" aria-label={c.tipo === "aggiungi" ? `Aggiungere ${nome}` : `Togliere ${nome}`}>
      {c.tipo === "aggiungi" ? (
        <>
          <p className="text-[16px] font-semibold">Aggiungere {nome}?</p>
          <p className="mt-1 text-[15px] text-ink-2" aria-live="polite">
            {c.importo !== null ? (
              <>
                Paghi subito <b className="code tabular-nums">{euro(c.importo)} + IVA</b> per i giorni fino al rinnovo{rinnovo}, poi {euro(prezzo(c.modulo, periodo))} {perPeriodo(periodo)}.
              </>
            ) : c.errore ? null : (
              "Calcolo l'importo con Stripe…"
            )}
          </p>
        </>
      ) : (
        <>
          <p className="text-[16px] font-semibold">Togliere {nome}?</p>
          {c.aperto.length > 0 && (
            <div className="mt-1 text-[15px]">
              <p className="font-semibold text-warn">C&apos;è ancora lavoro aperto:</p>
              <ul className="ml-5 list-disc">
                {c.aperto.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            </div>
          )}
          <p className="mt-1 text-[15px] text-ink-2">Il modulo si spegne subito e i giorni non usati diventano credito sulla prossima fattura. I dati restano salvati.</p>
        </>
      )}
      {c.errore && (
        <p role="alert" className="mt-2 rounded-md bg-danger-bg px-3 py-2 text-[15px] font-medium text-danger">
          {c.errore}
        </p>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        <Button size="sm" variant={c.tipo === "togli" ? "danger" : "primary"} onClick={onConferma} disabled={!pronto || !!c.invio}>
          {c.invio ? "Un momento…" : c.tipo === "aggiungi" ? "Aggiungi e paga" : "Togli il modulo"}
        </Button>
        <Button size="sm" variant="quiet" onClick={onAnnulla} disabled={!!c.invio}>
          Annulla
        </Button>
      </div>
    </div>
  );
}
