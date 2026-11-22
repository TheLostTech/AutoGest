"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Plus, UserPlus } from "lucide-react";
import { Button, Field, Notice, PageTitle, Panel } from "@/components/ui";
import { useSessione } from "@/lib/accesso/client";
import { fetchAzienda } from "@/lib/accesso/azienda-client";
import { RUOLI, RUOLO_LABEL } from "@/lib/accesso/ruoli";
import { PASSWORD_MIN } from "@/lib/accesso/registrazione";
import type { Role } from "@/lib/types";

type Persona = { id: string; nome: string; email: string | null; ruoli: Role[]; conPassword: boolean; conPin: boolean; attivo: boolean };
type Esito = { ok: true; dati: Record<string, unknown> } | { ok: false; messaggio: string };

async function chiama(url: string, method = "GET", corpo?: unknown): Promise<Esito> {
  try {
    const r = await fetchAzienda(url, {
      method,
      cache: "no-store",
      ...(corpo !== undefined ? { headers: { "content-type": "application/json" }, body: JSON.stringify(corpo) } : {}),
    });
    const j = (await r.json().catch(() => ({}))) as Record<string, unknown>;
    if (!r.ok) return { ok: false, messaggio: typeof j.error === "string" ? j.error : "Operazione non riuscita. Riprova." };
    return { ok: true, dati: j };
  } catch {
    return { ok: false, messaggio: "Non riesco a raggiungere il server. Riprova." };
  }
}
const avv = (d: Record<string, unknown>) => (typeof d.avviso === "string" ? ` ${d.avviso}` : "");
const accessoDi = (p: Persona) => [p.conPassword ? `email${p.email ? ` (${p.email})` : ""} e password` : "", p.conPin ? (p.conPassword ? "PIN" : "solo PIN") : ""].filter(Boolean).join(" + ") || "nessuno";

