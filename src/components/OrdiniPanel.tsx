"use client";

import Link from "next/link";
import { useState } from "react";
import { useStore } from "@/lib/store";
import { locToString } from "@/lib/warehouse";
import { Button, Notice, OrderChip, Panel } from "@/components/ui";
import { dateIt, euro } from "@/lib/logic";
import type { Order } from "@/lib/types";

// Ordini di tutti i canali (banco e ordini, modulo Vendite) o solo online (eBay e negozio, nel Magazzino):
// stessi passi in entrambi i casi, dall'incasso al documento fiscale e al reso.
export function OrdiniPanel({ canali, className = "" }: { canali: "online" | "tutti"; className?: string }) {
  const s = useStore();
  const [msg, setMsg] = useState<{ tone: "ok" | "danger"; text: React.ReactNode } | null>(null);
  const [chan, setChan] = useState<"tutti" | "ebay" | Order["channel"]>("tutti");
  const [which, setWhich] = useState<"da-gestire" | "tutti">("da-gestire");
  const docLink = (id: string) => <Link href={`/documento/${id}`} target="_blank" className="code font-semibold underline">{id}</Link>;

  // "Da gestire": ordini con un'azione aperta (incasso, consegna/spedizione, documento mancante)
  const hasDoc = (id: string) => s.docs.some((d) => d.orderId === id && d.type !== "preventivo" && d.type !== "nota di credito");
  const paidStates: Order["status"][] = ["pagato", "spedito", "consegnato"];
  const open = (o: Order) => o.status === "in attesa di pagamento" || o.status === "pagato" || (paidStates.includes(o.status) && !hasDoc(o.id)) || !!o.daGestire;
  const orders = s.orders.filter(
    (o) =>
      (canali === "tutti" || o.channel !== "banco") &&
      (chan === "tutti" || (chan === "ebay" ? !!o.ebayOrderId : o.channel === chan && !o.ebayOrderId)) &&
      (which === "tutti" || open(o)),
  );

  return (
    <Panel
      title={canali === "online" ? "Ordini online" : "Ordini"}
      className={className}
      action={
        <span className="flex gap-2">
          <select className="h-10 rounded border border-hair bg-label px-2 text-sm font-semibold" value={which} onChange={(e) => setWhich(e.target.value as typeof which)} aria-label="Quali ordini">
            <option value="da-gestire">Da gestire</option>
            <option value="tutti">Tutti</option>
          </select>
          <select className="h-10 rounded border border-hair bg-label px-2 text-sm font-semibold" value={chan} onChange={(e) => setChan(e.target.value as typeof chan)} aria-label="Canale">
            <option value="tutti">Tutti i canali</option>
            {canali === "tutti" && <option value="banco">Banco</option>}
            <option value="negozio">Negozio online</option>
            <option value="marketplace">Marketplace</option>
            <option value="ebay">eBay</option>
          </select>
        </span>
      }
    >
      {msg && (
        <div className="border-b border-hair-soft p-4">
          <Notice tone={msg.tone}>{msg.text}</Notice>
        </div>
      )}
      <ul className="divide-y divide-hair-soft">
        {orders.length === 0 && <li className="px-4 py-6 text-ink-2">{which === "da-gestire" ? "Nessun ordine da gestire." : "Nessun ordine."}</li>}
        {orders.slice(0, which === "tutti" ? 60 : 200).map((o) => (
          <li key={o.id} className={`grid gap-3 px-4 py-3 md:grid-cols-[120px_110px_1fr_100px_auto] md:items-center ${o.daGestire ? "bg-warn-bg" : ""}`}>
            <span className="code text-[22px] font-bold leading-none">{o.id}</span>
            <span className="text-sm font-semibold uppercase tracking-wide text-ink-2 code">
              {o.ebayOrderId ? "eBay" : o.channel}
              {o.ebayOrderId && <span className="block text-[12px] normal-case tracking-normal text-ink-3">{o.ebayOrderId}</span>}
            </span>
            <span className="min-w-0 text-[15px]">
              {o.partIds.map((pid) => {
                // Ordine aperto: dove andare a prendere il pezzo (o se è già stato prelevato)
                const loc = s.parts.find((x) => x.id === pid)?.location;
                const isOpen = o.status === "in attesa di pagamento" || o.status === "pagato";
                return (
                  <span key={pid} className="mr-3 inline-block">
                    <Link href={`/ricambi/${pid}`} className="code font-semibold text-band underline">{pid}</Link>
                    {isOpen && <span className="code ml-1 text-sm text-ink-2">{loc ? `in ${locToString(loc)}` : "prelevato"}</span>}
                  </span>
                );
              })}
              {o.daGestire && <span className="mb-1 block text-sm font-semibold text-warn">Da gestire: {o.daGestire}</span>}
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
              {o.daGestire && <Button size="sm" variant="secondary" onClick={() => s.markOrderHandled(o.id)}>Segna come gestito</Button>}
              {o.status === "pagato" && <Button size="sm" onClick={() => s.shipOrder(o.id)}>{o.channel === "banco" || o.delivery === "ritiro" ? "Consegnato" : "Spedito"}</Button>}
              {paidStates.includes(o.status) && !hasDoc(o.id) && (
                <>
                  <Button size="sm" variant="secondary" onClick={() => setMsg({ tone: "ok", text: <>Scontrino {docLink(s.issueDoc(o.id, "documento commerciale", { name: o.customer }))} emesso per {o.id}.</> })}>
                    Emetti scontrino
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      const tax = prompt(`Partita IVA o codice fiscale di ${o.customer}:`)?.replace(/\s/g, "").toUpperCase();
                      if (!tax) return;
                      if (!/^(IT)?\d{11}$|^[A-Z0-9]{16}$/.test(tax)) return setMsg({ tone: "danger", text: "Partita IVA (11 cifre) o codice fiscale (16 caratteri) non valido." });
                      setMsg({ tone: "ok", text: <>Fattura {docLink(s.issueDoc(o.id, "fattura", { name: o.customer, taxId: tax }))} per {o.id} inviata allo SdI (simulato).</> });
                    }}
                  >
                    Emetti fattura
                  </Button>
                </>
              )}
              {(o.status === "spedito" || o.status === "consegnato") && <Button size="sm" variant="secondary" onClick={() => s.returnOrder(o.id)}>Registra reso</Button>}
            </span>
          </li>
        ))}
      </ul>
    </Panel>
  );
}
