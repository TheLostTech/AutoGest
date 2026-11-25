// Registrazione del titolare su invito: crea l'azienda, l'archivio vuoto, il titolare e l'abbonamento "nuovo".
// Pubblica (senza sessione): l'accesso lo fa poi la pagina, come /accesso. Spec registrazione-pagamento, sezione 1.
import { ABBONAMENTO_NUOVO } from "@/lib/abbonamento";
import { aggiornaAbbonamento } from "@/lib/abbonamento-server";
import { rispostaNonPronta } from "@/lib/accesso/pronta";
import { registrazioneConsentita, validaRegistrazione } from "@/lib/accesso/registrazione";
import { ipCliente } from "@/lib/auth/intestazioni-ip";
import { aggiungiEventi, creaStatoAzienda } from "@/lib/archivio-azienda";
import { creaAzienda, creaMembro, slugDa } from "@/lib/piattaforma/crea";
import { usaInvito, verificaInvito } from "@/lib/piattaforma/inviti";
import { contesto, daAltroSito, errore, leggiJson, ok, type Contesto } from "@/lib/piattaforma/server";
import { DEFAULT_LISTINI } from "@/lib/pricing";
import { modalitaStripe } from "@/lib/stripe/server";
import { deposito } from "@/lib/deposito";
import { statoVuoto } from "@/lib/stato-iniziale";
import { WAREHOUSES } from "@/lib/warehouse";

const INVITO_NON_VALIDO = "Codice invito non valido";
const EMAIL_USATA = "Non è stato possibile registrarti con questa email. Se hai già un account, accedi.";

// Toglie quello che la registrazione aveva creato. Un guasto qui finisce nel log, mai nella risposta.
async function annulla(c: Contesto, aziendaId: string, userId: string | null) {
  const passi: [string, () => Promise<unknown>][] = [
    ["membri", () => c.adapter.deleteMany({ model: "member", where: [{ field: "organizationId", value: aziendaId }] })],
    ...(userId
      ? ([
          ["sessioni", () => c.adapter.deleteMany({ model: "session", where: [{ field: "userId", value: userId }] })],
          ["account", () => c.adapter.deleteMany({ model: "account", where: [{ field: "userId", value: userId }] })],
          ["utente", () => c.adapter.delete({ model: "user", where: [{ field: "id", value: userId }] })],
        ] as [string, () => Promise<unknown>][])
      : []),
    ["azienda", () => c.adapter.delete({ model: "organization", where: [{ field: "id", value: aziendaId }] })],
    ["cartella", () => deposito().togliAzienda(aziendaId)],
  ];
  for (const [nome, passo] of passi) {
    try {
      await passo();
    } catch (e) {
      console.error("Registrazione annullata a metà: non tolto", nome, aziendaId, e);
    }
  }
}

export async function POST(req: Request) {
  const nonPronta = rispostaNonPronta();
  if (nonPronta) return nonPronta;
  const x = daAltroSito(req, true);
  if (x) return x;
  if (!registrazioneConsentita(ipCliente(req.headers), Date.now())) {
    return errore(429, "Troppe registrazioni da questo indirizzo: riprova più tardi.");
  }
  const v = validaRegistrazione(await leggiJson(req));
  if ("errore" in v) return errore(400, v.errore);
  const d = v.ok;
  const c = await contesto();
  // Controllo anticipato (nessuna scrittura): il passo che conta è usaInvito, alla fine.
  if (!(await verificaInvito(c, d.invito))) return errore(400, INVITO_NON_VALIDO);
  if (await c.internalAdapter.findUserByEmail(d.email)) return errore(409, EMAIL_USATA);

  const org = await creaAzienda(c, d.azienda, slugDa(d.azienda), false, { registrata: true });
  let userId: string | null = null;
  try {
    await creaStatoAzienda(org.id, statoVuoto({ listini: DEFAULT_LISTINI, warehouses: WAREHOUSES }));
    // creaMembro, se fallisce, toglie da sé l'utente che aveva creato
    userId = await creaMembro(c, org.id, { nome: d.nome, ruoli: ["responsabile"], email: d.email, password: d.password });
    // prova: vero salvo con le chiavi vere (anche senza chiave: un'azienda nata così non va sincronizzata col conto vero)
    await aggiornaAbbonamento(org.id, () => ABBONAMENTO_NUOVO(modalitaStripe() !== "live", Date.now()));
    if (!(await usaInvito(c, d.invito, org.id))) {
      // Lo stesso codice usato da un'altra registrazione nel frattempo
      console.warn("Registrazione annullata: invito già usato", org.id);
      await annulla(c, org.id, userId);
      return errore(400, INVITO_NON_VALIDO);
    }
  } catch (e) {
    console.error("Registrazione non riuscita", e);
    await annulla(c, org.id, userId);
    // Due registrazioni con la stessa email nello stesso momento: il database rifiuta la seconda
    if (!userId && (await c.internalAdapter.findUserByEmail(d.email).catch(() => null))) return errore(409, EMAIL_USATA);
    return errore(500, "Non è stato possibile completare la registrazione. Riprova.");
  }
  // Riga del registro a nome del titolare (registra() firmerebbe "(assistenza)" dalla Piattaforma). Best-effort.
  try {
    await aggiungiEventi(org.id, [{ user: d.nome, role: "responsabile", device: "Registrazione", entity: "sistema", entityId: org.id, action: "Azienda registrata", detail: d.azienda }]);
  } catch (e) {
    console.error("Registro attività non aggiornato", org.id, e);
  }
  return ok({ ok: true }, 201);
}
