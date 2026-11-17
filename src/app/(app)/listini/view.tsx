"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { useStore } from "@/lib/store";
import { listPrice, USED_SHARE, type Listino } from "@/lib/pricing";
import { CONDITIONS } from "@/lib/catalog";
import { Button, Notice, PageTitle, Panel } from "@/components/ui";
import type { Condition } from "@/lib/types";

export default function Listini() {
  const { listini, saveListini } = useStore();
  const [rows, setRows] = useState<Listino[]>(listini);
  const [saved, setSaved] = useState(false);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const dirty = JSON.stringify(rows) !== JSON.stringify(listini);
  const valid = rows.every((r) => r.name.trim() && Number.isFinite(r.pct) && r.pct > -90 && r.pct < 200);
  const edit = (id: string, patch: Partial<Listino>) => {
    setSaved(false);
    setRows((xs) => xs.map((x) => (x.id === id ? { ...x, ...patch } : x)));
  };

  return (
    <div className="mx-auto max-w-3xl">
      <PageTitle
        title="Listini"
        sub="Un prezzo base per pezzo, e una percentuale per ogni tipo di cliente. Puoi chiamarli come le fasce del gestionale che usi oggi (es. L, T, B, 2, 3, 4)."
      />
      {saved && <div className="mb-5"><Notice tone="ok">Listini salvati: il banco vendite usa già i nuovi prezzi.</Notice></div>}

      <Panel title="Fasce di prezzo">
        <ul className="divide-y divide-hair-soft">
          {rows.map((r) => (
            <li key={r.id} className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-3 px-4 py-3">
              <input className="field h-11" value={r.name} onChange={(e) => edit(r.id, { name: e.target.value })} aria-label="Nome del listino" />
              <span className="flex items-center gap-1.5">
                <input
                  className="field code h-11 w-20 text-right font-bold"
                  inputMode="numeric"
                  value={r.id === "base" ? "0" : (draft[r.id] ?? String(r.pct))}
                  disabled={r.id === "base"}
                  // Si può scrivere "-" e poi il numero: si converte solo quando il valore è un numero
                  onChange={(e) => {
                    const raw = e.target.value.replace(/[^0-9-]/g, "").replace(/(?!^)-/g, "");
                    setDraft((d) => ({ ...d, [r.id]: raw }));
                    if (raw !== "" && raw !== "-") edit(r.id, { pct: Number(raw) });
                  }}
                  aria-label={`Variazione percentuale di ${r.name}`}
                />
                <span className="text-ink-3">%</span>
              </span>
              <span className="flex w-24 items-center justify-end gap-1">
                <span className="code text-[15px] text-ink-2">{listPrice(100, r)} €</span>
                {r.id !== "base" && (
                  <button onClick={() => setRows((xs) => xs.filter((x) => x.id !== r.id))} className="grid size-9 place-items-center text-ink-3 hover:text-danger" aria-label={`Elimina ${r.name}`}>
                    <Trash2 className="size-4" aria-hidden />
                  </button>
                )}
              </span>
            </li>
          ))}
        </ul>
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-hair-soft p-4">
          <Button variant="quiet" size="sm" onClick={() => setRows((xs) => [...xs, { id: `l${Date.now().toString(36)}`, name: `Fascia ${xs.length + 1}`, pct: -10 }])}>
            <Plus className="size-4" aria-hidden /> Aggiungi fascia
          </Button>
          <span className="flex items-center gap-2">
            <span className="text-sm text-ink-3">Esempio su un pezzo da 100 €</span>
            <Button
              disabled={!dirty || !valid}
              onClick={() => {
                saveListini(rows.map((r) => ({ ...r, name: r.name.trim() })));
                setSaved(true);
              }}
            >
              Salva listini
            </Button>
          </span>
        </div>
      </Panel>

      <Panel title="Prezzo suggerito dell'usato" className="mt-6">
        <div className="p-4">
          <p className="text-[15px] text-ink-2">Durante la catalogazione il prezzo base viene proposto come quota del prezzo del ricambio nuovo, secondo le condizioni. Se la tipologia è già oltre la scorta massima, la proposta scende del 10%.</p>
          <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {(Object.keys(USED_SHARE) as Condition[]).map((c) => (
              <div key={c} className="rounded border border-hair-soft bg-carton px-3 py-2">
                <dt className="text-sm text-ink-2"><b className="code">{c}</b> {CONDITIONS[c].label}</dt>
                <dd className="code text-[22px] font-bold">{Math.round(USED_SHARE[c] * 100)}%</dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-[13px] text-ink-3">Quote dimostrative: il prezzo del nuovo arriverà dalla banca dati ricambi scelta.</p>
        </div>
      </Panel>
    </div>
  );
}
