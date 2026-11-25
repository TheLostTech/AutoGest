// Limite di dimensione di foto e allegati: lo stesso per tutte le route che ricevono file dal gestionale.
export const MAX_FILE_BYTES = 3 * 1024 * 1024;

export function controllaDimensione(bytes: number): { ok: true } | { ok: false; messaggio: string } {
  if (bytes === 0) return { ok: false, messaggio: "File vuoto." };
  if (bytes > MAX_FILE_BYTES) return { ok: false, messaggio: "File più grande di 3 MB: riducilo e riprova." };
  return { ok: true };
}
