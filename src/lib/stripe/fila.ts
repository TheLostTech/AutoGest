// Coda per chiave (un'azienda): un lavoro per volta, e chi arriva mentre un lavoro aspetta in coda
// riusa quello invece di metterne un altro. Un lavoro già partito non si riusa: chi arriva dopo vuole una lettura nuova.
// Senza Stripe né disco: si prova con i test.

export type Fila<T> = {
  metti(chiave: string, lavoro: () => Promise<T>): Promise<T>;
  /** Il lavoro in coda e non ancora partito per la chiave, se c'è. */
  inAttesa(chiave: string): Promise<T> | null;
};

export function creaFila<T>(): Fila<T> {
  const code = new Map<string, { coda: Promise<unknown>; inAttesa: Promise<T> | null }>();
  return {
    inAttesa: (chiave) => code.get(chiave)?.inAttesa ?? null,
    metti(chiave, lavoro) {
      const davanti = code.get(chiave);
      if (davanti?.inAttesa) return davanti.inAttesa;
      const f = davanti ?? { coda: Promise.resolve(), inAttesa: null };
      const run: Promise<T> = f.coda.then(() => {
        // Partito: da qui in poi chi arriva mette un lavoro nuovo
        if (f.inAttesa === run) f.inAttesa = null;
        return lavoro();
      });
      // In attesa solo se c'è un lavoro davanti; senza, parte subito
      f.inAttesa = davanti ? run : null;
      const coda = run.catch(() => undefined);
      f.coda = coda;
      code.set(chiave, f);
      void coda.then(() => {
        if (code.get(chiave)?.coda === coda) code.delete(chiave);
      });
      return run;
    },
  };
}
