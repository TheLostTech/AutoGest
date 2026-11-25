// "Piattaforma non pronta": se l'avvio (tabelle, azienda demo, super admin) fallisce, il server resta acceso
// ma le API della gestione, della piattaforma e del negozio rispondono 503 con un messaggio chiaro. Solo server.
// Su Vercel la stessa istanza resta accesa a lungo: l'avvio si riprova da qui, alla prima richiesta che trova la
// piattaforma non pronta, al massimo una volta ogni 30 secondi per istanza e un solo tentativo per volta (le richieste
// che arrivano insieme aspettano lo stesso). Riuscito il tentativo, la richiesta prosegue e il 503 non c'è più.

export const RIPROVA_AVVIO_MS = 30_000;

export interface StatoAvvio {
  nonPronta: boolean;
  /** Quando è finito (o partito) l'ultimo tentativo di avvio, in ms */
  ultimoTentativo: number;
  inCorso: Promise<boolean> | null;
}

/**
 * Riprova l'avvio se la piattaforma non è pronta. true se è pronta (subito o dopo il tentativo), false se non lo è
 * ancora: tentativo fallito, oppure l'ultimo è di meno di `intervalloMs` fa. Le chiamate durante un tentativo lo
 * aspettano, senza farne partire un altro. `avvia` dice se l'avvio è riuscito; se lancia vale come non riuscito.
 */
export function riprovaAvvio(
  s: StatoAvvio,
  avvia: () => Promise<boolean>,
  ora: () => number,
  intervalloMs = RIPROVA_AVVIO_MS,
): Promise<boolean> {
  if (!s.nonPronta) return Promise.resolve(true);
  if (s.inCorso) return s.inCorso;
  if (ora() - s.ultimoTentativo < intervalloMs) return Promise.resolve(false);
  s.ultimoTentativo = ora();
  // Promise.resolve().then: anche un `avvia` che lancia subito passa di qui in modo asincrono, dopo che inCorso è segnato
  const tentativo = Promise.resolve()
    .then(avvia)
    .then(
      (ok) => ok === true,
      (e) => {
        console.error("[avvio] nuovo tentativo di avvio non riuscito:", e);
        return false;
      },
    )
    .then((ok) => {
      s.nonPronta = !ok;
      // L'attesa di 30 secondi conta dalla fine del tentativo: un avvio lento non ne fa partire subito un altro
      s.ultimoTentativo = ora();
      s.inCorso = null;
      return ok;
    });
  s.inCorso = tentativo;
  return tentativo;
}

const g = globalThis as typeof globalThis & { __statoAvvio?: StatoAvvio };
const stato = (): StatoAvvio => (g.__statoAvvio ??= { nonPronta: false, ultimoTentativo: 0, inCorso: null });

export const segnaPiattaformaNonPronta = (v: boolean) => {
  const s = stato();
  s.nonPronta = v;
  if (v) s.ultimoTentativo = Date.now();
};

// Import dinamico: avvio.ts importa questo file
const avviaDiNuovo = async () => (await import("./avvio")).avviaPiattaforma();

/** Risposta 503 se l'avvio non è riuscito (e il nuovo tentativo, se è il momento di farlo, nemmeno), altrimenti null. */
export async function rispostaNonPronta(): Promise<Response | null> {
  if (await riprovaAvvio(stato(), avviaDiNuovo, Date.now)) return null;
  return Response.json(
    { error: "Il gestionale non è pronto: l'avvio non è riuscito. Controlla il registro del server e riavvia.", motivo: "non-pronta" },
    { status: 503, headers: { "Cache-Control": "no-store" } },
  );
}
