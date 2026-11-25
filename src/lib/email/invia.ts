export type Email = { a: string; oggetto: string; testo: string; html: string };

// Invia con Resend (fetch, niente SDK). Senza chiave: in locale scrive il testo nel log del server (serve alle prove),
// in produzione si ferma. La chiave non finisce mai nei log.
export async function inviaEmail(e: Email): Promise<void> {
  const chiave = process.env.RESEND_API_KEY;
  if (!chiave) {
    if (process.env.NODE_ENV === "production") throw new Error("Invio email non configurato");
    console.log(`[email] a ${e.a}: ${e.oggetto}\n${e.testo}`);
    return;
  }
  const risposta = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${chiave}`, "Content-Type": "application/json" },
    body: JSON.stringify({ from: process.env.EMAIL_MITTENTE, to: [e.a], subject: e.oggetto, text: e.testo, html: e.html }),
  });
  if (!risposta.ok) {
    const dettaglio = await risposta.text().catch(() => "");
    console.error(`[email] Resend ${risposta.status}: ${dettaglio.slice(0, 300)}`);
    throw new Error("Email non inviata");
  }
}
