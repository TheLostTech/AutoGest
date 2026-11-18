// Code per chiave (di solito l'id dell'azienda): le operazioni con la stessa chiave vanno una dopo l'altra,
// quelle con chiavi diverse non si aspettano. Le code stanno sulla globalThis, con un nome per ogni uso: le route di
// Next possono avere ognuna la propria copia di un modulo, ma la coda di un file deve essere una sola per processo.
// Un solo processo Node (come il resto del prototipo).
const g = globalThis as typeof globalThis & { __gestionaleFile?: Map<string, Map<string, Promise<unknown>>> };
const tutte = (g.__gestionaleFile ??= new Map());

export function inFilaPer<T>(nome: string, chiave: string, fn: () => Promise<T>): Promise<T> {
  let code = tutte.get(nome);
  if (!code) tutte.set(nome, (code = new Map()));
  const mappa = code;
  const run = (mappa.get(chiave) ?? Promise.resolve()).then(fn);
  const coda = run.catch(() => undefined);
  mappa.set(chiave, coda);
  void coda.then(() => {
    if (mappa.get(chiave) === coda) mappa.delete(chiave);
  });
  return run;
}
