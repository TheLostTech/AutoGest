"use client";

import { useState } from "react";
import { Button, Field, Notice, PageTitle } from "@/components/ui";
import { chiama } from "../comune";

export default function NuovaAzienda() {
  const [nome, setNome] = useState("");
  const [errore, setErrore] = useState("");
  const [attesa, setAttesa] = useState(false);

  async function crea(ev: React.FormEvent) {
    ev.preventDefault();
    setAttesa(true);
    setErrore("");
    const r = await chiama<{ id: string }>("/api/piattaforma/aziende", { method: "POST", corpo: { nome } });
    if (!r.ok) {
      setErrore(r.messaggio);
      setAttesa(false);
      return;
    }
    window.location.assign(`/piattaforma/aziende/${r.dati.id}`);
  }

  return (
    <div className="mx-auto max-w-xl">
      <PageTitle title="Nuova azienda" sub="L'azienda parte vuota: nessun veicolo, nessun ricambio, nessun dato di prova. Dopo la crei i suoi utenti." />
      {errore && (
        <div role="alert" className="mb-4">
          <Notice tone="danger">{errore}</Notice>
        </div>
      )}
      <form onSubmit={crea} className="space-y-4 rounded-md border border-hair bg-label p-4">
        <Field label="Nome dell'azienda">
          <input className="field" value={nome} onChange={(e) => setNome(e.target.value)} minLength={2} maxLength={80} required autoFocus />
        </Field>
        <Button type="submit" disabled={attesa || nome.trim().length < 2}>
          {attesa ? "Creo…" : "Crea azienda"}
        </Button>
      </form>
    </div>
  );
}
