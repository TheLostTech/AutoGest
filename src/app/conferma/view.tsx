"use client";

import { useState } from "react";
import Link from "next/link";
import { BRAND } from "@/lib/config";
import { EMAIL_CONFERMATA, LINK_NON_VALIDO } from "@/lib/accesso/conferma";
import { Button, Field, Notice } from "@/components/ui";

// Conferma dell'email del titolare: dal link dell'email, con la password scelta alla registrazione (api/conferma).
// Riuscita: la prova di 15 giorni è partita e la sessione è già aperta nell'azienda, si va al lavoro.
export function ConfermaView({ token }: { token: string }) {
  const [password, setPassword] = useState("");
  const [errore, setErrore] = useState(token ? "" : LINK_NON_VALIDO);
  const [linkScaduto, setLinkScaduto] = useState(!token);
  const [attesa, setAttesa] = useState(false);
  const [fatta, setFatta] = useState(false);

  async function invia(ev: React.FormEvent) {
    ev.preventDefault();
    setErrore("");
    setAttesa(true);
    let r: Response;
    try {
      r = await fetch("/api/conferma", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ token, password }) });
    } catch {
      setErrore("Non riesco a collegarmi al server. Controlla la rete e riprova.");
      setAttesa(false);
      return;
    }
    const corpo = (await r.json().catch(() => null)) as { error?: string; accesso?: boolean } | null;
    if (!r.ok) {
      setErrore(corpo?.error ?? "Non è stato possibile confermare l'email. Riprova.");
      // Link non più valido o email già confermata: da qui non si va avanti, si passa dalla pagina di accesso
      setLinkScaduto(r.status === 400 || r.status === 409);
      setAttesa(false);
      return;
    }
    setFatta(true);
    // Navigazione completa: i dati dell'azienda si caricano da zero
    window.location.assign(corpo?.accesso === false ? "/accesso" : "/");
  }

  return (
    <main className="grid min-h-dvh place-items-center bg-ground px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <div className="code text-[28px] font-bold uppercase leading-none tracking-wide text-band">
            {BRAND.azienda.replace(/\s*4\.0$/, "")} <span className="text-[#F4B500]">4.0</span>
          </div>
          <p className="mt-1 text-[14px] font-medium text-ink-3">Gestionale autodemolizione</p>
        </div>
        <form onSubmit={invia} className="label-sheet space-y-4 p-5" noValidate>
          <h1 className="code text-[18px] font-bold uppercase tracking-wide text-ink">Conferma l&apos;email</h1>
          {fatta ? (
            <div role="status">
              <Notice tone="ok">{EMAIL_CONFERMATA} Entro…</Notice>
            </div>
          ) : (
            <>
              <p className="text-[15px] text-ink-2">Conferma la tua email: scrivi la password che hai scelto quando ti sei registrato.</p>
              {errore && (
                <div role="alert">
                  <Notice tone="danger">{errore}</Notice>
                </div>
              )}
              {!linkScaduto && (
                <>
                  <Field label="Password">
                    <input className="field" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required autoFocus />
                  </Field>
                  <Button type="submit" size="lg" className="w-full" disabled={attesa || !password}>
                    {attesa ? "Controllo…" : "Conferma e inizia la prova"}
                  </Button>
                </>
              )}
            </>
          )}
        </form>
        <div className="mt-4 text-center">
          <Link href="/accesso" className="inline-flex min-h-11 items-center px-2 text-[14px] font-semibold text-ink-3 underline">
            Vai alla pagina di accesso
          </Link>
        </div>
      </div>
    </main>
  );
}
