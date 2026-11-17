"use client";

import Link from "next/link";
import { useState } from "react";
import { CreditCard, Loader2, Trash2 } from "lucide-react";
import { useStore } from "@/lib/store";
import { useCart } from "@/lib/cart";
import { euro } from "@/lib/logic";
import { typeById } from "@/lib/catalog";
import { Button, Field, Notice, PartImage } from "@/components/ui";

type Step = "carrello" | "pagamento" | "esito";

export default function Carrello() {
  const s = useStore();
  const cart = useCart();
  const [step, setStep] = useState<Step>("carrello");
  const [orderId, setOrderId] = useState<string>();
  const [error, setError] = useState("");
  const [paying, setPaying] = useState(false);
  const [form, setForm] = useState({ nome: "", email: "", consegna: "spedizione" as "spedizione" | "ritiro" });

  const items = cart.ids.map((id) => s.parts.find((p) => p.id === id)).filter((p) => !!p);
  const total = items.reduce((a, p) => a + (p.price ?? 0), 0);
  const blocked = items.filter((p) => p.status !== "disponibile" || p.listing !== "pubblicato");
  const pickupOnly = items.some((p) => !typeById(p.typeId).shippable);
  const order = orderId ? s.orders.find((o) => o.id === orderId) : undefined;

  function placeOrder(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const r = s.createOrder(
      "negozio",
      cart.ids,
      form.nome || "Cliente online",
      { user: form.nome || "Cliente online", role: "cliente", device: "Negozio online" },
      undefined,
      form.consegna === "ritiro" || pickupOnly ? "ritiro" : "corriere",
    );
    if (!r.ok) {
      setError(`Mentre completavi l'ordine, ${r.conflicts?.join(", ")} è stato venduto o riservato su un altro canale. Toglilo dal carrello per continuare.`);
      return;
    }
    setOrderId(r.value);
    setStep("pagamento");
  }

  async function pay(success: boolean) {
    if (!orderId) return;
    setPaying(true);
    await new Promise((r) => setTimeout(r, 900));
    s.payOrder(orderId, success, { user: form.nome || "Cliente online", role: "cliente", device: "Provider di pagamento (simulato)" });
    setPaying(false);
    setStep("esito");
    if (success) cart.clear();
  }

  if (step === "pagamento" && order) {
    return (
      <div className="mx-auto max-w-md">
        <div className="rounded-md border border-hair bg-label p-6">
          <h1 className="text-[26px] font-bold">Ordine {order.id}</h1>
          <p className="mt-1 text-ink-2">Pagina del provider di pagamento (simulata). I pezzi sono riservati per te mentre completi il pagamento. Nessun dato della carta passa dal negozio.</p>
          <div className="code my-5 text-[44px] font-bold leading-none">{euro(order.amount)}</div>
          <div className="grid gap-2">
            <Button size="lg" onClick={() => pay(true)} disabled={paying}>
              {paying ? <Loader2 className="size-5 animate-spin" aria-hidden /> : <CreditCard className="size-5" aria-hidden />}
              Simula pagamento riuscito
            </Button>
            <Button size="lg" variant="secondary" onClick={() => pay(false)} disabled={paying}>Simula pagamento rifiutato</Button>
          </div>
        </div>
      </div>
    );
  }

  if (step === "esito" && order) {
    const ok = order.status === "pagato";
    return (
      <div className="mx-auto max-w-md rounded-md border border-hair bg-label p-6">
        <Notice tone={ok ? "ok" : "danger"}>{ok ? "Pagamento confermato. Grazie!" : "Pagamento non riuscito. I pezzi sono tornati disponibili."}</Notice>
        <p className="code mt-4 text-[34px] font-bold">{order.id}</p>
        <p className="text-ink-2">{ok ? (order.delivery === "ritiro" ? "Ti avvisiamo quando i pezzi sono pronti per il ritiro in sede." : "Riceverai il tracking quando il pacco parte.") + " Ogni pezzo è identificato dal suo codice univoco." : "Puoi riprovare dal carrello."}</p>
        <div className="mt-5 flex gap-2">
          {ok ? <Link href="/negozio" className="font-semibold text-band">Torna al catalogo</Link> : <Button onClick={() => { setStep("carrello"); setOrderId(undefined); }}>Torna al carrello</Button>}
          <Link href="/vendite" className="ml-auto text-sm font-semibold text-ink-3 underline">Vedi l&apos;ordine nel gestionale</Link>
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
            {items.map((p) => (
              <li key={p.id} className="grid grid-cols-[72px_1fr_auto_auto] items-center gap-3 p-3">
                <PartImage src={p.photos[0]} typeId={p.typeId} className="size-[72px] rounded bg-white" />
                <span className="min-w-0">
                  <Link href={`/negozio/${p.id}`} className="block truncate font-semibold">{p.description}</Link>
                  <span className="code text-sm text-ink-3">{p.id}</span>
                  {blocked.includes(p) && <span className="block text-sm font-semibold text-danger">Non più disponibile</span>}
                </span>
                <span className="code text-[20px] font-bold">{euro(p.price)}</span>
                <button onClick={() => cart.remove(p.id)} className="grid size-10 place-items-center text-ink-3 hover:text-danger" aria-label={`Rimuovi ${p.id}`}>
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
            <input className="field" required value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} autoComplete="name" />
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
          <Button size="lg" type="submit" className="w-full" disabled={blocked.length > 0}>Vai al pagamento</Button>
        </form>
      )}
    </div>
  );
}
