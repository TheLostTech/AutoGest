"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Tablet } from "lucide-react";
import { authClient } from "@/lib/auth/client";
import type { DispositivoAzienda } from "@/lib/auth/pin-dispositivo-client";
import { useSessione } from "@/lib/accesso/client";
import { inviaInSospeso } from "@/lib/sync";
import { segnalaAziendaCambiata } from "@/lib/accesso/azienda-client";
import { Button, Field, Notice, PageTitle, Panel } from "@/components/ui";

const leggiElenco = () =>
  authClient.pinDispositivo
    .elenco()
    .then((r) => {
      if (r.error?.status === 409) segnalaAziendaCambiata();
      return r;
    })
    .catch(() => null);
const data = (iso: string) => new Date(iso).toLocaleDateString("it-IT", { day: "numeric", month: "short", year: "numeric" });

export default function Dispositivi() {
  const { accesso } = useSessione();
  const [elenco, setElenco] = useState<DispositivoAzienda[] | null>(null);
  const [conPassword, setConPassword] = useState(false);
  const [errore, setErrore] = useState("");
  const [nome, setNome] = useState("");
  const [attesa, setAttesa] = useState(false);
  const [fatto, setFatto] = useState("");

  const responsabile = !!accesso?.ruoli.includes("responsabile");

  const applica = useCallback((r: Awaited<ReturnType<typeof leggiElenco>>) => {
    if (!r || r.error || !r.data) {
      setErrore(r?.error?.message ?? "Non riesco a leggere i dispositivi dal server dell'azienda.");
      return;
    }
    setElenco(r.data.dispositivi);
    setConPassword(r.data.passwordSession);
  }, []);
  const carica = () => leggiElenco().then(applica);

  useEffect(() => {
    if (responsabile) void leggiElenco().then(applica);
  }, [responsabile, applica]);

  if (accesso && !responsabile) {
    return (
      <div className="mx-auto max-w-4xl">
        <PageTitle title="Dispositivi" />
        <Notice tone="warn">I dispositivi dell&apos;azienda li gestisce solo il responsabile.</Notice>
      </div>
    );
  }

  const questo = elenco?.find((d) => d.questo && !d.revocato);

  async function registra(ev: React.FormEvent) {
    ev.preventDefault();
    if (!confirm(`Usare questo browser come «${nome.trim()}»? Esci dal tuo account e qui comparirà l'elenco dei nomi con il PIN.`)) return;
    setAttesa(true);
    setFatto("");
    // Prima il lavoro in sospeso, con la sessione ancora valida: la registrazione chiude la sessione del responsabile
    await inviaInSospeso().catch(() => false);
    const r = await authClient.pinDispositivo.registra({ nome: nome.trim() }).catch(() => null);
    if (r?.error?.status === 409) segnalaAziendaCambiata();
    if (!r || r.error) {
      setAttesa(false);
      setErrore(r?.error?.message ?? "Non riesco a registrare il dispositivo. Riprova.");
      return;
    }
    // Da ora è un dispositivo condiviso: si va all'elenco dei nomi (navigazione completa, i dati si scaricano)
    window.location.assign("/accesso");
  }

  async function azione(d: DispositivoAzienda, tipo: "revoca" | "sblocca") {
    if (tipo === "revoca" && !confirm(`Revocare «${d.nome}»? Chi lo sta usando esce subito e il dispositivo torna all'accesso con email.`)) return;
    setFatto("");
    // Sbloccare questo stesso browser chiude la sessione del responsabile: prima il lavoro non ancora inviato
    if (tipo === "sblocca" && d.questo) await inviaInSospeso().catch(() => false);
    const r = await (tipo === "revoca" ? authClient.pinDispositivo.revoca({ dispositivoId: d.id }) : authClient.pinDispositivo.sblocca({ dispositivoId: d.id })).catch(() => null);
    if (r?.error?.status === 409) segnalaAziendaCambiata();
    if (!r || r.error) {
      setErrore(r?.error?.message ?? "Operazione non riuscita. Riprova.");
      return;
    }
    // Sbloccato il tablet su cui si è entrati con la password: si torna all'elenco dei nomi (la sessione è già chiusa)
    if (r.data && "esci" in r.data && r.data.esci) {
      window.location.assign("/accesso");
      return;
    }
    setFatto(tipo === "revoca" ? `«${d.nome}» revocato.` : `«${d.nome}» sbloccato.`);
    await carica();
  }

  return (
    <div className="mx-auto max-w-4xl">
      <PageTitle
        title="Dispositivi"
        sub="Tablet e telefoni dell'azienda usati da più persone: chi lavora tocca il proprio nome e scrive il PIN. Dopo 5 minuti senza tocchi il dispositivo torna all'elenco dei nomi."
      />

      <div className="mb-6 space-y-3">
        {errore && (
          <div role="alert">
            <Notice tone="danger">{errore}</Notice>
          </div>
        )}
        {fatto && (
          <div role="status">
            <Notice tone="ok">{fatto}</Notice>
          </div>
        )}
      </div>

      <section className="mb-8">
        <h2 className="mb-3 text-[20px] font-bold text-ink">Questo browser</h2>
        <Panel>
          <div className="p-4">
            {!elenco ? null : !conPassword ? (
              <Notice tone="info">Per registrare, revocare o sbloccare i dispositivi entra con email e password.</Notice>
            ) : (
              <form onSubmit={registra} className="space-y-4">
                {questo && (
                  <p className="text-[15px] text-ink-2">
                    È già il dispositivo <b className="text-ink">«{questo.nome}»</b>. Registrandolo di nuovo, quello vecchio viene revocato.
                  </p>
                )}
                <Field label="Nome del dispositivo" hint="Come lo riconoscete in azienda, per esempio «Tablet piazzale 1».">
                  <input className="field" value={nome} onChange={(e) => setNome(e.target.value)} maxLength={60} required />
                </Field>
                <Button type="submit" disabled={attesa || !nome.trim()}>
                  <Tablet className="size-5" aria-hidden />
                  {attesa ? "Registro…" : "Usa come dispositivo dell'azienda"}
                </Button>
              </form>
            )}
          </div>
        </Panel>
      </section>

      <section>
        <h2 className="mb-3 text-[20px] font-bold text-ink">Dispositivi registrati</h2>
        {!elenco && !errore && (
          <p className="flex items-center gap-2 text-ink-2">
            <Loader2 className="size-5 animate-spin" aria-hidden /> Carico i dispositivi…
          </p>
        )}
        {elenco && elenco.length === 0 && <p className="text-ink-2">Nessun dispositivo registrato.</p>}
        {elenco && elenco.length > 0 && (
          <Panel>
            <ul className="divide-y divide-hair-soft">
              {elenco.map((d) => (
                <li key={d.id} className="flex flex-wrap items-center gap-3 px-4 py-3.5">
                  <span className="min-w-0 flex-1">
                    <span className="block font-semibold text-ink">
                      {d.nome}
                      {d.questo && !d.revocato && <span className="ml-2 text-[13px] font-semibold text-band">(questo browser)</span>}
                    </span>
                    <span className="block text-[14px] text-ink-2">
                      Registrato il {data(d.creato)}
                      {d.creatoDa ? ` da ${d.creatoDa}` : ""}
                      {d.revocato ? ` · revocato il ${data(d.revocato)}` : ""}
                    </span>
                  </span>
                  <StatoDispositivo d={d} />
                  {conPassword && !d.revocato && (
                    <span className="flex gap-2">
                      {d.bloccato && (
                        <Button size="sm" onClick={() => void azione(d, "sblocca")}>
                          Sblocca
                        </Button>
                      )}
                      <Button size="sm" variant="danger" onClick={() => void azione(d, "revoca")}>
                        Revoca
                      </Button>
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </Panel>
        )}
      </section>
    </div>
  );
}

function StatoDispositivo({ d }: { d: DispositivoAzienda }) {
  const [txt, cls] = d.revocato ? ["Revocato", "bg-hair-soft text-ink-2"] : d.bloccato ? ["Bloccato", "bg-danger-bg text-danger"] : ["Attivo", "bg-ok-bg text-ok"];
  return <span className={`inline-flex h-7 shrink-0 items-center rounded-full px-2.5 text-[13px] font-semibold ${cls}`}>{txt}</span>;
}
