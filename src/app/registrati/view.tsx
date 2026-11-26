"use client";

import { useState } from "react";
import Link from "next/link";
import { BRAND } from "@/lib/config";
import { Button, Field, Notice } from "@/components/ui";
import { CLAUSOLE_SPECIFICHE, CONDIZIONI } from "@/lib/legale/condizioni";
import { RimandaEmail } from "../accesso/rimanda-email";

// Registrazione libera: dopo l'invio non si entra, si conferma l'email (il link fa partire la prova di 15 giorni).
export function RegistratiView({ prova }: { prova: boolean }) {
  const [azienda, setAzienda] = useState("");
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [telefono, setTelefono] = useState("");
  const [password, setPassword] = useState("");
  const [condizioni, setCondizioni] = useState(false);
  // Approvazione specifica delle clausole onerose (artt. 1341 e 1342 c.c.)
  const [clausole, setClausole] = useState(false);
  // Contatti commerciali: facoltativi e di serie non spuntati
  const [commerciale, setCommerciale] = useState(false);
  const [errore, setErrore] = useState("");
  const [attesa, setAttesa] = useState(false);
  const [fatta, setFatta] = useState(false);
  // false: la registrazione c'è, ma l'email di conferma non è partita (si rimanda da qui o dalla pagina di accesso)
  const [inviata, setInviata] = useState(true);

  async function invia(ev: React.FormEvent) {
    ev.preventDefault();
    setErrore("");
    setAttesa(true);
    let r: Response;
    try {
      r = await fetch("/api/registrazione", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ azienda, nome, email, telefono, password, condizioni, clausole, commerciale }),
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
    const corpo = (await r.json().catch(() => null)) as { inviata?: boolean } | null;
    setInviata(corpo?.inviata !== false);
    setFatta(true);
    setAttesa(false);
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
            <div role="status">
              {inviata ? (
                <Notice tone="ok">Controlla la posta: ti abbiamo mandato il link per attivare la prova.</Notice>
              ) : (
                <Notice tone="warn">La registrazione è fatta, ma non sono riuscito a mandarti l&apos;email con il link per attivare la prova. Rimandala tra qualche minuto.</Notice>
              )}
            </div>
            <p className="text-[15px] text-ink-2">
              L&apos;email arriva a <span className="font-semibold text-ink">{email.trim().toLowerCase()}</span>. Se non la trovi, guarda anche nella posta indesiderata.
            </p>
            <RimandaEmail email={email} />
          </div>
        ) : (
          <form onSubmit={invia} className="label-sheet space-y-4 p-5" noValidate>
            <h1 className="code text-[18px] font-bold uppercase tracking-wide text-ink">Registra la tua azienda</h1>
            <p className="text-[15px] text-ink-2">Prova gratuita di 15 giorni con tutti i moduli.</p>
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
            <Field label="Telefono (facoltativo)" hint="Solo cifre, spazi e +.">
              <input className="field" type="tel" autoComplete="tel" inputMode="tel" maxLength={20} value={telefono} onChange={(e) => setTelefono(e.target.value)} />
            </Field>
            <Field label="Password" hint="Almeno 10 caratteri.">
              <input className="field" type="password" autoComplete="new-password" minLength={10} maxLength={128} value={password} onChange={(e) => setPassword(e.target.value)} required />
            </Field>
            <label className="flex items-start gap-3 text-[15px] text-ink">
              <input type="checkbox" className="mt-0.5 size-6 shrink-0 accent-band" checked={condizioni} onChange={(e) => setCondizioni(e.target.checked)} />
              <span>
                Accetto le{" "}
                <Link href="/condizioni" target="_blank" className="font-semibold text-band underline">
                  condizioni del servizio
                </Link>{" "}
                e l&apos;
                <Link href="/condizioni#accordo" target="_blank" className="font-semibold text-band underline">
                  accordo sul trattamento dei dati
                </Link>
              </span>
            </label>
            <label className="flex items-start gap-3 text-[15px] text-ink">
              <input type="checkbox" className="mt-0.5 size-6 shrink-0 accent-band" checked={clausole} onChange={(e) => setClausole(e.target.checked)} />
              <span>
                Approvo specificamente le{" "}
                <Link href="/condizioni#clausole" target="_blank" className="font-semibold text-band underline">
                  clausole indicate nelle condizioni
                </Link>{" "}
                (artt. 1341 e 1342 c.c.)
              </span>
            </label>
            <ul className="space-y-1 break-words pl-9 text-[13px] leading-snug text-ink-3">
              {CLAUSOLE_SPECIFICHE.map((c) => {
                const i = CONDIZIONI.sezioni.findIndex((s) => s.id === c.sezione);
                return (
                  <li key={c.clausola}>
                    {c.clausola} (punto {i + 1}, {CONDIZIONI.sezioni[i].titolo})
                  </li>
                );
              })}
            </ul>
            <p className="text-[15px] text-ink">
              Ho letto l&apos;
              <Link href="/privacy" target="_blank" className="font-semibold text-band underline">
                informativa privacy
              </Link>
            </p>
            <label className="flex items-start gap-3 text-[15px] text-ink">
              <input type="checkbox" className="mt-0.5 size-6 shrink-0 accent-band" checked={commerciale} onChange={(e) => setCommerciale(e.target.checked)} />
              <span>Acconsento a essere contattato da Lostar Technology per proposte commerciali su Piazzale</span>
            </label>
            <Button type="submit" size="lg" className="w-full" disabled={attesa || !azienda || !nome || !email || !password || !condizioni || !clausole}>
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
