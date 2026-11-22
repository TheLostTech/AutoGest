// Richiesta scritta dell'azienda (PDF o foto) allegata quando il super admin crea un utente o ne cambia i ruoli.
export const RICHIESTA_MAX_BYTE = 10_485_760;

export type TipoRichiesta = "pdf" | "jpeg" | "png";

// Il tipo si legge dalla firma del file (i primi byte), mai dall'estensione o dal tipo dichiarato dal browser.
export function tipoRichiesta(primiByte: Uint8Array): TipoRichiesta | null {
  const b = primiByte;
  if (b.length >= 4 && b[0] === 0x25 && b[1] === 0x50 && b[2] === 0x44 && b[3] === 0x46) return "pdf";
  if (b.length >= 3 && b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return "jpeg";
  if (b.length >= 4 && b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47) return "png";
  return null;
}

export const RICHIESTA_CONTENT_TYPE: Record<TipoRichiesta, string> = { pdf: "application/pdf", jpeg: "image/jpeg", png: "image/png" };
export const RICHIESTA_ESTENSIONE: Record<TipoRichiesta, string> = { pdf: "pdf", jpeg: "jpg", png: "png" };

export type AzioneUtente = "crea" | "ruoli" | "pin" | "password" | "disattiva";

// Obbligatoria per creare un utente e per cambiarne i ruoli; per il resto è facoltativa.
export function richiestaObbligatoria(azione: AzioneUtente): boolean {
  return azione === "crea" || azione === "ruoli";
}
