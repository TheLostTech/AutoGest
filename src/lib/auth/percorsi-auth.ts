// Endpoint di Better Auth raggiungibili dal browser: solo quelli che l'app chiama (authClient in accesso, Piattaforma,
// Sicurezza, Dispositivi). Puro. Ogni nuovo uso di authClient va aggiunto qui, altrimenti risponde 404.
const BASE = "/api/auth";

const PERMESSI: Record<string, "GET" | "POST"> = {
  "/ok": "GET",
  "/get-session": "GET",
  "/sign-in/email": "POST",
  "/sign-out": "POST",
  "/organization/list": "GET",
  "/organization/set-active": "POST",
  "/two-factor/enable": "POST",
  "/two-factor/verify-totp": "POST",
  "/two-factor/verify-backup-code": "POST",
  "/pin-dispositivo/nomi": "GET",
  "/pin-dispositivo/elenco": "GET",
  "/pin-dispositivo/entra": "POST",
  "/pin-dispositivo/registra": "POST",
  "/pin-dispositivo/revoca": "POST",
  "/pin-dispositivo/sblocca": "POST",
};

export function percorsoAuthPermesso(metodo: string, pathname: string): boolean {
  // Better Auth confronta i percorsi senza badare a maiuscole e barre finali: qui si fa lo stesso, poi elenco esatto
  const p = pathname.replace(/\/+$/, "").toLowerCase();
  if (!p.startsWith(BASE + "/")) return false;
  const resto = p.slice(BASE.length);
  return PERMESSI[resto] === metodo.toUpperCase();
}
