// Stato di un'azienda nuova: tutte le liste condivise vuote, contatori a zero.
export function statoVuoto(base: { listini: unknown[]; warehouses: unknown[] }): Record<string, unknown> {
  return {
    vehicles: [],
    parts: [],
    annunci: [],
    orders: [],
    audit: [],
    rules: [],
    wasteMoves: [],
    firs: [],
    soggetti: [],
    docs: [],
    inventory: [],
    listini: base.listini,
    warehouses: base.warehouses,
    counters: {
      vehicle: 0,
      part: 0,
      order: 0,
      event: 0,
      move: 0,
      fir: 0,
      docs: { P: 0, DC: 0, FT: 0, NC: 0 },
      inventory: 0,
      annuncio: 0,
    },
  };
}
