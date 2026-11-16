"use client";

import Link from "next/link";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { FileText, Info, Trash2, Zap } from "lucide-react";
import { useStore } from "@/lib/store";
import { Button, Field, Notice, OrderChip, PageTitle, Panel, PartImage } from "@/components/ui";
import { dateIt, euro } from "@/lib/logic";
import { PartDetailSheet } from "@/components/PartDetailSheet";
import { listPrice } from "@/lib/pricing";
import type { Order } from "@/lib/types";

export default function Page() {
  return (
    <Suspense>
      <Vendite />
    </Suspense>
  );
}

function Vendite() {
  const sp = useSearchParams();
  const s = useStore();
  const [cart, setCart] = useState<string[]>(() => (sp.get("pezzo") ? [sp.get("pezzo")!] : []));
  const [q, setQ] = useState("");
  const [customer, setCustomer] = useState("");
  const [msg, setMsg] = useState<{ tone: "ok" | "danger" | "warn"; text: React.ReactNode } | null>(null);
  const [raceId, setRaceId] = useState("");
  const [chan, setChan] = useState<"tutti" | Order["channel"]>("tutti");
  const [detail, setDetail] = useState<string | null>(null);
  const [docType, setDocType] = useState<"documento commerciale" | "fattura">("documento commerciale");
  const [taxId, setTaxId] = useState("");
  const [listinoId, setListinoId] = useState("base");

  const avail = s.parts.filter((p) => p.status === "disponibile");
  const query = q.trim().toUpperCase();
  const results = query ? avail.filter((p) => !cart.includes(p.id) && (p.id.includes(query) || p.description.toUpperCase().includes(query))).slice(0, 6) : [];
  const cartParts = cart.map((id) => s.parts.find((p) => p.id === id)!).filter(Boolean);
  const listino = s.listini.find((l) => l.id === listinoId) ?? s.listini[0];
  const priceOf = (p: { price?: number }) => listPrice(p.price, listino);
  const prices = Object.fromEntries(cartParts.filter((p) => p.price).map((p) => [p.id, priceOf(p)!]));
  const total = cartParts.reduce((a, p) => a + (priceOf(p) ?? 0), 0);
  // Un pezzo senza prezzo non si vende né si preventiva: va prezzato dalla sua scheda
  const unpriced = cartParts.filter((p) => !p.price);
  const blocked = !cart.length || unpriced.length > 0;

  const needTax = docType === "fattura";
  const taxOk = !needTax || /^(IT)?\d{11}$|^[A-Z0-9]{16}$/i.test(taxId.replace(/\s/g, ""));
  const who = () => ({ name: customer.trim() || "Cliente al banco", taxId: needTax ? taxId.replace(/\s/g, "").toUpperCase() : undefined });
  const docLink = (id: string) => <Link href={`/documento/${id}`} target="_blank" className="code font-semibold underline">{id}</Link>;

  function checkout(payNow: boolean) {
    const r = s.createOrder("banco", cart, who().name, undefined, prices);
    if (!r.ok) {
      setMsg({ tone: "danger", text: `Vendita bloccata: ${r.conflicts?.join(", ")} non più disponibile. Nessun pezzo è stato venduto due volte.` });
      return;
    }
    if (payNow) {
      s.payOrder(r.value, true);
      const doc = s.issueDoc(r.value, docType, who(), prices, listino?.name);
      setMsg({ tone: "ok", text: <>Ordine <b className="code">{r.value}</b> incassato: pezzi venduti. {docType === "fattura" ? "Fattura" : "Scontrino"} {docLink(doc)}{docType === "fattura" ? " inviata allo SdI (simulato)" : ""}.</> });
    } else setMsg({ tone: "ok", text: <>Ordine <b className="code">{r.value}</b> creato: pezzi riservati in attesa di pagamento.</> });
    setCart([]);
    setCustomer("");
    setTaxId("");
  }

  function quote() {
    const id = s.createQuote(cart, who(), prices, listino?.name);
    setMsg({ tone: "ok", text: <>Preventivo {docLink(id)} creato. I pezzi restano disponibili: la riserva scatta solo quando il cliente conferma.</> });
    setCart([]);
  }

  function race() {
    if (!raceId) return;
    // Due canali tentano la riserva dello stesso pezzo nello stesso istante.
    const a = s.createOrder("banco", [raceId], "Cliente al banco");
    const b = s.createOrder("marketplace", [raceId], "Acquirente marketplace (demo)", { user: "Connettore marketplace", role: "sistema", device: "API marketplace" });
    setMsg({
      tone: "warn",
      text: (
        <>
          Banco: {a.ok ? <b>riserva riuscita ({a.value})</b> : <b>rifiutato</b>} · Marketplace: {b.ok ? <b>riserva riuscita</b> : <b>rifiutato, pezzo già riservato</b>}. Il secondo canale riceve l&apos;errore e aggiorna la propria giacenza.
        </>
      ),
    });
    setRaceId("");
  }

  const orders = s.orders.filter((o) => chan === "tutti" || o.channel === chan);

  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle title="Vendite" sub="Banco, negozio online e marketplace leggono la stessa giacenza: un pezzo si riserva una volta sola." />
      {msg && <div className="mb-5"><Notice tone={msg.tone}>{msg.text}</Notice></div>}

      <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        <Panel title="Vendita al banco">
          <div className="space-y-4 p-4">
            <Field label="Aggiungi ricambio" hint="Cerca per ID (anche da scansione) o descrizione">
              <input className="field" value={q} onChange={(e) => setQ(e.target.value)} placeholder="R-0023… / faro Panda" />
            </Field>
            {results.length > 0 && (
              <ul className="divide-y divide-hair-soft rounded-md border border-hair">
                {results.map((p) => (
                  <li key={p.id} className="flex items-stretch">
                    <button onClick={() => { setCart([...cart, p.id]); setQ(""); }} className="grid min-w-0 flex-1 grid-cols-[auto_1fr_auto] items-center gap-3 px-3 py-2 text-left hover:bg-carton" aria-label={`Aggiungi ${p.id} al conto`}>
                      <span className="code text-[18px] font-bold">{p.id}</span>
                      <span className="truncate">{p.description}</span>
                      <span className={`code font-bold ${p.price ? "" : "text-danger"}`}>{p.price ? euro(p.price) : "senza prezzo"}</span>
                    </button>
                    <button onClick={() => setDetail(p.id)} className="grid w-12 shrink-0 place-items-center border-l border-hair-soft text-band hover:bg-band-tint" aria-label={`Dettagli di ${p.id}`}>
                      <Info className="size-5" aria-hidden />
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <ul className="divide-y divide-hair-soft">
              {cartParts.map((p) => (
                <li key={p.id} className="grid grid-cols-[1fr_auto_auto] items-center gap-3 py-2">
                  <button onClick={() => setDetail(p.id)} className="-ml-1 grid min-w-0 grid-cols-[48px_1fr] items-center gap-3 rounded p-1 text-left hover:bg-carton" aria-label={`Dettagli di ${p.id}`}>
                    <PartImage src={p.photos[0]} typeId={p.typeId} className="size-12 rounded bg-white [&>span]:hidden" />
                    <span className="min-w-0">
                      <span className="flex items-center gap-1.5">
                        <span className="code text-[18px] font-bold leading-none">{p.id}</span>
                        <Info className="size-4 text-band" aria-hidden />
                      </span>
                      <span className="block truncate text-sm text-ink-2">{p.description}</span>
                      {p.status !== "disponibile" && <span className="text-sm font-semibold text-danger">non più disponibile ({p.status})</span>}
                    {!p.price && <span className="text-sm font-semibold text-danger">prezzo mancante: assegnalo dalla scheda</span>}
                    </span>
                  </button>
                  <span className="text-right">
                    <span className="code block text-[18px] font-bold">{euro(priceOf(p))}</span>
                    {listino && listino.pct !== 0 && p.price && <span className="block text-[13px] text-ink-3 line-through">{euro(p.price)}</span>}
                  </span>
                  <button onClick={() => setCart(cart.filter((x) => x !== p.id))} className="grid size-10 place-items-center text-ink-3 hover:text-danger" aria-label={`Togli ${p.id}`}>
                    <Trash2 className="size-5" />
                  </button>
                </li>
              ))}
              {cartParts.length === 0 && <li className="py-4 text-ink-3">Nessun pezzo nel conto.</li>}
            </ul>
            <Field label="Listino" hint={listino && listino.pct !== 0 ? `${listino.pct > 0 ? "+" : ""}${listino.pct}% sul prezzo base` : "Prezzo base"}>
              <select className="field" value={listinoId} onChange={(e) => setListinoId(e.target.value)}>
                {s.listini.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
            </Field>
            <Field label="Cliente">
              <input className="field" value={customer} onChange={(e) => setCustomer(e.target.value)} placeholder={needTax ? "Ragione sociale o nome" : "Nome o ragione sociale (facoltativo)"} />
            </Field>
            <div>
              <span className="mb-1.5 block text-sm font-semibold text-ink">Documento all&apos;incasso</span>
              <div className="inline-flex rounded-md border border-hair bg-carton p-1" role="radiogroup" aria-label="Documento all'incasso">
                {(["documento commerciale", "fattura"] as const).map((t) => (
                  <button
                    key={t}
                    role="radio"
                    aria-checked={docType === t}
                    onClick={() => setDocType(t)}
                    className={`min-h-10 rounded px-4 text-[15px] font-semibold ${docType === t ? "bg-label text-ink shadow-sm" : "text-ink-2"}`}
                  >
                    {t === "fattura" ? "Fattura" : "Scontrino"}
                  </button>
                ))}
              </div>
            </div>
            {needTax && (
              <Field label="Partita IVA o codice fiscale" error={taxId && !taxOk ? "11 cifre per la partita IVA, 16 caratteri per il codice fiscale" : undefined}>
                <input className="field code uppercase" value={taxId} onChange={(e) => setTaxId(e.target.value)} placeholder="IT00000000001" />
              </Field>
            )}
            <div className="flex items-end justify-between gap-3 border-t border-hair-soft pt-4">
              <div>
                <span className="text-sm text-ink-3">Totale</span>
                <div className="code text-[36px] font-bold leading-none">{euro(total)}</div>
              </div>
              <div className="flex flex-wrap justify-end gap-2">
                <Button variant="quiet" disabled={blocked} onClick={quote}><FileText className="size-5" aria-hidden /> Preventivo</Button>
                <Button variant="secondary" disabled={blocked} onClick={() => checkout(false)}>Prenota</Button>
                <Button disabled={blocked || !taxOk || (needTax && !customer.trim())} onClick={() => checkout(true)}>Incassa e vendi</Button>
              </div>
            </div>
            <p className="text-[13px] text-ink-3">Scontrino e fattura sono simulati: registratore telematico, invio allo SdI e regime IVA da definire con il commercialista.</p>
          </div>
        </Panel>

        <Panel title="Prova: doppia vendita simultanea">
          <div className="space-y-4 p-4">
            <p className="text-ink-2">Simula banco e marketplace che vendono lo stesso pezzo nello stesso istante. La riserva è atomica: vince il primo, il secondo viene rifiutato.</p>
            <Field label="Pezzo disponibile">
              <select className="field" value={raceId} onChange={(e) => setRaceId(e.target.value)}>
                <option value="">Scegli…</option>
                {avail.slice(0, 40).map((p) => <option key={p.id} value={p.id}>{p.id} · {p.description}</option>)}
              </select>
            </Field>
            <Button onClick={race} disabled={!raceId}>
              <Zap className="size-5" aria-hidden /> Avvia le due vendite
            </Button>
            <p className="text-[13px] text-ink-3">In produzione la riserva avviene con una transazione sul database centrale; i connettori marketplace ricevono l&apos;aggiornamento di giacenza.</p>
          </div>
        </Panel>
      </div>

      <Panel
        title="Ordini"
        className="mt-6"
        action={
          <select className="h-10 rounded border border-hair bg-label px-2 text-sm font-semibold" value={chan} onChange={(e) => setChan(e.target.value as typeof chan)} aria-label="Canale">
            <option value="tutti">Tutti i canali</option>
            <option value="banco">Banco</option>
            <option value="negozio">Negozio online</option>
            <option value="marketplace">Marketplace</option>
          </select>
        }
      >
        <ul className="divide-y divide-hair-soft">
          {orders.slice(0, 40).map((o) => (
            <li key={o.id} className="grid gap-3 px-4 py-3 md:grid-cols-[120px_110px_1fr_100px_auto] md:items-center">
              <span className="code text-[22px] font-bold leading-none">{o.id}</span>
              <span className="text-sm font-semibold uppercase tracking-wide text-ink-2 code">{o.channel}</span>
              <span className="min-w-0 text-[15px]">
                {o.partIds.map((pid) => (
                  <Link key={pid} href={`/ricambi/${pid}`} className="code mr-2 font-semibold text-band underline">{pid}</Link>
                ))}
                <span className="block text-sm text-ink-3">
                  {o.customer} · {dateIt(o.createdAt, true)}
                  {s.docs.filter((d) => d.orderId === o.id && d.type !== "preventivo").map((d) => (
                    <span key={d.id}> · <Link href={`/documento/${d.id}`} target="_blank" className="code font-semibold text-band underline">{d.id}</Link></span>
                  ))}
                </span>
              </span>
              <span className="code text-[20px] font-bold">{euro(o.amount)}</span>
              <span className="flex flex-wrap items-center gap-2">
                <OrderChip status={o.status} />
                {o.status === "in attesa di pagamento" && (
                  <>
                    <Button size="sm" onClick={() => s.payOrder(o.id, true)}>Pagato</Button>
                    <Button size="sm" variant="secondary" onClick={() => s.payOrder(o.id, false)}>Pagamento fallito</Button>
                    <Button size="sm" variant="quiet" onClick={() => s.cancelOrder(o.id, "Annullato dall'operatore")}>Annulla</Button>
                  </>
                )}
                {o.status === "pagato" && <Button size="sm" onClick={() => s.shipOrder(o.id)}>{o.channel === "banco" ? "Consegnato" : "Spedito"}</Button>}
                {(o.status === "spedito" || o.status === "consegnato") && <Button size="sm" variant="secondary" onClick={() => s.returnOrder(o.id)}>Registra reso</Button>}
              </span>
            </li>
          ))}
        </ul>
      </Panel>

      <PartDetailSheet partId={detail} onClose={() => setDetail(null)} inCart={!!detail && cart.includes(detail)} onAdd={(id) => { setCart((c) => (c.includes(id) ? c : [...c, id])); setQ(""); }} />
    </div>
  );
}
