// Indirizzo da scrivere nei QR stampati: deve aprirsi dal telefono di chiunque in azienda.
// 1) INDIRIZZO_GESTIONALE, se impostato sul server (es. https://gestionale.azienda.it): vince sempre.
// 2) Altrimenti l'indirizzo di rete del server (es. 192.168.1.58), usato quando si stampa dal server stesso
//    aperto come "localhost", che dal telefono non porterebbe da nessuna parte.
import os from "node:os";
import { connection } from "next/server";

function lanAddress() {
  for (const list of Object.values(os.networkInterfaces())) {
    for (const a of list ?? []) if (a.family === "IPv4" && !a.internal && !a.address.startsWith("169.254.")) return a.address;
  }
  return undefined;
}

export async function GET() {
  await connection();
  const fisso = process.env.INDIRIZZO_GESTIONALE?.trim().replace(/\/+$/, "") || undefined;
  return Response.json({ fisso, lan: lanAddress() }, { headers: { "Cache-Control": "no-store" } });
}
