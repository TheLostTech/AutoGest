"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { authClient } from "@/lib/auth/client";
import type { NomiDispositivo } from "@/lib/auth/pin-dispositivo-client";
import { NomiPin } from "./nomi-pin";
import { RimandaEmail } from "./rimanda-email";
import { CODICE_DA_CONFERMARE, MESSAGGIO_DA_CONFERMARE } from "@/lib/accesso/conferma";
import { BRAND } from "@/lib/config";
import { Button, Field, Notice } from "@/components/ui";

type Passo = "password" | "codice";

// null: questo browser non è un dispositivo dell'azienda (o il server non risponde): accesso con email.
const leggiNomiDispositivo = () =>
  authClient.pinDispositivo
    .nomi()
    .then((r) => r.data ?? null)
    .catch(() => null);

// Dopo l'accesso: super admin alla piattaforma; chi appartiene a un'azienda la attiva (la prima, per ora) e va al lavoro.
async function dopoAccesso(da: string) {
  const s = await authClient.getSession();
  const ruolo = (s.data?.user as { role?: string | null } | undefined)?.role ?? "";
  if (ruolo.split(",").map((r) => r.trim()).includes("superadmin")) return "/piattaforma";
  const aziende = await authClient.organization.list();
  const prima = aziende.data?.[0];
  if (!prima) throw new Error("nessuna-azienda");
  const r = await authClient.organization.setActive({ organizationId: prima.id });
  if (r.error) throw new Error("attiva");
  return da;
}

export function AccessoView({ da }: { da: string }) {
  // Dispositivo dell'azienda (cookie valido): elenco dei nomi + PIN. Altrimenti, o su richiesta, email e password.
  const [dispositivo, setDispositivo] = useState<NomiDispositivo | null | undefined>(undefined);
  const [conEmail, setConEmail] = useState(false);
  const leggiNomi = useCallback(() => leggiNomiDispositivo().then((d) => setDispositivo(d)), []);
  useEffect(() => {
    void leggiNomiDispositivo().then((d) => setDispositivo(d));
  }, []);

  if (dispositivo === undefined) {
    return <main className="grid min-h-dvh place-items-center bg-ground" aria-busy="true" />;
  }
  if (dispositivo && !conEmail) {
    return (
      <main className="grid min-h-dvh place-items-center bg-ground px-4 py-10">
        <NomiPin dati={dispositivo} da={da} onEmail={() => setConEmail(true)} onAggiorna={() => void leggiNomi()} />
      </main>
    );
  }
  return <AccessoEmail da={da} onNomi={dispositivo ? () => setConEmail(false) : undefined} />;
}

function AccessoEmail({ da, onNomi }: { da: string; onNomi?: () => void }) {
  const [passo, setPasso] = useState<Passo>("password");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [codice, setCodice] = useState("");
  const [recupero, setRecupero] = useState(false);
  const [errore, setErrore] = useState("");
  // Titolare che non ha ancora confermato l'email: messaggio e "Rimanda l'email"
  const [daConfermare, setDaConfermare] = useState(false);
  const [attesa, setAttesa] = useState(false);

  async function concludi() {
    try {
      const dove = await dopoAccesso(da);
      // Navigazione completa: i dati dell'azienda si caricano da zero
      window.location.assign(dove);
    } catch (e) {
      setErrore(
        e instanceof Error && e.message === "nessuna-azienda"
          ? "Il tuo account non è collegato a nessuna azienda. Chiedi al responsabile di aggiungerti."
          : "Non riesco a completare l'accesso. Riprova.",
      );
      setAttesa(false);
    }
  }

  async function invia(ev: React.FormEvent) {
    ev.preventDefault();
    setErrore("");
    setDaConfermare(false);
    setAttesa(true);
    try {
      if (passo === "password") {
        const r = await authClient.signIn.email({ email: email.trim(), password });
        if (r.error?.code === CODICE_DA_CONFERMARE) {
          setDaConfermare(true);
          setAttesa(false);
          return;
        }
        if (r.error) {
          setErrore("Email o password non corrette.");
          setAttesa(false);
          return;
        }
        if ((r.data as { twoFactorRedirect?: boolean } | null)?.twoFactorRedirect) {
          setPasso("codice");
          setAttesa(false);
          return;
        }
        await concludi();
      } else {
        // Niente "fidati di questo dispositivo": la sessione non risulterebbe verificata con il secondo fattore.
        const r = recupero
          ? await authClient.twoFactor.verifyBackupCode({ code: codice.trim() })
          : await authClient.twoFactor.verifyTotp({ code: codice.trim(), trustDevice: false });
        if (r.error) {
          setErrore("Codice non valido. Riprova.");
          setAttesa(false);
          return;
        }
        await concludi();
      }
    } catch {
      setErrore("Non riesco a collegarmi al server. Controlla la rete e riprova.");
      setAttesa(false);
    }
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
          <h1 className="code text-[18px] font-bold uppercase tracking-wide text-ink">{passo === "password" ? "Accedi" : "Codice dal telefono"}</h1>
          {daConfermare && (
            <div role="alert" className="space-y-3">
              <Notice tone="warn">{MESSAGGIO_DA_CONFERMARE}</Notice>
              <RimandaEmail email={email} />
            </div>
          )}
          {errore && (
            <div role="alert">
              <Notice tone="danger">{errore}</Notice>
            </div>
          )}
          {passo === "password" ? (
            <>
              <Field label="Email">
                <input className="field" type="email" autoComplete="username" inputMode="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
              </Field>
              <Field label="Password">
                <input className="field" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
              </Field>
            </>
          ) : (
            <>
              <Field label={recupero ? "Codice di recupero" : "Codice a 6 cifre"} hint={recupero ? "Uno dei codici di recupero che hai salvato." : "Lo trovi nell'app di autenticazione sul tuo telefono."}>
                <input
                  className="field code tracking-[0.2em]"
                  type="text"
                  autoComplete="one-time-code"
                  inputMode={recupero ? "text" : "numeric"}
                  value={codice}
                  onChange={(e) => setCodice(e.target.value)}
                  required
                  autoFocus
                />
              </Field>
              <button
                type="button"
                onClick={() => {
                  setRecupero((v) => !v);
                  setCodice("");
                  setErrore("");
                }}
                className="text-[14px] font-semibold text-band underline"
              >
                {recupero ? "Uso il codice dal telefono" : "Ho perso il telefono: uso un codice di recupero"}
              </button>
            </>
          )}
          <Button type="submit" size="lg" className="w-full" disabled={attesa || (passo === "password" ? !email || !password : !codice)}>
            {attesa ? "Controllo…" : passo === "password" ? "Entra" : "Conferma"}
          </Button>
        </form>
        <div className="mt-4 text-center">
          <Link href="/registrati" className="inline-flex min-h-11 items-center px-2 text-[14px] font-semibold text-band underline">
            Non hai un account? Registrati gratis
          </Link>
        </div>
        <p className="flex justify-center gap-4 text-[13px] text-ink-3">
          <Link href="/privacy" target="_blank" className="inline-flex min-h-11 items-center underline">
            Privacy
          </Link>
          <Link href="/condizioni" target="_blank" className="inline-flex min-h-11 items-center underline">
            Condizioni
          </Link>
        </p>
        {onNomi && (
          <div className="mt-4 text-center">
            <button type="button" onClick={onNomi} className="min-h-11 px-2 text-[14px] font-semibold text-ink-3 underline">
              Torna all&apos;elenco dei nomi
            </button>
          </div>
        )}
      </div>
    </main>
  );
}
