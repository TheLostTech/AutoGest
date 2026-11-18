"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, FileText, Plus, UserPlus } from "lucide-react";
import { Button, Field, Notice, PageTitle, Panel } from "@/components/ui";
import { RUOLI, RUOLO_LABEL } from "@/lib/accesso/ruoli";
import { RICHIESTA_MAX_BYTE } from "@/lib/accesso/richieste";
import type { Role } from "@/lib/types";
import { chiama } from "../../comune";

type VoceRichiesta = { azione: string; quando: string; autore: string; fileId?: string; estremi?: string };
type Utente = { id: string; nome: string; email: string | null; ruoli: Role[]; conPassword: boolean; conPin: boolean; attivo: boolean; richieste: VoceRichiesta[] };
type Dispositivo = { id: string; nome: string; creato: string; revocato: string | null; bloccato: boolean };

const data = (iso: string) => new Date(iso).toLocaleString("it-IT", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

// Richiesta scritta dell'azienda: file (PDF, JPEG, PNG) e/o gli estremi. Il file si carica quando si conferma.
type DatiRichiesta = { file: File | null; estremi: string };
const richiestaVuota: DatiRichiesta = { file: null, estremi: "" };

async function preparaRichiesta(aziendaId: string, r: DatiRichiesta): Promise<{ ok: true; richiesta: { fileId?: string; estremi?: string } } | { ok: false; messaggio: string }> {
  const richiesta: { fileId?: string; estremi?: string } = {};
  if (r.estremi.trim()) richiesta.estremi = r.estremi.trim();
  if (r.file) {
    if (r.file.size > RICHIESTA_MAX_BYTE) return { ok: false, messaggio: "Il file è troppo grande: massimo 10 MB." };
    const f = new FormData();
    f.set("aziendaId", aziendaId);
    f.set("file", r.file);
    try {
      const res = await fetch("/api/piattaforma/richieste", { method: "POST", body: f });
      const j = (await res.json().catch(() => ({}))) as { fileId?: string; error?: string };
      if (!res.ok || !j.fileId) return { ok: false, messaggio: j.error ?? "Non riesco a caricare il file." };
      richiesta.fileId = j.fileId;
    } catch {
      return { ok: false, messaggio: "Non riesco a caricare il file. Riprova." };
    }
  }
  return { ok: true, richiesta };
}

function CampiRichiesta({ valore, onChange, obbligatoria }: { valore: DatiRichiesta; onChange: (v: DatiRichiesta) => void; obbligatoria: boolean }) {
  return (
    <fieldset className="space-y-3 rounded-md border border-hair-soft p-3">
      <legend className="px-1 text-sm font-semibold text-ink">Richiesta scritta dell&apos;azienda {obbligatoria ? "(obbligatoria)" : "(facoltativa)"}</legend>
      <Field label="Allega il file" hint="PDF, JPEG o PNG, al massimo 10 MB.">
        <input type="file" accept="application/pdf,image/jpeg,image/png" className="field" onChange={(e) => onChange({ ...valore, file: e.target.files?.[0] ?? null })} />
      </Field>
      <Field label="Estremi" hint="Data e chi la firma, per esempio «12/11/2026, firmata dal titolare Mario Rossi».">
        <input className="field" value={valore.estremi} maxLength={500} onChange={(e) => onChange({ ...valore, estremi: e.target.value })} />
      </Field>
    </fieldset>
  );
}

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

export default function SchedaAzienda() {
  const { id } = useParams<{ id: string }>();
  const [azienda, setAzienda] = useState<{ id: string; nome: string } | null>(null);
  const [utenti, setUtenti] = useState<Utente[] | null>(null);
  const [dispositivi, setDispositivi] = useState<Dispositivo[] | null>(null);
  const [errore, setErrore] = useState("");
  const [fatto, setFatto] = useState("");
  const [nuovo, setNuovo] = useState(false);
  const [modifica, setModifica] = useState<string | null>(null);

  const carica = useCallback(async () => {
    const [u, d] = await Promise.all([
      chiama<{ azienda: { id: string; nome: string }; utenti: Utente[] }>(`/api/piattaforma/aziende/${id}/utenti`),
      chiama<{ dispositivi: Dispositivo[] }>(`/api/piattaforma/aziende/${id}/dispositivi`),
    ]);
    if (u.ok) {
      setAzienda(u.dati.azienda);
      setUtenti(u.dati.utenti);
    } else setErrore(u.messaggio);
    if (d.ok) setDispositivi(d.dati.dispositivi);
  }, [id]);
  useEffect(() => {
    // Lettura iniziale dal server al caricamento della pagina
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void carica();
  }, [carica]);

  async function dispositivo(d: Dispositivo, azione: "revoca" | "sblocca") {
    if (azione === "revoca" && !confirm(`Revocare «${d.nome}»? Chi lo sta usando esce subito.`)) return;
    setErrore("");
    const r = await chiama(`/api/piattaforma/aziende/${id}/dispositivi`, { method: "POST", corpo: { dispositivoId: d.id, azione } });
    if (!r.ok) setErrore(r.messaggio);
    else setFatto(azione === "revoca" ? `«${d.nome}» revocato.` : `«${d.nome}» sbloccato.`);
    await carica();
  }

  return (
    <div>
      <Link href="/piattaforma" className="mb-3 inline-flex items-center gap-1.5 text-[15px] font-semibold text-band hover:underline">
        <ArrowLeft className="size-4" aria-hidden /> Aziende
      </Link>
      <PageTitle
        title={azienda?.nome ?? "Azienda"}
        sub="Chi può entrare, con quali ruoli e come. Ogni modifica resta nel registro attività dell'azienda."
        actions={
          <Button onClick={() => { setNuovo(true); setModifica(null); setFatto(""); }}>
            <UserPlus className="size-5" aria-hidden />
            Nuovo utente
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
            <Notice tone="ok">{fatto}</Notice>
          </div>
        )}
      </div>

      {nuovo && (
        <NuovoUtente
          aziendaId={id}
          onChiudi={() => setNuovo(false)}
          onFatto={async (m) => {
            setNuovo(false);
            setFatto(m);
            await carica();
          }}
        />
      )}

      <section className="mb-8">
        <h2 className="mb-3 text-[20px] font-bold text-ink">Utenti</h2>
        {!utenti && !errore && <p className="text-ink-2">Carico gli utenti…</p>}
        {utenti && utenti.length === 0 && <p className="text-ink-2">Nessun utente. Crea il primo con «Nuovo utente».</p>}
        {utenti && utenti.length > 0 && (
          <Panel>
            <ul className="divide-y divide-hair-soft">
              {utenti.map((u) => (
                <li key={u.id} className="px-4 py-3.5">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="min-w-48 flex-1">
                      <span className="block font-semibold text-ink">
                        {u.nome} {!u.attivo && <span className="ml-1 rounded bg-danger-bg px-2 py-0.5 text-[13px] font-semibold text-danger">Disattivato</span>}
                      </span>
                      <span className="block text-sm text-ink-2">
                        {u.ruoli.map((r) => RUOLO_LABEL[r]).join(", ") || "nessun ruolo"} · accesso: {[u.conPassword ? `email${u.email ? ` (${u.email})` : ""} e password` : "", u.conPin ? "PIN" : ""].filter(Boolean).join(" + ") || "nessuno"}
                      </span>
                    </span>
                    <Button size="sm" variant="secondary" onClick={() => { setModifica(modifica === u.id ? null : u.id); setNuovo(false); setFatto(""); }}>
                      {modifica === u.id ? "Chiudi" : "Modifica"}
                    </Button>
                  </div>
                  {u.richieste.length > 0 && (
                    <ul className="mt-2 space-y-1 text-sm text-ink-2">
                      {u.richieste.map((r, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <FileText className="mt-0.5 size-4 shrink-0 text-ink-3" aria-hidden />
                          <span className="min-w-0">
                            {r.azione} · {data(r.quando)} · {r.autore}
                            {r.estremi ? ` · ${r.estremi}` : ""}
                            {r.fileId && (
                              <>
                                {" · "}
                                <a className="font-semibold text-band hover:underline" href={`/api/piattaforma/richieste/${r.fileId}?aziendaId=${encodeURIComponent(id)}`}>
                                  Scarica il file
                                </a>
                              </>
                            )}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                  {modifica === u.id && (
                    <ModificaUtente
                      aziendaId={id}
                      utente={u}
                      onFatto={async (m) => {
                        setModifica(null);
                        setFatto(m);
                        await carica();
                      }}
                    />
                  )}
                </li>
              ))}
            </ul>
          </Panel>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-[20px] font-bold text-ink">Dispositivi</h2>
        {dispositivi && dispositivi.length === 0 && <p className="text-ink-2">Nessun dispositivo registrato. Lo registra il responsabile dalle impostazioni dell&apos;azienda.</p>}
        {dispositivi && dispositivi.length > 0 && (
          <Panel>
            <ul className="divide-y divide-hair-soft">
              {dispositivi.map((d) => (
                <li key={d.id} className="flex flex-wrap items-center gap-3 px-4 py-3.5">
                  <span className="min-w-48 flex-1">
                    <span className="block font-semibold text-ink">{d.nome}</span>
                    <span className="block text-sm text-ink-2">
                      Registrato il {data(d.creato)}
                      {d.revocato ? ` · revocato il ${data(d.revocato)}` : d.bloccato ? " · bloccato dopo troppi PIN sbagliati" : ""}
                    </span>
                  </span>
                  {!d.revocato && d.bloccato && (
                    <Button size="sm" variant="secondary" onClick={() => void dispositivo(d, "sblocca")}>
                      Sblocca
                    </Button>
                  )}
                  {!d.revocato && (
                    <Button size="sm" variant="danger" onClick={() => void dispositivo(d, "revoca")}>
                      Revoca
                    </Button>
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

function NuovoUtente({ aziendaId, onChiudi, onFatto }: { aziendaId: string; onChiudi: () => void; onFatto: (m: string) => Promise<void> }) {
  const [nome, setNome] = useState("");
  const [ruoli, setRuoli] = useState<Role[]>([]);
  const [conEmail, setConEmail] = useState(false);
  const [conPin, setConPin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pin, setPin] = useState("");
  const [richiesta, setRichiesta] = useState(richiestaVuota);
  const [errore, setErrore] = useState("");
  const [attesa, setAttesa] = useState(false);

  async function invia(ev: React.FormEvent) {
    ev.preventDefault();
    setErrore("");
    if (ruoli.length === 0) return setErrore("Scegli almeno un ruolo.");
    if (!conEmail && !conPin) return setErrore("Scegli come entra: email e password, PIN, o tutti e due.");
    if (!richiesta.file && !richiesta.estremi.trim()) return setErrore("Serve la richiesta scritta dell'azienda: allega il file o scrivi gli estremi.");
    setAttesa(true);
    const p = await preparaRichiesta(aziendaId, richiesta);
    if (!p.ok) {
      setErrore(p.messaggio);
      setAttesa(false);
      return;
    }
    const r = await chiama(`/api/piattaforma/aziende/${aziendaId}/utenti`, {
      method: "POST",
      corpo: { nome, ruoli, ...(conEmail ? { email, password } : {}), ...(conPin ? { pin } : {}), richiesta: p.richiesta },
    });
    setAttesa(false);
    if (!r.ok) return setErrore(r.messaggio);
    await onFatto(`Utente «${nome.trim()}» creato.`);
  }

  return (
    <form onSubmit={invia} className="mb-8 space-y-4 rounded-md border border-hair bg-label p-4">
      <h2 className="text-[20px] font-bold text-ink">Nuovo utente</h2>
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
          <input type="checkbox" checked={conEmail} onChange={(e) => setConEmail(e.target.checked)} /> Email e password (da qualunque dispositivo)
        </label>
        {conEmail && (
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Email">
              <input className="field" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="off" required />
            </Field>
            <Field label="Password" hint="Almeno 8 caratteri.">
              <input className="field" type="password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={8} autoComplete="new-password" required />
            </Field>
          </div>
        )}
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={conPin} onChange={(e) => setConPin(e.target.checked)} /> PIN (solo dai dispositivi dell&apos;azienda)
        </label>
        {conPin && (
          <Field label="PIN" hint="4 cifre.">
            <input className="field max-w-40" inputMode="numeric" pattern="[0-9]{4}" maxLength={4} value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))} autoComplete="off" required />
          </Field>
        )}
      </fieldset>
      <CampiRichiesta valore={richiesta} onChange={setRichiesta} obbligatoria />
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={attesa}>
          <Plus className="size-5" aria-hidden />
          {attesa ? "Creo…" : "Crea utente"}
        </Button>
        <Button type="button" variant="quiet" onClick={onChiudi}>
          Annulla
        </Button>
      </div>
    </form>
  );
}

function ModificaUtente({ aziendaId, utente, onFatto }: { aziendaId: string; utente: Utente; onFatto: (m: string) => Promise<void> }) {
  const [ruoli, setRuoli] = useState<Role[]>(utente.ruoli);
  const [pin, setPin] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [richiesta, setRichiesta] = useState(richiestaVuota);
  const [errore, setErrore] = useState("");
  const [attesa, setAttesa] = useState(false);

  const stessiRuoli = ruoli.length === utente.ruoli.length && ruoli.every((r) => utente.ruoli.includes(r));

  async function invia(cambi: Record<string, unknown>, messaggio: string, conferma?: string) {
    setErrore("");
    if (conferma && !confirm(conferma)) return;
    const serveRichiesta = "ruoli" in cambi;
    if (serveRichiesta && !richiesta.file && !richiesta.estremi.trim()) return setErrore("Per cambiare i ruoli serve la richiesta scritta dell'azienda: allega il file o scrivi gli estremi.");
    setAttesa(true);
    const p = await preparaRichiesta(aziendaId, richiesta);
    if (!p.ok) {
      setErrore(p.messaggio);
      setAttesa(false);
      return;
    }
    const r = await chiama(`/api/piattaforma/utenti/${utente.id}`, { method: "PATCH", corpo: { aziendaId, ...cambi, richiesta: p.richiesta } });
    setAttesa(false);
    if (!r.ok) return setErrore(r.messaggio);
    await onFatto(cambi.attivo === true ? messaggio : `${messaggio} Le sessioni aperte di ${utente.nome} sono state chiuse.`);
  }

  return (
    <div className="mt-3 space-y-5 rounded-md border border-hair-soft bg-ground p-4">
      {errore && (
        <div role="alert">
          <Notice tone="danger">{errore}</Notice>
        </div>
      )}
      <CampiRichiesta valore={richiesta} onChange={setRichiesta} obbligatoria={false} />
      <div className="space-y-3">
        <Ruoli valore={ruoli} onChange={setRuoli} />
        <Button size="sm" disabled={attesa || stessiRuoli || ruoli.length === 0} onClick={() => void invia({ ruoli }, "Ruoli aggiornati.")}>
          Salva i ruoli (serve la richiesta)
        </Button>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <Field label={utente.conPin ? "Nuovo PIN" : "Dai un PIN"} hint="4 cifre.">
          <input className="field max-w-40" inputMode="numeric" pattern="[0-9]{4}" maxLength={4} value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))} autoComplete="off" />
        </Field>
        <Button size="sm" variant="secondary" disabled={attesa || pin.length !== 4} onClick={() => void invia({ pin }, "PIN reimpostato.")}>
          Reimposta il PIN
        </Button>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        {!utente.conPassword && (
          <Field label="Email">
            <input className="field" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="off" />
          </Field>
        )}
        <Field label={utente.conPassword ? "Nuova password" : "Password"} hint="Almeno 8 caratteri.">
          <input className="field" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
        </Field>
        <Button size="sm" variant="secondary" disabled={attesa || password.length < 8 || (!utente.conPassword && !email.trim())} onClick={() => void invia({ password, ...(utente.conPassword ? {} : { email }) }, utente.conPassword ? "Password reimpostata." : "Accesso con email attivato.")}>
          {utente.conPassword ? "Reimposta la password" : "Attiva email e password"}
        </Button>
      </div>
      <div>
        {utente.attivo ? (
          <Button size="sm" variant="danger" disabled={attesa} onClick={() => void invia({ attivo: false }, "Utente disattivato.", `Disattivare ${utente.nome}? Non potrà più entrare e le sue sessioni si chiudono subito.`)}>
            Disattiva
          </Button>
        ) : (
          <Button size="sm" variant="secondary" disabled={attesa} onClick={() => void invia({ attivo: true }, "Utente riattivato.")}>
            Riattiva
          </Button>
        )}
      </div>
    </div>
  );
}
