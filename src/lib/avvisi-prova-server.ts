// Giro giornaliero degli avvisi di fine prova. Solo server (lo chiama la route pianificata).
import type { AuthContext } from "better-auth";
import { ruoliDaStringa } from "@/lib/accesso/ruoli";
import { aggiornaAbbonamento, leggiAbbonamento } from "@/lib/abbonamento-server";
import { avvisoDaMandare, giorniAllaFine, type Avviso } from "@/lib/avvisi-prova";
import { indirizzoPubblico } from "@/lib/email/indirizzo";
import { inviaEmail } from "@/lib/email/invia";
import { emailProvaFinita, emailProvaInScadenza } from "@/lib/email/modelli";

export type EsitoGiro = { aziende: number; mandati: number; saltati: number; errori: number };

const registrata = (metadata: unknown): boolean => {
  try {
    const m = typeof metadata === "string" ? JSON.parse(metadata) : metadata;
    return typeof m === "object" && m !== null && (m as { registrata?: unknown }).registrata === true;
  } catch {
    return false;
  }
};

async function titolare(c: AuthContext, aziendaId: string): Promise<{ email: string; nome: string } | null> {
  const membri = await c.adapter.findMany<{ userId: string; role: string }>({ model: "member", where: [{ field: "organizationId", value: aziendaId }] });
  for (const m of membri) {
    if (!ruoliDaStringa(m.role).includes("responsabile")) continue;
    const u = await c.internalAdapter.findUserById(m.userId).catch(() => null);
    if (u?.email) return { email: u.email, nome: u.name || "" };
  }
  return null;
}

/**
 * Scorre le aziende registrate e manda a ogni titolare l'avviso che gli spetta. L'avviso si segna nell'abbonamento
 * (dentro l'aggiornamento atomico, rivalutando la regola sul documento più recente) PRIMA di inviare: due esecuzioni
 * insieme non mandano due email. Se l'invio fallisce il segno resta: meglio un avviso perso che email ripetute ogni giorno.
 * Il risultato sono solo numeri: né indirizzi né nomi escono da qui.
 */
export async function mandaAvvisiProva(c: AuthContext, ora: number): Promise<EsitoGiro> {
  const esito: EsitoGiro = { aziende: 0, mandati: 0, saltati: 0, errori: 0 };
  const base = indirizzoPubblico();
  // Senza indirizzo assoluto il link dell'email non esiste: ci si ferma prima di segnare qualunque avviso
  if (!base) throw new Error("Indirizzo pubblico non configurato");
  const link = `${base}/impostazioni/abbonamento`;
  const aziende = await c.adapter.findMany<{ id: string; metadata?: unknown }>({ model: "organization" });
  for (const org of aziende) {
    if (!registrata(org.metadata)) continue;
    esito.aziende++;
    try {
      const letto = await leggiAbbonamento(org.id);
      if (!letto || !avvisoDaMandare(letto, ora)) { esito.saltati++; continue; }
      const dest = await titolare(c, org.id);
      if (!dest) { esito.saltati++; continue; }
      // Segno prima dell'invio, sul documento più recente
      let avviso: Avviso | null = null;
      let giorni = 0;
      await aggiornaAbbonamento(org.id, (prima) => {
        if (!prima) throw new Error("Abbonamento assente");
        avviso = avvisoDaMandare(prima, ora);
        if (!avviso) return prima;
        giorni = giorniAllaFine(prima, ora) ?? 0;
        return { ...prima, avvisi: { ...prima.avvisi, [avviso]: new Date(ora).toISOString() } };
      });
      if (!avviso) { esito.saltati++; continue; }
      const nome = dest.nome || dest.email.split("@")[0];
      const email = avviso === "scadenza" ? emailProvaInScadenza(nome, Math.max(1, giorni), link) : emailProvaFinita(nome, link);
      try {
        await inviaEmail({ ...email, a: dest.email });
        esito.mandati++;
      } catch {
        // Niente indirizzo né testo nel log: solo l'azienda e il tipo di avviso
        console.error("Avviso di fine prova non inviato", org.id, avviso);
        esito.errori++;
      }
    } catch (e) {
      console.error("Avvisi di fine prova: azienda saltata", org.id, e instanceof Error ? e.message : "errore");
      esito.errori++;
    }
  }
  return esito;
}