function Ruoli({ valore, onChange }: { valore: Role[]; onChange: (r: Role[]) => void }) {
  return (
    <fieldset>
      <legend className="mb-1.5 text-sm font-semibold text-ink">Ruoli (anche più di uno)</legend>
      <div className="flex flex-wrap gap-2">
        {RUOLI.map((r) => (
          <label key={r} className="inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-md border border-hair bg-label px-3 text-[15px]">
            <input type="checkbox" checked={valore.includes(r)} onChange={(e) => onChange(e.target.checked ? [...valore, r] : valore.filter((x) => x !== r))} />
            {RUOLO_LABEL[r]}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export default function Persone() {
  const { accesso } = useSessione();
  const [persone, setPersone] = useState<Persona[] | null>(null);
  const [io, setIo] = useState("");
  const [errore, setErrore] = useState("");
  const [fatto, setFatto] = useState("");
  const [nuova, setNuova] = useState(false);
  const [modifica, setModifica] = useState<string | null>(null);

  const titolare = !!accesso?.ruoli.includes("responsabile");

  const carica = useCallback(async () => {
    const r = await chiama("/api/azienda/persone");
    if (!r.ok) return setErrore(r.messaggio);
    setPersone(r.dati.persone as Persona[]);
    setIo(typeof r.dati.io === "string" ? r.dati.io : "");
  }, []);
  useEffect(() => {
    // Lettura iniziale dal server al caricamento della pagina
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (titolare) void carica();
  }, [titolare, carica]);

  if (accesso && !titolare) {
    return (
      <div className="mx-auto max-w-4xl">
        <PageTitle title="Persone" />
        <Notice tone="warn">Gli accessi delle persone li gestisce solo il responsabile.</Notice>
      </div>
    );
  }

  const fine = async (m: string) => {
    setNuova(false);
    setModifica(null);
    setErrore("");
    setFatto(m);
    await carica();
  };

  return (
    <div className="mx-auto max-w-4xl">
      <PageTitle
        title="Persone"
        sub="Chi lavora in azienda, con quali ruoli e come entra: con email e password da qualunque dispositivo, o solo con il PIN dai dispositivi dell'azienda."
        actions={
          <Button onClick={() => { setNuova(true); setModifica(null); setFatto(""); }}>
            <UserPlus className="size-5" aria-hidden />
            Aggiungi persona
          </Button>
        }
      />
      <div className="mb-4 space-y-3">
        {errore && (
          <div role="alert">
            <Notice tone="danger">{errore}</Notice>
          </div>
        )}
        {fatto && (
          <div role="status">
            <Notice tone={fatto.includes("registro") ? "warn" : "ok"}>{fatto}</Notice>
          </div>
        )}
      </div>

      {nuova && <NuovaPersona onChiudi={() => setNuova(false)} onFatto={fine} />}

      {!persone && !errore && (
        <p className="flex items-center gap-2 text-ink-2">
          <Loader2 className="size-5 animate-spin" aria-hidden /> Carico le persone…
        </p>
      )}
      {persone && (
        <Panel>
          <ul className="divide-y divide-hair-soft">
            {persone.map((p) => (
              <li key={p.id} className="px-4 py-3.5">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="min-w-0 flex-1">
                    <span className="block font-semibold text-ink">
                      {p.nome}
                      {p.id === io && <span className="ml-2 text-[13px] font-semibold text-band">(tu)</span>}
                      {!p.attivo && <span className="ml-2 rounded bg-danger-bg px-2 py-0.5 text-[13px] font-semibold text-danger">Sospeso</span>}
                    </span>
                    <span className="block text-[14px] text-ink-2">
                      {p.ruoli.map((r) => RUOLO_LABEL[r]).join(", ") || "nessun ruolo"} · accesso: {accessoDi(p)}
                    </span>
                  </span>
                  <Button size="sm" variant="secondary" onClick={() => { setModifica(modifica === p.id ? null : p.id); setNuova(false); setFatto(""); }}>
                    {modifica === p.id ? "Chiudi" : "Modifica"}
                  </Button>
                </div>
                {modifica === p.id && <ModificaPersona persona={p} io={p.id === io} onFatto={fine} />}
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </div>
  );
}

function NuovaPersona({ onChiudi, onFatto }: { onChiudi: () => void; onFatto: (m: string) => Promise<void> }) {
  const [nome, setNome] = useState("");
  const [ruoli, setRuoli] = useState<Role[]>([]);
  const [modo, setModo] = useState<"pin" | "email">("pin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pin, setPin] = useState("");
  const [errore, setErrore] = useState("");
  const [attesa, setAttesa] = useState(false);

  async function invia(ev: React.FormEvent) {
    ev.preventDefault();
    setErrore("");
    if (ruoli.length === 0) return setErrore("Scegli almeno un ruolo.");
    setAttesa(true);
    const r = await chiama("/api/azienda/persone", "POST", { nome, ruoli, ...(modo === "email" ? { email, password } : { pin }) });
    setAttesa(false);
    if (!r.ok) return setErrore(r.messaggio);
    await onFatto(`«${nome.trim()}» può entrare.${avv(r.dati)}`);
  }

  return (
    <form onSubmit={invia} className="mb-8 space-y-4 rounded-md border border-hair bg-label p-4">
      <h2 className="text-[20px] font-bold text-ink">Aggiungi persona</h2>
      {errore && (
        <div role="alert">
          <Notice tone="danger">{errore}</Notice>
        </div>
      )}
      <Field label="Nome e cognome">
        <input className="field" value={nome} onChange={(e) => setNome(e.target.value)} minLength={2} maxLength={80} required />
      </Field>
      <Ruoli valore={ruoli} onChange={setRuoli} />
      <fieldset className="space-y-3">
        <legend className="mb-1.5 text-sm font-semibold text-ink">Come entra</legend>
        <label className="flex items-center gap-2">
          <input type="radio" name="modo" checked={modo === "pin"} onChange={() => setModo("pin")} /> Solo PIN (dai dispositivi dell&apos;azienda)
        </label>
        <label className="flex items-center gap-2">
          <input type="radio" name="modo" checked={modo === "email"} onChange={() => setModo("email")} /> Email e password (da qualunque dispositivo)
        </label>
        {modo === "pin" ? (
          <Field label="PIN" hint="4 cifre.">
            <input className="field max-w-40" inputMode="numeric" pattern="[0-9]{4}" maxLength={4} value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))} autoComplete="off" required />
          </Field>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Email">
              <input className="field" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="off" required />
            </Field>
            <Field label="Password" hint={`Almeno ${PASSWORD_MIN} caratteri.`}>
              <input className="field" type="password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={PASSWORD_MIN} maxLength={128} autoComplete="new-password" required />
            </Field>
          </div>
        )}
      </fieldset>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={attesa}>
          <Plus className="size-5" aria-hidden />
          {attesa ? "Creo…" : "Crea l'accesso"}
        </Button>
        <Button type="button" variant="quiet" onClick={onChiudi}>
          Annulla
        </Button>
      </div>
    </form>
  );
}

function ModificaPersona({ persona: p, io, onFatto }: { persona: Persona; io: boolean; onFatto: (m: string) => Promise<void> }) {
  const [ruoli, setRuoli] = useState<Role[]>(p.ruoli);
  const [pin, setPin] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [errore, setErrore] = useState("");
  const [attesa, setAttesa] = useState(false);

  const stessiRuoli = ruoli.length === p.ruoli.length && ruoli.every((r) => p.ruoli.includes(r));

  async function invia(cambi: Record<string, unknown>, messaggio: string, conferma?: string) {
    setErrore("");
    if (conferma && !confirm(conferma)) return;
    setAttesa(true);
    const r = await chiama(`/api/azienda/persone/${encodeURIComponent(p.id)}`, "PATCH", cambi);
    setAttesa(false);
    if (!r.ok) return setErrore(r.messaggio);
    // Cambiati i propri ruoli, PIN o password: la propria sessione è chiusa, si rientra
    if (r.dati.esci === true) {
      window.location.assign("/accesso");
      return;
    }
    await onFatto((cambi.attivo === true ? messaggio : `${messaggio} Le sessioni aperte di ${p.nome} sono state chiuse.`) + avv(r.dati));
  }

  const avvisoIo = io ? " Si chiude anche la tua sessione: dovrai entrare di nuovo." : "";

  return (
    <div className="mt-3 space-y-5 rounded-md border border-hair-soft bg-ground p-4">
      {errore && (
        <div role="alert">
          <Notice tone="danger">{errore}</Notice>
        </div>
      )}
      <div className="space-y-3">
        <Ruoli valore={ruoli} onChange={setRuoli} />
        <Button size="sm" disabled={attesa || stessiRuoli || ruoli.length === 0} onClick={() => void invia({ ruoli }, "Ruoli aggiornati.", io ? `Cambiare i tuoi ruoli?${avvisoIo}` : undefined)}>
          Salva i ruoli
        </Button>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <Field label={p.conPin ? "Nuovo PIN" : "Dai un PIN"} hint="4 cifre.">
          <input className="field max-w-40" inputMode="numeric" pattern="[0-9]{4}" maxLength={4} value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))} autoComplete="off" />
        </Field>
        <Button size="sm" variant="secondary" disabled={attesa || pin.length !== 4} onClick={() => void invia({ pin }, "PIN reimpostato.", io ? `Cambiare il tuo PIN?${avvisoIo}` : undefined)}>
          {p.conPin ? "Reimposta il PIN" : "Dai il PIN"}
        </Button>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        {!p.conPassword && (
          <Field label="Email">
            <input className="field" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="off" />
          </Field>
        )}
        <Field label={p.conPassword ? "Nuova password" : "Password"} hint={`Almeno ${PASSWORD_MIN} caratteri.`}>
          <input className="field" type="password" value={password} onChange={(e) => setPassword(e.target.value)} maxLength={128} autoComplete="new-password" />
        </Field>
        <Button
          size="sm"
          variant="secondary"
          disabled={attesa || password.length < PASSWORD_MIN || (!p.conPassword && !email.trim())}
          onClick={() => void invia({ password, ...(p.conPassword ? {} : { email }) }, p.conPassword ? "Password reimpostata." : "Accesso con email attivato.", io ? `Cambiare la tua password?${avvisoIo}` : undefined)}
        >
          {p.conPassword ? "Reimposta la password" : "Attiva email e password"}
        </Button>
      </div>
      {!io && (
        <div>
          {p.attivo ? (
            <Button size="sm" variant="danger" disabled={attesa} onClick={() => void invia({ attivo: false }, `${p.nome} è sospeso.`, `Sospendere ${p.nome}? Non potrà più entrare e le sue sessioni si chiudono subito.`)}>
              Sospendi
            </Button>
          ) : (
            <Button size="sm" variant="secondary" disabled={attesa} onClick={() => void invia({ attivo: true }, `${p.nome} può di nuovo entrare.`)}>
              Riattiva
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
