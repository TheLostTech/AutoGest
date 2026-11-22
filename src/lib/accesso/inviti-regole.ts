// Regole pure dei codici invito (nessun accesso al database).

export const INVITO_MS = 30 * 86_400_000;
export const ALFABETO_INVITO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
export const LUNGHEZZA_INVITO = 12;

/** Maiuscole, senza spazi e trattini → "XXXX-XXXX-XXXX"; lunghezza o caratteri sbagliati → null. */
export function formatoCodice(s: string): string | null {
  const n = String(s).toUpperCase().replace(/[\s-]/g, "");
  if (n.length !== LUNGHEZZA_INVITO) return null;
  for (const ch of n) if (!ALFABETO_INVITO.includes(ch)) return null;
  return `${n.slice(0, 4)}-${n.slice(4, 8)}-${n.slice(8)}`;
}

export function invitoValido(i: { scade: number; usato?: number | null } | null, ora: number): boolean {
  return !!i && i.scade > ora && i.usato == null;
}
