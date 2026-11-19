"use client";

import { useState } from "react";
import { useStore } from "@/lib/store";
import { datiRegistroErrori, type DatiRegistro } from "@/lib/dati-registro";
import { Button, Field, Notice, Panel } from "@/components/ui";
import type { Vehicle } from "@/lib/types";

// Con Ambiente ma senza Accettazione: la pratica si fa altrove e qui si ricopiano i dati che servono al registro
// rifiuti. Scrivono negli stessi campi della pratica, così attivando l'Accettazione dopo ci sono già.
export function DatiRegistroPanel({ v }: { v: Vehicle }) {
  const setDatiRegistro = useStore((s) => s.setDatiRegistro);
  const [d, setD] = useState<DatiRegistro>({
    nome: v.conferente?.nome ?? "",
    cf: v.conferente?.cf ?? "",
    numero: v.dossier.number ?? "",
    data: v.presaInCarico?.at.slice(0, 10) ?? "",
  });
  const [errori, setErrori] = useState<string[]>([]);
  const [salvato, setSalvato] = useState(false);
  const set = (k: keyof DatiRegistro) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setSalvato(false);
    setD({ ...d, [k]: e.target.value });
  };
  const completi = !!(v.conferente?.nome && v.conferente.cf && v.dossier.number && v.presaInCarico);

  function salva() {
    const e = datiRegistroErrori(d);
    setErrori(e);
    if (e.length) return;
    if (setDatiRegistro(v.id, d).ok) setSalvato(true);
  }

  return (
    <Panel title="Dati per il registro rifiuti">
      <div className="space-y-4 p-4">
        <p className="text-[15px] text-ink-2">
          {completi ? "Dati registrati: il carico del veicolo nel registro è completo." : "Ricopia dalla pratica di demolizione chi ha consegnato il veicolo e il certificato di rottamazione: senza, il carico resta in bozza."}
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Chi ha consegnato">
            <input className="field" value={d.nome} onChange={set("nome")} autoComplete="off" />
          </Field>
          <Field label="Codice fiscale o partita IVA">
            <input className="field code uppercase" value={d.cf} onChange={set("cf")} autoComplete="off" maxLength={20} />
          </Field>
          <Field label="Numero del certificato">
            <input className="field code" value={d.numero} onChange={set("numero")} autoComplete="off" />
          </Field>
          <Field label="Data del certificato">
            <input className="field" type="date" value={d.data} onChange={set("data")} />
          </Field>
        </div>
        {errori.length > 0 && (
          <Notice tone="danger">
            <ul className="space-y-1">
              {errori.map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          </Notice>
        )}
        {salvato && <Notice tone="ok">Dati salvati nel registro rifiuti.</Notice>}
        <Button size="sm" onClick={salva}>Salva</Button>
      </div>
    </Panel>
  );
}
