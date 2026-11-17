"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { useStore } from "@/lib/store";
import { Button, Field, Notice, PageTitle, Panel } from "@/components/ui";
import type { RuoloSoggetto, Soggetto } from "@/lib/types";

const RUOLI: { id: RuoloSoggetto; label: string; hint: string }[] = [
  { id: "impianto", label: "Il vostro impianto", hint: "Denominazione, codice fiscale, sede e autorizzazione: compaiono come produttore nei formulari." },
  { id: "destinatario", label: "Destinatari", hint: "Chi riceve i rifiuti: autorizzazione e operazione (es. R13)." },
  { id: "trasportatore", label: "Trasportatori", hint: "Chi trasporta: numero di iscrizione all'Albo gestori ambientali." },
  { id: "intermediario", label: "Intermediari", hint: "Commercianti e intermediari: numero di iscrizione all'Albo." },
];

// Anagrafica dei soggetti dei formulari: si compila una volta, poi nei formulari si sceglie da qui
export default function Soggetti() {
  const { soggetti, saveSoggetto } = useStore();
  const [edit, setEdit] = useState<Soggetto | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  return (
    <div className="mx-auto max-w-4xl">
      <PageTitle title="Soggetti" sub="Impianto, destinatari, trasportatori e intermediari dei formulari. Si inseriscono una volta: nei formulari basta sceglierli." />
      {msg && <div className="mb-5"><Notice tone="ok">{msg}</Notice></div>}

      {edit && (
        <Modulo
          s={edit}
          onCancel={() => setEdit(null)}
          onSave={(s) => {
            saveSoggetto(s);
            setMsg(`${s.nome} salvato.`);
            setEdit(null);
          }}
        />
      )}

      <div className="space-y-6">
        {RUOLI.map((r) => {
          const list = soggetti.filter((s) => s.ruolo === r.id);
          return (
            <Panel
              key={r.id}
              title={r.label}
              action={
                r.id !== "impianto" || list.length === 0 ? (
                  <Button size="sm" variant="quiet" onClick={() => setEdit({ id: `S-${Date.now().toString(36)}`, ruolo: r.id, nome: "", cf: "" })}>
                    <Plus className="size-4" aria-hidden /> Aggiungi
                  </Button>
                ) : undefined
              }
            >
              <p className="px-4 pt-3 text-sm text-ink-3">{r.hint}</p>
              <ul className="divide-y divide-hair-soft">
                {list.map((s) => (
                  <li key={s.id} className="flex flex-wrap items-start justify-between gap-3 px-4 py-3">
                    <div className="min-w-0">
                      <p className="font-semibold">{s.nome}</p>
                      <p className="text-sm text-ink-2">
                        <span className="code">{s.cf}</span>
                        {s.sede && <> · {s.sede}</>}
                        {s.albo && <> · Albo <span className="code">{s.albo}</span></>}
                        {s.operazione && <> · {s.operazione}</>}
                      </p>
                      {s.autorizzazione && <p className="text-sm text-ink-3">{s.autorizzazione}</p>}
                    </div>
                    <Button size="sm" variant="quiet" onClick={() => setEdit(s)}>Modifica</Button>
                  </li>
                ))}
                {list.length === 0 && <li className="px-4 py-3 text-sm text-ink-3">Nessuno inserito.</li>}
              </ul>
            </Panel>
          );
        })}
      </div>
    </div>
  );
}

function Modulo({ s, onSave, onCancel }: { s: Soggetto; onSave: (s: Soggetto) => void; onCancel: () => void }) {
  const [f, setF] = useState<Soggetto>(s);
  const set = (patch: Partial<Soggetto>) => setF((x) => ({ ...x, ...patch }));
  const withAlbo = f.ruolo === "trasportatore" || f.ruolo === "intermediario";
  const withAut = f.ruolo === "impianto" || f.ruolo === "destinatario";
  const valid = f.nome.trim() && f.cf.trim();
  return (
    <Panel title={s.nome ? `Modifica ${s.nome}` : "Nuovo soggetto"} className="mb-6">
      <div className="grid gap-4 p-4 sm:grid-cols-2">
        <Field label="Denominazione">
          <input className="field" value={f.nome} onChange={(e) => set({ nome: e.target.value })} />
        </Field>
        <Field label="Codice fiscale o partita IVA">
          <input className="field code uppercase" value={f.cf} onChange={(e) => set({ cf: e.target.value.toUpperCase().trim() })} />
        </Field>
        <Field label="Sede (unità locale)">
          <input className="field" value={f.sede ?? ""} onChange={(e) => set({ sede: e.target.value || undefined })} />
        </Field>
        {withAut && (
          <Field label="Autorizzazione">
            <input className="field" value={f.autorizzazione ?? ""} onChange={(e) => set({ autorizzazione: e.target.value || undefined })} placeholder="es. Aut. art. 208 D.Lgs. 152/06 n. …" />
          </Field>
        )}
        {withAut && (
          <Field label="Operazione">
            <input className="field code uppercase" value={f.operazione ?? ""} onChange={(e) => set({ operazione: e.target.value.toUpperCase() || undefined })} placeholder="R13" />
          </Field>
        )}
        {withAlbo && (
          <Field label="Iscrizione all'Albo gestori ambientali">
            <input className="field code uppercase" value={f.albo ?? ""} onChange={(e) => set({ albo: e.target.value.toUpperCase() || undefined })} placeholder="TO/000000" />
          </Field>
        )}
        <div className="flex flex-wrap gap-2 sm:col-span-2">
          <Button disabled={!valid} onClick={() => onSave({ ...f, nome: f.nome.trim() })}>Salva</Button>
          <Button variant="quiet" onClick={onCancel}>Annulla</Button>
        </div>
      </div>
    </Panel>
  );
}
