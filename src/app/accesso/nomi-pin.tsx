"use client";

import { useRef, useState } from "react";
import { Delete, Lock } from "lucide-react";
import { authClient } from "@/lib/auth/client";
import type { NomiDispositivo } from "@/lib/auth/pin-dispositivo-client";
import { Notice } from "@/components/ui";

// Tablet del piazzale: si tocca il proprio nome, poi le 4 cifre del PIN. Bersagli grandi, usabili coi guanti.
export function NomiPin({ dati, da, onEmail, onAggiorna }: { dati: NomiDispositivo; da: string; onEmail: () => void; onAggiorna: () => void }) {
  const [scelto, setScelto] = useState<{ userId: string; nome: string } | null>(null);
  const [pin, setPin] = useState("");
  const [errore, setErrore] = useState("");
  const [attesa, setAttesa] = useState(false);

  async function invia(codice: string) {
    if (!scelto) return;
    setAttesa(true);
    setErrore("");
    try {
      const r = await authClient.pinDispositivo.entra({ userId: scelto.userId, pin: codice });
      if (r.error) {
        aggiorna("");
        setAttesa(false);
        setErrore(r.error.message ?? "PIN non corretto.");
        // Nome o dispositivo appena bloccati: l'elenco va riletto
        if (r.error.status === 403) {
          setScelto(null);
          onAggiorna();
        }
        return;
      }
      window.location.assign(da);
    } catch {
      aggiorna("");
      setAttesa(false);
      setErrore("Non riesco a collegarmi al server. Controlla la rete e riprova.");
    }
  }

  // Tocchi rapidi arrivano prima del nuovo disegno: le cifre si accumulano in un ref, non nello stato del disegno
  const cifre = useRef("");
  const inInvio = useRef(false);
  function aggiorna(p: string) {
    cifre.current = p;
    setPin(p);
  }
  function cifra(c: string) {
    if (inInvio.current || cifre.current.length >= 4) return;
    aggiorna(cifre.current + c);
    setErrore("");
    if (cifre.current.length === 4) {
      inInvio.current = true;
      void invia(cifre.current).finally(() => {
        inInvio.current = false;
      });
    }
  }

  return (
    <div className="w-full max-w-xl">
      <div className="mb-5 text-center">
        <p className="code text-[22px] font-bold uppercase leading-tight tracking-wide text-band">{dati.azienda}</p>
        <p className="mt-1 text-[14px] font-medium text-ink-3">{dati.dispositivo}</p>
      </div>

      <div className="label-sheet space-y-4 p-5">
        {dati.bloccato ? (
          <div role="alert">
            <Notice tone="danger">
              <b>Dispositivo bloccato</b> per troppi PIN sbagliati. Il responsabile lo sblocca da Impostazioni → Dispositivi, entrando con email e password.
            </Notice>
          </div>
        ) : !scelto ? (
          <>
            <h1 className="code text-[18px] font-bold uppercase tracking-wide text-ink">Chi sei?</h1>
            {errore && (
              <div role="alert">
                <Notice tone="danger">{errore}</Notice>
              </div>
            )}
            {dati.nomi.length === 0 ? (
              <Notice tone="info">Nessun utente con PIN in questa azienda. Il responsabile può accedere con email.</Notice>
            ) : (
              <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {dati.nomi.map((n) => (
                  <li key={n.userId}>
                    <button
                      type="button"
                      disabled={n.bloccato}
                      onClick={() => {
                        setScelto(n);
                        aggiorna("");
                        setErrore("");
                      }}
                      className="flex min-h-20 w-full flex-col items-center justify-center gap-1 rounded-md border border-hair bg-label px-3 text-center text-[18px] font-semibold text-ink transition-colors hover:border-band active:bg-band-tint disabled:cursor-not-allowed disabled:bg-carton disabled:text-ink-3"
                    >
                      <span className="break-words">{n.nome}</span>
                      {n.bloccato && (
                        <span className="flex items-center gap-1 text-[13px] font-semibold text-danger">
                          <Lock className="size-3.5" aria-hidden /> Bloccato
                        </span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </>
        ) : (
          <>
            <div className="flex items-baseline justify-between gap-3">
              <h1 className="code text-[18px] font-bold uppercase tracking-wide text-ink">{scelto.nome}</h1>
              <button
                type="button"
                onClick={() => {
                  setScelto(null);
                  aggiorna("");
                  setErrore("");
                }}
                className="min-h-11 px-2 text-[15px] font-semibold text-band underline"
              >
                Non sono io
              </button>
            </div>
            <p className="text-[15px] text-ink-2">Scrivi il tuo PIN di 4 cifre.</p>
            <div className="flex justify-center gap-3" aria-label={`${pin.length} cifre su 4`} role="status">
              {[0, 1, 2, 3].map((i) => (
                <span key={i} className={`size-5 rounded-full border-2 ${i < pin.length ? "border-band bg-band" : "border-hair"}`} />
              ))}
            </div>
            {errore && (
              <div role="alert">
                <Notice tone="danger">{errore}</Notice>
              </div>
            )}
            <div className="mx-auto grid max-w-xs grid-cols-3 gap-3">
              {["1", "2", "3", "4", "5", "6", "7", "8", "9"].map((c) => (
                <TastoPin key={c} onClick={() => cifra(c)} disabled={attesa}>
                  {c}
                </TastoPin>
              ))}
              <TastoPin onClick={() => aggiorna("")} disabled={attesa || !pin} piccolo>
                Cancella
              </TastoPin>
              <TastoPin onClick={() => cifra("0")} disabled={attesa}>
                0
              </TastoPin>
              <TastoPin onClick={() => aggiorna(cifre.current.slice(0, -1))} disabled={attesa || !pin} piccolo etichetta="Togli l'ultima cifra">
                <Delete className="size-7" aria-hidden />
              </TastoPin>
            </div>
            {attesa && <p className="text-center text-[15px] font-semibold text-ink-2">Controllo…</p>}
          </>
        )}
      </div>

      <div className="mt-4 text-center">
        <button type="button" onClick={onEmail} className="min-h-11 px-2 text-[14px] font-semibold text-ink-3 underline">
          Accedi con email
        </button>
      </div>
    </div>
  );
}

function TastoPin({ children, onClick, disabled, piccolo, etichetta }: { children: React.ReactNode; onClick: () => void; disabled?: boolean; piccolo?: boolean; etichetta?: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={etichetta}
      className={`code grid min-h-18 place-items-center rounded-md border border-hair bg-label font-bold text-ink transition-colors active:bg-band-tint disabled:text-ink-3 ${piccolo ? "text-[15px]" : "text-[30px]"}`}
    >
      {children}
    </button>
  );
}
