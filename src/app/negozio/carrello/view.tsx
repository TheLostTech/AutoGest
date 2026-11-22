"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { CreditCard, Loader2, Trash2 } from "lucide-react";
import { useStore } from "@/lib/store";
import { useCart } from "@/lib/cart";
import { euro } from "@/lib/logic";
import { onlinePrice } from "@/lib/pricing";
import { typeById } from "@/lib/catalog";
import { Button, Field, Notice, PartImage } from "@/components/ui";
import { isShippable } from "@/lib/spedizione";
import { nextToShip, partsOf, quantityOf } from "@/lib/annunci";

type Step = "carrello" | "pagamento" | "esito";
type Consegna = "corriere" | "ritiro";
// Ordine fatto sul server: il token serve a pagarlo; importo e consegna arrivano dalle risposte
type Ordine = { id: string; token: string; amount: number; delivery: Consegna; pagato?: boolean; pagamentoAttivo: boolean };

export default function Carrello() {
  // Il catalogo pubblico (annunci e pezzi in vendita): lo carica l'Hydrator dal server
  const annunci = useStore((x) => x.annunci);
  const parts = useStore((x) => x.parts);
  const cart = useCart();
  const [step, setStep] = useState<Step>("carrello");
  const [order, setOrder] = useState<Ordine>();
  const [error, setError] = useState("");
  const [paying, setPaying] = useState(false);
  // Pagamento online attivo? Sconosciuto finché il server non risponde (il server rifiuta comunque gli ordini se non è attivo)
  const [pagamentoAttivo, setPagamentoAttivo] = useState<boolean>();
  useEffect(() => {
    fetch("/api/negozio/catalogo", { cache: "no-store" })
      .then((r) => r.json())
      .then((j: { pagamentoAttivo?: boolean }) => setPagamentoAttivo(j.pagamentoAttivo === true))
      .catch(() => undefined);
  }, []);
  const [form, setForm] = useState({ nome: "", email: "", consegna: "spedizione" as "spedizione" | "ritiro" });

  // Un'unità per annuncio; foto dal prossimo a partire
  const items = cart.ids.flatMap((id) => {
    const a = annunci.find((x) => x.id === id);
    if (!a) return [];
    const p = nextToShip(a, parts)[0] ?? partsOf(a, parts)[0];
    return [{ a, p, ok: a.negozio?.stato === "online" && quantityOf(a, parts) > 0 }];
  });
  const total = Math.round(items.reduce((t, x) => t + (onlinePrice(x.a.price) ?? 0), 0) * 100) / 100;
  const blocked = items.filter((x) => !x.ok);
  const pickupOnly = items.some((x) => !isShippable(x.a, typeById(x.a.typeId).shippable));

  async function placeOrder(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setPaying(true);
    const delivery: Consegna = form.consegna === "ritiro" || pickupOnly ? "ritiro" : "corriere";
    try {
      const r = await fetch("/api/negozio/ordine", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ annuncioIds: cart.ids, nome: form.nome || "Cliente online", consegna: delivery }),
      });
      const j = (await r.json().catch(() => ({}))) as { ordineId?: string; token?: string; importo?: number; pagamentoAttivo?: boolean; conflicts?: string[]; error?: string };
      if (r.status === 409) {
        setError(`Mentre completavi l'ordine, ${(j.conflicts ?? []).join(", ")} è stato venduto o riservato su un altro canale. Toglilo dal carrello per continuare.`);
        return;
      }
      if (!r.ok || !j.ordineId || !j.token) {
        setError(j.error ?? "Non riesco a registrare l'ordine: riprova tra poco.");
        return;
      }
      setOrder({ id: j.ordineId, token: j.token, amount: j.importo ?? total, delivery, pagamentoAttivo: j.pagamentoAttivo === true });
      setStep("pagamento");
    } catch {
      setError("Non riesco a raggiungere il negozio: riprova tra poco.");
    } finally {
      setPaying(false);
    }
  }

  async function pay(success: boolean) {
    if (!order) return;
    setPaying(true);
    setError("");
    await new Promise((r) => setTimeout(r, 900));
    try {
      const r = await fetch("/api/negozio/paga", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ordineId: order.id, token: order.token, riuscito: success }),
      });
      if (!r.ok) {
        const j = (await r.json().catch(() => ({}))) as { error?: string };
        setError(j.error ?? "Non riesco a registrare il pagamento: riprova tra poco.");
        return;
      }
      setOrder({ ...order, pagato: success });
      setStep("esito");
      if (success) cart.clear();
    } catch {
      setError("Non riesco a raggiungere il negozio: riprova tra poco.");
    } finally {
      setPaying(false);
    }
  }

  if (step === "pagamento" && order) {
    return (
      <div className="mx-auto max-w-md">
        <div className="rounded-md border border-hair bg-label p-6">
          <h1 className="text-[26px] font-bold">Ordine {order.id}</h1>
          {order.pagamentoAttivo && <p className="mt-1 text-ink-2">I pezzi sono riservati per te per 30 minuti. Pagina del provider di pagamento (simulata). Nessun dato della carta passa dal negozio.</p>}
          <div className="code my-5 text-[44px] font-bold leading-none">{euro(order.amount)}</div>
          {error && <div className="mb-3"><Notice tone="danger">{error}</Notice></div>}
          {!order.pagamentoAttivo ? (
            <Notice tone="warn">Pagamento online non ancora attivo. I pezzi restano riservati per 30 minuti: chiamaci per completare l&apos;ordine.</Notice>
          ) : (
          <div className="grid gap-2">
            <Button size="lg" onClick={() => pay(true)} disabled={paying}>
              {paying ? <Loader2 className="size-5 animate-spin" aria-hidden /> : <CreditCard className="size-5" aria-hidden />}
              Simula pagamento riuscito
            </Button>
            <Button size="lg" variant="secondary" onClick={() => pay(false)} disabled={paying}>Simula pagamento rifiutato</Button>
          </div>
          )}
        </div>
      </div>
    );
  }

  if (step === "esito" && order) {
    const ok = order.pagato === true;
    return (
      <div className="mx-auto max-w-md rounded-md border border-hair bg-label p-6">
        <Notice tone={ok ? "ok" : "danger"}>{ok ? "Pagamento confermato. Grazie!" : "Pagamento non riuscito. I pezzi sono tornati disponibili."}</Notice>
        <p className="code mt-4 text-[34px] font-bold">{order.id}</p>
        <p className="text-ink-2">{ok ? (order.delivery === "ritiro" ? "Ti avvisiamo quando i pezzi sono pronti per il ritiro in sede." : "Riceverai il tracking quando il pacco parte.") + " Ogni pezzo è identificato dal suo codice univoco." : "Puoi riprovare dal carrello."}</p>
        <div className="mt-5 flex gap-2">
          {ok ? <Link href="/negozio" className="font-semibold text-band">Torna al catalogo</Link> : <Button onClick={() => { setStep("carrello"); setOrder(undefined); }}>Torna al carrello</Button>}
        </div>
      </div>
    );
  }

  return (
    <div className="grid gap-8 md:grid-cols-[1.3fr_1fr]">
      <div>
        <h1 className="text-[30px] font-bold">Carrello</h1>
        {items.length === 0 ? (
          <p className="mt-4 text-ink-2">Il carrello è vuoto. <Link href="/negozio" className="font-semibold text-band">Sfoglia i ricambi</Link></p>
        ) : (
          <ul className="mt-4 divide-y divide-hair rounded-md border border-hair bg-label">
            {items.map(({ a, p, ok }) => (
              <li key={a.id} className="grid grid-cols-[72px_1fr_auto_auto] items-center gap-3 p-3">
                <PartImage src={p?.photos[0]} typeId={a.typeId} className="size-[72px] rounded bg-white" />
                <span className="min-w-0">
                  <Link href={`/negozio/${a.id}`} className="block truncate font-semibold">{a.titolo}</Link>
                  <span className="code text-sm text-ink-3">{a.id}</span>
                  {!ok && <span className="block text-sm font-semibold text-danger">Non più disponibile</span>}
                </span>
                <span className="code text-[20px] font-bold">{euro(onlinePrice(a.price))}</span>
                <button onClick={() => cart.remove(a.id)} className="grid size-10 place-items-center text-ink-3 hover:text-danger" aria-label={`Rimuovi ${a.id}`}>
                  <Trash2 className="size-5" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      {items.length > 0 && (
        <form onSubmit={placeOrder} className="h-fit space-y-4 rounded-md border border-hair bg-label p-5">
          <h2 className="text-[20px] font-bold">Dati ordine</h2>
          <Field label="Nome e cognome">
            <input className="field" required maxLength={80} value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} autoComplete="name" />
          </Field>
          <Field label="Email">
            <input className="field" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} autoComplete="email" />
          </Field>
          <fieldset>
            <legend className="mb-1.5 text-sm font-semibold">Consegna</legend>
            <div className="grid grid-cols-2 gap-2">
              {(["spedizione", "ritiro"] as const).map((c) => (
                <button type="button" key={c} disabled={c === "spedizione" && pickupOnly} onClick={() => setForm({ ...form, consegna: c })} className={`min-h-12 rounded-md border font-semibold capitalize disabled:text-ink-3 ${form.consegna === c && !(c === "spedizione" && pickupOnly) ? "border-band bg-band text-white" : "border-hair"}`}>
                  {c === "ritiro" ? "Ritiro in sede" : "Corriere"}
                </button>
              ))}
            </div>
            {pickupOnly && <p className="mt-1 text-sm text-ink-3">Un pezzo nel carrello è solo ritiro in sede.</p>}
          </fieldset>
          <div className="flex items-end justify-between border-t border-hair-soft pt-4">
            <span className="text-ink-3">Totale</span>
            <span className="code text-[34px] font-bold leading-none">{euro(total)}</span>
          </div>
          {error && <Notice tone="danger">{error}</Notice>}
          {pagamentoAttivo === false && <Notice tone="warn">Pagamento online non ancora attivo</Notice>}
          <Button size="lg" type="submit" className="w-full" disabled={blocked.length > 0 || paying || pagamentoAttivo === false}>Vai al pagamento</Button>
        </form>
      )}
    </div>
  );
}
