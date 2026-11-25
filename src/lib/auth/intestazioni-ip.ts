// Da quale intestazione si prende l'indirizzo del cliente per i limiti (Better Auth e registrazione).
// Solo quella che il davanti riscrive a ogni richiesta, così il cliente non la può scegliere: su Vercel x-real-ip,
// altrimenti cf-connecting-ip di Cloudflare Tunnel (x-forwarded-for lo può scrivere chiunque). Vedi docs/ACCESSO.md.
type Variabili = Record<string, string | undefined>;

export function intestazioniIp(env: Variabili): string[] {
  return env.VERCEL === "1" ? ["x-real-ip"] : ["cf-connecting-ip"];
}

/** L'indirizzo del cliente dall'intestazione scelta, o null se manca (localhost, rete interna). */
export function ipCliente(h: Headers, env: Variabili = process.env): string | null {
  for (const nome of intestazioniIp(env)) {
    const v = h.get(nome)?.trim();
    if (v) return v;
  }
  return null;
}
