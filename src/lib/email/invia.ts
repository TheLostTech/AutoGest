export type Email = { a: string; oggetto: string; testo: string; html: string };

// Invia con Resend (fetch, niente SDK). Senza chiave: in locale scrive il testo nel log del server (serve alle prove),
// in produzione si ferma. Con la chiave serve anche il mittente (EMAIL_MITTENTE). La chiave e il contenuto dell'email
// non finiscono mai nei log: di un rifiuto di Resend si scrivono solo lo stato e il tipo d'errore.
export async function inviaEmail(e: Email): Promise<void> {
  const chiave = process.env.RESEND_API_KEY;
  if (!chiave) {
    if (process.env.NODE_ENV === "production") throw new Error("Invio email non configurato");
    console.log(`[email] a ${e.a}: ${e.oggetto}\n${e.testo}`);
    return;
  }
  const mittente = process.env.EMAIL_MITTENTE?.trim();
  if (!mittente) throw new Error("Invio email non configurato");
  const risposta = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${chiave}`, "Content-Type": "application/json" },
    body: JSON.stringify({ from: mittente, to: [e.a], subject: e.oggetto, text: e.testo, html: e.html }),
    signal: AbortSignal.timeout(10_000),
  });
  if (!risposta.ok) {
    const tipo = await risposta
      .json()
      .then((j: unknown) => (j && typeof j === "object" && typeof (j as { name?: unknown }).name === "string" ? (j as { name: string }).name : ""))
      .catch(() => "");
    console.error(`[email] Resend ${risposta.status}${tipo ? ` ${tipo.slice(0, 60)}` : ""}`);
    throw new Error("Email non inviata");
  }
}
