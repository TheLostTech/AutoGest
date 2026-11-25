// Registrazione libera del titolare: crea l'azienda, l'archivio vuoto, il titolare, la scheda con i consensi
// e l'abbonamento "nuovo" senza fine della prova. Pubblica (senza sessione) e senza accesso: il titolare entra
// dopo aver confermato l'email, che fa partire i 15 giorni (auth/conferma-titolare.ts). Spec prova-15-giorni, sezione 3.
// Una registrazione mai confermata con la stessa email si sostituisce: chi l'ha fatta non ha dimostrato di avere
// quell'email, e non deve poterla occupare (né preparare un account da usare dopo la conferma del vero titolare).
import { checkBotId } from "botid/server";
import { ABBONAMENTO_NUOVO } from "@/lib/abbonamento";
import { aggiornaAbbonamento } from "@/lib/abbonamento-server";
import { rispostaNonPronta } from "@/lib/accesso/pronta";
import { registrazioneConsentita, validaRegistrazione } from "@/lib/accesso/registrazione";
import { registrazioneDaRobot } from "@/lib/accesso/robot";
import { RITORNO_CONFERMA } from "@/lib/accesso/conferma";
import { registrazioneInSospeso } from "@/lib/auth/conferma-titolare";
import { ipCliente } from "@/lib/auth/intestazioni-ip";
import { auth } from "@/lib/auth/server";
import { aggiungiEventi, creaStatoAzienda } from "@/lib/archivio-azienda";
import { creaAzienda, creaMembro, slugDa } from "@/lib/piattaforma/crea";
import { contesto, daAltroSito, errore, leggiJson, ok, type Contesto } from "@/lib/piattaforma/server";
import { DEFAULT_LISTINI } from "@/lib/pricing";
import { modalitaStripe } from "@/lib/stripe/server";
import { schedaRegistrazione } from "@/lib/consensi";
import { deposito } from "@/lib/deposito";
import { statoVuoto } from "@/lib/stato-iniziale";
import { WAREHOUSES } from "@/lib/warehouse";

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

// Con l'endpoint di Better Auth, che firma il link (valido 48 ore). La richiesta passata è nuova e senza cookie: serve
// solo a dare l'indirizzo del sito al link quando Better Auth non ne ha uno fisso (in locale), e una sessione aperta in
// questo browser (per esempio del super admin) non deve entrare nell'invio.
async function inviaConferma(req: Request, email: string): Promise<boolean> {
  try {
    await auth.api.sendVerificationEmail({
      body: { email, callbackURL: RITORNO_CONFERMA },
      request: new Request(new URL("/api/auth/send-verification-email", req.url), { method: "POST" }),
      asResponse: false,
    });
    return true;
  } catch (e) {
    console.error("Email di conferma non inviata", e instanceof Error ? e.message : e);
    return false;
  }
}

export async function POST(req: Request) {
  const nonPronta = await rispostaNonPronta();
  if (nonPronta) return nonPronta;
  const x = daAltroSito(req, true);
  if (x) return x;
  const ip = ipCliente(req.headers);
  if (!registrazioneConsentita(ip, Date.now())) {
    return errore(429, "Troppe registrazioni da questo indirizzo: riprova più tardi.");
  }
  // Dopo il limite per indirizzo, che costa meno: BotID chiede a Vercel a ogni richiesta
  if (await registrazioneDaRobot(() => checkBotId())) return errore(403, "Registrazione non riuscita.");
  const v = validaRegistrazione(await leggiJson(req));
  if ("errore" in v) return errore(400, v.errore);
  const d = v.ok;
  const c = await contesto();
  const esistente = await c.internalAdapter.findUserByEmail(d.email);
  if (esistente) {
    // Titolare confermato, dipendente, super admin: la stessa risposta di sempre. Registrazione in sospeso: si toglie.
    const daTogliere = await registrazioneInSospeso(c, esistente.user).catch((e: unknown) => {
      console.error("Registrazione: controllo dell'email già usata non riuscito", e);
      return null;
    });
    if (!daTogliere) return errore(409, EMAIL_USATA);
    for (const [i, id] of daTogliere.entries()) await annulla(c, id, i === daTogliere.length - 1 ? esistente.user.id : null);
    console.info("Registrazione mai confermata sostituita da una nuova con la stessa email", daTogliere);
    if (await c.internalAdapter.findUserByEmail(d.email).catch(() => esistente)) {
      return errore(500, "Non è stato possibile completare la registrazione. Riprova.");
    }
  }

  const org = await creaAzienda(c, d.azienda, slugDa(d.azienda), false, { registrata: true });
  let userId: string | null = null;
  try {
    await creaStatoAzienda(org.id, statoVuoto({ listini: DEFAULT_LISTINI, warehouses: WAREHOUSES }));
    // Contatti e consensi (versione dei testi, ora, indirizzo): annulla la toglie con il resto dell'azienda
    if (!(await deposito().creaDocumento(org.id, "registrazione", schedaRegistrazione(d, ip, Date.now())))) {
      throw new Error("Scheda della registrazione già presente");
    }
    // Prima del titolare: quando l'utente esiste, l'abbonamento "in attesa di conferma" c'è già (e lo ferma all'accesso).
    // prova: vero salvo con le chiavi vere (anche senza chiave: un'azienda nata così non va sincronizzata col conto vero).
    // fineProva resta null: i 15 giorni partono dalla conferma dell'email
    await aggiornaAbbonamento(org.id, () => ABBONAMENTO_NUOVO(modalitaStripe() !== "live", Date.now()));
    // creaMembro, se fallisce, toglie da sé l'utente che aveva creato
    userId = await creaMembro(c, org.id, { nome: d.nome, ruoli: ["responsabile"], email: d.email, password: d.password });
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
  // Niente accesso qui: il titolare entra dopo la conferma dell'email. Se l'email non parte la registrazione resta:
  // la pagina lo dice e l'email si rimanda (anche dalla pagina di accesso).
  const inviata = await inviaConferma(req, d.email);
  return ok({ ok: true, conferma: true, inviata }, 201);
}
