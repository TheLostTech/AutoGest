"use client";

import { useState } from "react";
import Link from "next/link";
import { authClient } from "@/lib/auth/client";
import { BRAND } from "@/lib/config";
import { Button, Field, Notice } from "@/components/ui";

// Dopo la registrazione si entra come da /accesso: sessione, poi l'azienda (la sola del titolare) diventa attiva.
async function entra(email: string, password: string) {
  const r = await authClient.signIn.email({ email, password });
  if (r.error) throw new Error("accesso");
  const aziende = await authClient.organization.list();
  const prima = aziende.data?.[0];
  if (!prima) throw new Error("accesso");
  const a = await authClient.organization.setActive({ organizationId: prima.id });
  if (a.error) throw new Error("accesso");
}

export function RegistratiView({ invito: invitoIniziale, prova }: { invito: string; prova: boolean }) {
  const [azienda, setAzienda] = useState("");
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [invito, setInvito] = useState(invitoIniziale);
  const [condizioni, setCondizioni] = useState(false);
  const [errore, setErrore] = useState("");
  const [attesa, setAttesa] = useState(false);
  // Registrazione fatta ma accesso non riuscito: si entra da /accesso
  const [fatta, setFatta] = useState(false);

  async function invia(ev: React.FormEvent) {
    ev.preventDefault();
    setErrore("");
    setAttesa(true);
    let r: Response;
    try {
      r = await fetch("/api/registrazione", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ azienda, nome, email, password, invito, condizioni }),
      });
    } catch {
      setErrore("Non riesco a collegarmi al server. Controlla la rete e riprova.");
      setAttesa(false);
      return;
    }
    if (r.status !== 201) {
      const corpo = (await r.json().catch(() => null)) as { error?: string } | null;
      setErrore(corpo?.error ?? "Non è stato possibile completare la registrazione. Riprova.");
      setAttesa(false);
      return;
    }
    try {
      await entra(email.trim().toLowerCase(), password);
      // Navigazione completa: i dati dell'azienda si caricano da zero
      window.location.assign("/");
    } catch {
      setFatta(true);
      setAttesa(false);
    }
  }

  return (
    <main className="grid min-h-dvh place-items-center bg-ground px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="code text-[28px] font-bold uppercase leading-none tracking-wide text-band">
            {BRAND.azienda.replace(/\s*4\.0$/, "")} <span className="text-[#F4B500]">4.0</span>
          </div>
          <p className="mt-1 text-[14px] font-medium text-ink-3">Gestionale autodemolizione</p>
        </div>
        {fatta ? (
          <div className="label-sheet space-y-4 p-5">
            <h1 className="code text-[18px] font-bold uppercase tracking-wide text-ink">Registrazione fatta</h1>
            <Notice tone="ok">La tua azienda è pronta. Non sono riuscito a farti entrare da solo: accedi con l&apos;email e la password che hai scelto.</Notice>
            <Link href="/accesso" className="press inline-flex min-h-14 w-full items-center justify-center rounded-md bg-band px-6 text-lg font-semibold text-white">
              Vai all&apos;accesso
            </Link>
          </div>
        ) : (
          <form onSubmit={invia} className="label-sheet space-y-4 p-5" noValidate>
            <h1 className="code text-[18px] font-bold uppercase tracking-wide text-ink">Registra la tua azienda</h1>
            {!invitoIniziale && <Notice>La registrazione è su invito: chiedi il codice a Piazzale.</Notice>}
            {errore && (
              <div role="alert">
                <Notice tone="danger">{errore}</Notice>
              </div>
            )}
            <Field label="Nome dell'azienda">
              <input className="field" type="text" autoComplete="organization" maxLength={80} value={azienda} onChange={(e) => setAzienda(e.target.value)} required autoFocus />
            </Field>
            <Field label="Nome e cognome del titolare">
              <input className="field" type="text" autoComplete="name" maxLength={100} value={nome} onChange={(e) => setNome(e.target.value)} required />
            </Field>
            <Field label="Email">
              <input className="field" type="email" autoComplete="username" inputMode="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </Field>
            <Field label="Password" hint="Almeno 10 caratteri.">
              <input className="field" type="password" autoComplete="new-password" minLength={10} maxLength={128} value={password} onChange={(e) => setPassword(e.target.value)} required />
            </Field>
            <Field label="Codice invito">
              <input
                className="field code tracking-[0.15em] uppercase"
                type="text"
                autoComplete="off"
                autoCapitalize="characters"
                spellCheck={false}
                placeholder="XXXX-XXXX-XXXX"
                value={invito}
                onChange={(e) => setInvito(e.target.value)}
                required
              />
            </Field>
            <label className="flex items-start gap-3 text-[15px] text-ink">
              <input type="checkbox" className="mt-0.5 size-6 shrink-0 accent-band" checked={condizioni} onChange={(e) => setCondizioni(e.target.checked)} />
              <span>
                Accetto le{" "}
                <Link href="/condizioni" target="_blank" className="font-semibold text-band underline">
                  condizioni del servizio
                </Link>
              </span>
            </label>
            <Button type="submit" size="lg" className="w-full" disabled={attesa || !azienda || !nome || !email || !password || !invito || !condizioni}>
              {attesa ? "Registrazione…" : "Registrati"}
            </Button>
            {prova && <p className="text-center text-[13px] text-ink-3">Ambiente di prova: nessun addebito vero</p>}
          </form>
        )}
        <div className="mt-4 text-center">
          <Link href="/accesso" className="inline-flex min-h-11 items-center px-2 text-[14px] font-semibold text-ink-3 underline">
            Hai già un account? Accedi
          </Link>
        </div>
      </div>
    </main>
  );
}
