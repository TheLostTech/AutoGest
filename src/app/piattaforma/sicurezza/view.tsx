"use client";

// Codice dal telefono (TOTP) del super admin. Usa direttamente gli endpoint di Better Auth: serve poterlo
// attivare prima di averlo (il resto della piattaforma lo pretende). Nessun "ricorda questo dispositivo".
import { useState } from "react";
import QRCode from "qrcode";
import { ShieldCheck } from "lucide-react";
import { authClient } from "@/lib/auth/client";
import { Button, Field, Notice, PageTitle, Panel } from "@/components/ui";
import { usePiattaforma } from "../comune";

export default function Sicurezza() {
  const { stato, ricarica } = usePiattaforma();
  const [password, setPassword] = useState("");
  const [codice, setCodice] = useState("");
  const [qr, setQr] = useState<string | null>(null);
  const [chiave, setChiave] = useState("");
  const [riserva, setRiserva] = useState<string[] | null>(null);
  const [errore, setErrore] = useState("");
  const [attesa, setAttesa] = useState(false);
  const [attivato, setAttivato] = useState(false);

  async function avvia(ev: React.FormEvent) {
    ev.preventDefault();
    setErrore("");
    setAttesa(true);
    const r = await authClient.twoFactor.enable({ password }).catch(() => null);
    setAttesa(false);
    setPassword("");
    if (!r || r.error || !r.data || !("totpURI" in r.data)) {
      setErrore(r?.error?.message ?? "Non riesco ad avviare l'attivazione. Controlla la password.");
      return;
    }
    setQr(await QRCode.toDataURL(r.data.totpURI, { margin: 1, width: 224 }));
    setChiave(new URL(r.data.totpURI).searchParams.get("secret") ?? "");
    setRiserva(r.data.backupCodes);
  }

  async function conferma(ev: React.FormEvent) {
    ev.preventDefault();
    setErrore("");
    setAttesa(true);
    // Niente trustDevice: il codice si chiede a ogni accesso
    const r = await authClient.twoFactor.verifyTotp({ code: codice.trim() }).catch(() => null);
    setAttesa(false);
    if (!r || r.error) {
      setErrore("Il codice non è corretto. Controlla l'ora del telefono e riprova.");
      return;
    }
    setQr(null);
    setChiave("");
    setCodice("");
    setAttivato(true);
    await ricarica();
  }

  const attivo = stato.dueFattoriAttivo;

  return (
    <div className="mx-auto max-w-xl">
      <PageTitle title="Sicurezza" sub="Il codice dal telefono protegge l'ingresso nelle aziende. Senza, la piattaforma resta chiusa." />
      {errore && (
        <div role="alert" className="mb-4">
          <Notice tone="danger">{errore}</Notice>
        </div>
      )}

      {attivo && !qr && (
        <div className="space-y-4">
          <Notice tone="ok">
            <span className="inline-flex items-center gap-2">
              <ShieldCheck className="size-5" aria-hidden /> Il codice dal telefono è attivo.
            </span>
          </Notice>
          {!stato.dueFattoriVerificato && <Notice tone="warn">Questa sessione non l&apos;ha ancora usato: esci e accedi di nuovo inserendo il codice.</Notice>}
        </div>
      )}

      {attivato && riserva && (
        <div className="mt-4">
          <CodiciRiserva codici={riserva} onChiudi={() => setRiserva(null)} />
        </div>
      )}

      {!attivo && !qr && (
        <form onSubmit={avvia} className="space-y-4 rounded-md border border-hair bg-label p-4">
          <p className="text-ink-2">Attivalo con un&apos;app per i codici sul telefono (per esempio Google Authenticator). Per cominciare conferma la tua password.</p>
          <Field label="Password">
            <input className="field" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
          </Field>
          <Button type="submit" disabled={attesa || !password}>
            {attesa ? "Un attimo…" : "Attiva il codice dal telefono"}
          </Button>
        </form>
      )}

      {qr && (
        <Panel title="Attiva il codice">
          <div className="space-y-5 p-4">
            <ol className="list-decimal space-y-1 pl-5 text-ink-2">
              <li>Apri l&apos;app dei codici sul telefono e aggiungi un account con il QR qui sotto.</li>
              <li>Scrivi qui il codice a 6 cifre che mostra.</li>
            </ol>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={qr} alt="QR per l'app dei codici" width={224} height={224} className="rounded-md border border-hair bg-white" />
            {chiave && (
              <p className="text-sm text-ink-2">
                Senza fotocamera, scrivi questa chiave nell&apos;app: <b className="code select-all text-ink">{chiave}</b>
              </p>
            )}
            {riserva && <CodiciRiserva codici={riserva} />}
            <form onSubmit={conferma} className="space-y-3">
              <Field label="Codice a 6 cifre">
                <input className="field max-w-48" inputMode="numeric" pattern="[0-9]{6}" maxLength={6} value={codice} onChange={(e) => setCodice(e.target.value.replace(/\D/g, ""))} autoComplete="one-time-code" required />
              </Field>
              <Button type="submit" disabled={attesa || codice.length !== 6}>
                {attesa ? "Controllo…" : "Conferma e attiva"}
              </Button>
            </form>
          </div>
        </Panel>
      )}
    </div>
  );
}

function CodiciRiserva({ codici, onChiudi }: { codici: string[]; onChiudi?: () => void }) {
  return (
    <div className="rounded-md border border-hair bg-label p-4">
      <h2 className="text-[17px] font-bold text-ink">Codici di riserva</h2>
      <p className="mb-3 text-sm text-ink-2">Se perdi il telefono, ogni codice vale una volta sola. Scrivili e conservali al sicuro: non verranno mostrati di nuovo.</p>
      <ul className="code grid grid-cols-2 gap-x-6 gap-y-1 text-[17px] text-ink">
        {codici.map((c) => (
          <li key={c}>{c}</li>
        ))}
      </ul>
      {onChiudi && (
        <div className="mt-3">
          <Button size="sm" variant="secondary" onClick={onChiudi}>
            Li ho salvati
          </Button>
        </div>
      )}
    </div>
  );
}
