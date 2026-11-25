"use client";

import { useState } from "react";
import { authClient } from "@/lib/auth/client";
import { esitoRimando, type Avviso } from "@/lib/accesso/conferma";
import { Button, Notice } from "@/components/ui";

// "Rimanda l'email" di conferma (pagina di accesso e registrazione). Better Auth risponde allo stesso modo per ogni
// email e manda il link solo al titolare in attesa; il limite sulle richieste è il suo (3 al minuto per indirizzo).
export function RimandaEmail({ email }: { email: string }) {
  const [attesa, setAttesa] = useState(false);
  const [esito, setEsito] = useState<Avviso | null>(null);

  async function rimanda() {
    setAttesa(true);
    setEsito(null);
    let stato = 0;
    try {
      const r = await authClient.sendVerificationEmail({ email: email.trim().toLowerCase() });
      stato = r.error ? r.error.status || 500 : 200;
    } catch {
      stato = 0;
    }
    setEsito(esitoRimando(stato));
    setAttesa(false);
  }

  return (
    <div className="space-y-3">
      <Button type="button" variant="secondary" className="w-full" onClick={() => void rimanda()} disabled={attesa || !email.trim()}>
        {attesa ? "Invio…" : "Rimanda l'email"}
      </Button>
      {esito && (
        <div role="status">
          <Notice tone={esito.tono}>{esito.testo}</Notice>
        </div>
      )}
    </div>
  );
}
