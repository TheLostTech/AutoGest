// "Piattaforma non pronta": se l'avvio (tabelle, azienda demo, super admin) fallisce, il server resta acceso
// ma le API della gestione, della piattaforma e del negozio rispondono 503 con un messaggio chiaro. Solo server.
const g = globalThis as typeof globalThis & { __piattaformaNonPronta?: boolean };

export const segnaPiattaformaNonPronta = (v: boolean) => {
  g.__piattaformaNonPronta = v;
};

/** Risposta 503 se l'avvio non è riuscito, altrimenti null. */
export function rispostaNonPronta(): Response | null {
  if (!g.__piattaformaNonPronta) return null;
  return Response.json(
    { error: "Il gestionale non è pronto: l'avvio non è riuscito. Controlla il registro del server e riavvia.", motivo: "non-pronta" },
    { status: 503, headers: { "Cache-Control": "no-store" } },
  );
}
