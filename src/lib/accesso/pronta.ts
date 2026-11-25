// "Piattaforma non pronta": se l'avvio (tabelle, azienda demo, super admin) fallisce, il server resta acceso
// ma le API della gestione, della piattaforma e del negozio rispondono 503 con un messaggio chiaro. Solo server.
// Su Vercel la stessa istanza resta accesa a lungo: l'avvio si riprova da qui, alla prima richiesta che trova la
// piattaforma non pronta, al massimo una volta ogni 30 secondi per istanza e un solo tentativo per volta (le richieste
// che arrivano insieme aspettano lo stesso). Riuscito il tentativo, la richiesta prosegue e il 503 non c'è più.
// Un tentativo che dura più di 60 secondi (per esempio un'istruzione in attesa di un lock) conta come fallito: le
// richieste in attesa ricevono il 503 e il tentativo dopo segue la regola dei 30 secondi. L'avvio appeso non si
// interrompe (non si può): se poi finisce, vale per quello che è (riuscito: pronta; fallito: conta solo se è l'ultimo).

export const RIPROVA_AVVIO_MS = 30_000;
export const TEMPO_MASSIMO_AVVIO_MS = 60_000;

/** Avvia un timer e restituisce come annullarlo (iniettabile nei test). */
export type Timer = (fn: () => void, ms: number) => () => void;
const timerVero: Timer = (fn, ms) => {
  const t = setTimeout(fn, ms);
  return () => clearTimeout(t);
};

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
  massimoMs = TEMPO_MASSIMO_AVVIO_MS,
  timer: Timer = timerVero,
): Promise<boolean> {
  if (!s.nonPronta) return Promise.resolve(true);
  if (s.inCorso) return s.inCorso;
  if (ora() - s.ultimoTentativo < intervalloMs) return Promise.resolve(false);
  s.ultimoTentativo = ora();
  // Promise.resolve().then: anche un `avvia` che lancia subito passa di qui in modo asincrono, dopo che inCorso è segnato
  let annullaTimer: () => void = () => {};
  const scaduto = new Promise<boolean>((risolvi) => {
    annullaTimer = timer(() => {
      console.error(`[avvio] il tentativo di avvio dura più di ${Math.round(massimoMs / 1000)} secondi: conta come fallito.`);
      risolvi(false);
    }, massimoMs);
  });
  const avvio = Promise.resolve()
    .then(avvia)
    .then(
      (ok) => ok === true,
      (e) => {
        console.error("[avvio] nuovo tentativo di avvio non riuscito:", e);
        return false;
      },
    );
  const tentativo = Promise.race([avvio, scaduto])
    .then((ok) => {
      annullaTimer();
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

// Numero dell'ultimo avvio partito: un avvio appeso che finisce tardi, dopo che ne è partito un altro, non deve
// rimettere "non pronta" una piattaforma che nel frattempo è pronta (o che l'altro avvio sta già riprovando).
const gen = globalThis as typeof globalThis & { __numeroAvvio?: number };
export const nuovoAvvio = (): number => (gen.__numeroAvvio = (gen.__numeroAvvio ?? 0) + 1);
export const eUltimoAvvio = (n: number): boolean => gen.__numeroAvvio === n;

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
