import { test } from "node:test";
import assert from "node:assert/strict";
import { aziendaCambiata, decidiAccesso, PIN_INATTIVITA_MS, PIN_TURNO_MS, ASSISTENZA_MS } from "./regole.ts";
import { RUOLI } from "./ruoli.ts";
import type { SessioneVista, AziendaVista, AssistenzaVista } from "./regole.ts";

const ORA = 1_800_000_000_000;
const DISP = { id: "d1", nome: "Tablet piazzale 1" };

type Input = {
  sessione: SessioneVista | null;
  azienda: AziendaVista | null;
  ruoliMembro: string | null;
  assistenza: AssistenzaVista | null;
  ora: number;
};

function base(): Input {
  return {
    sessione: {
      userId: "u1",
      nome: "Mario",
      ruoloPiattaforma: null,
      dueFattori: false,
      impersonata: false,
      aziendaAttiva: "a1",
      tipo: "password",
      creata: ORA - 1000,
      ultimaAttivita: ORA - 1000,
    },
    azienda: { id: "a1", nome: "Rossi Demolizioni", demo: false },
    ruoliMembro: "accettazione,smontatore",
    assistenza: null,
    ora: ORA,
  };
}

function superadmin(due = true): Input {
  const i = base();
  i.sessione = { ...i.sessione!, ruoloPiattaforma: "superadmin", dueFattori: due };
  i.ruoliMembro = null;
  i.assistenza = { id: "s1", organizationId: "a1", motivo: "Richiesta ticket 12", scade: ORA + 1000 };
  return i;
}

test("costanti", () => {
  assert.equal(PIN_INATTIVITA_MS, 300_000);
  assert.equal(PIN_TURNO_MS, 36_000_000);
  assert.equal(ASSISTENZA_MS, 7_200_000);
});

test("membro con più ruoli", () => {
  const r = decidiAccesso(base());
  assert.ok(!("negato" in r));
  if ("negato" in r) return;
  assert.deepEqual(r.ruoli, ["accettazione", "smontatore"]);
  assert.equal(r.superadmin, false);
  assert.equal(r.utente.id, "u1");
  assert.equal(r.azienda.id, "a1");
  assert.equal(r.tipo, "password");
  assert.equal(r.assistenza, undefined);
});

test("nessuna sessione", () => {
  const i = base();
  i.sessione = null;
  assert.deepEqual(decidiAccesso(i), { negato: 401, motivo: "nessuna-sessione" });
});

test("PIN fermo da 5 minuti + 1 ms: scaduta", () => {
  const i = base();
  i.sessione = { ...i.sessione!, tipo: "pin", dispositivo: DISP, ultimaAttivita: ORA - PIN_INATTIVITA_MS - 1 };
  assert.deepEqual(decidiAccesso(i), { negato: 401, motivo: "sessione-scaduta" });
});

test("PIN fermo da 4 min 59 s: accesso", () => {
  const i = base();
  i.sessione = { ...i.sessione!, tipo: "pin", dispositivo: DISP, ultimaAttivita: ORA - 299_000 };
  assert.ok(!("negato" in decidiAccesso(i)));
});

test("PIN fermo da esattamente 5 minuti: accesso (limite escluso)", () => {
  const i = base();
  i.sessione = { ...i.sessione!, tipo: "pin", dispositivo: DISP, ultimaAttivita: ORA - PIN_INATTIVITA_MS };
  assert.ok(!("negato" in decidiAccesso(i)));
});

test("PIN creato 10 ore + 1 ms fa ma attivo ora: scaduta", () => {
  const i = base();
  i.sessione = { ...i.sessione!, tipo: "pin", dispositivo: DISP, creata: ORA - PIN_TURNO_MS - 1, ultimaAttivita: ORA };
  assert.deepEqual(decidiAccesso(i), { negato: 401, motivo: "sessione-scaduta" });
});

test("PIN creato da esattamente 10 ore e attivo: accesso", () => {
  const i = base();
  i.sessione = { ...i.sessione!, tipo: "pin", dispositivo: DISP, creata: ORA - PIN_TURNO_MS, ultimaAttivita: ORA };
  assert.ok(!("negato" in decidiAccesso(i)));
});

test("sessione password ferma da 3 ore: accesso", () => {
  const i = base();
  i.sessione = { ...i.sessione!, ultimaAttivita: ORA - 3 * 3_600_000, creata: ORA - 20 * 3_600_000 };
  assert.ok(!("negato" in decidiAccesso(i)));
});

test("la scadenza del PIN viene prima di tutto il resto", () => {
  const i = base();
  i.sessione = { ...i.sessione!, tipo: "pin", dispositivo: DISP, aziendaAttiva: null, ultimaAttivita: ORA - PIN_INATTIVITA_MS - 1 };
  i.azienda = null;
  assert.deepEqual(decidiAccesso(i), { negato: 401, motivo: "sessione-scaduta" });
});

test("nessuna azienda attiva", () => {
  const i = base();
  i.sessione = { ...i.sessione!, aziendaAttiva: null };
  i.azienda = null;
  assert.deepEqual(decidiAccesso(i), { negato: 403, motivo: "nessuna-azienda" });
});

test("azienda attiva ma inesistente", () => {
  const i = base();
  i.azienda = null;
  assert.deepEqual(decidiAccesso(i), { negato: 403, motivo: "nessuna-azienda" });
});

test("azienda diversa da quella attiva della sessione: nessuna azienda", () => {
  const i = base();
  i.azienda = { id: "a2", nome: "Altra", demo: false };
  assert.deepEqual(decidiAccesso(i), { negato: 403, motivo: "nessuna-azienda" });
});

test("non membro (nessun ruolo)", () => {
  const i = base();
  i.ruoliMembro = null;
  assert.deepEqual(decidiAccesso(i), { negato: 403, motivo: "non-membro" });
});

test("membro con solo owner: non-membro", () => {
  const i = base();
  i.ruoliMembro = "owner";
  assert.deepEqual(decidiAccesso(i), { negato: 403, motivo: "non-membro" });
});

test("membro con ruolo valido e sconosciuto: solo quello valido", () => {
  const i = base();
  i.ruoliMembro = "owner,vendite";
  const r = decidiAccesso(i);
  assert.ok(!("negato" in r));
  if (!("negato" in r)) assert.deepEqual(r.ruoli, ["vendite"]);
});

test("super admin senza due fattori, con assistenza valida: due-fattori", () => {
  assert.deepEqual(decidiAccesso(superadmin(false)), { negato: 403, motivo: "due-fattori" });
});

test("super admin con assistenza valida", () => {
  const r = decidiAccesso(superadmin());
  assert.ok(!("negato" in r));
  if ("negato" in r) return;
  assert.deepEqual(r.ruoli, [...RUOLI]);
  assert.equal(r.superadmin, true);
  assert.equal(r.assistenza?.id, "s1");
  assert.equal(r.assistenza?.motivo, "Richiesta ticket 12");
  assert.equal(r.assistenza?.scade, new Date(ORA + 1000).toISOString());
});

test("super admin con assistenza scaduta (scade = ora)", () => {
  const i = superadmin();
  i.assistenza = { ...i.assistenza!, scade: ORA };
  assert.deepEqual(decidiAccesso(i), { negato: 403, motivo: "assistenza-scaduta" });
});

test("super admin con assistenza terminata (fine impostata)", () => {
  const i = superadmin();
  i.assistenza = { ...i.assistenza!, fine: ORA - 10 };
  assert.deepEqual(decidiAccesso(i), { negato: 403, motivo: "assistenza-scaduta" });
});

test("super admin con assistenza di un'altra azienda", () => {
  const i = superadmin();
  i.assistenza = { ...i.assistenza!, organizationId: "a2" };
  assert.deepEqual(decidiAccesso(i), { negato: 403, motivo: "assistenza-scaduta" });
});

test("super admin senza assistenza", () => {
  const i = superadmin();
  i.assistenza = null;
  assert.deepEqual(decidiAccesso(i), { negato: 403, motivo: "assistenza-scaduta" });
});

test("super admin senza due fattori che è anche membro: due-fattori (il codice vale sempre)", () => {
  const i = superadmin(false);
  i.ruoliMembro = "vendite";
  assert.deepEqual(decidiAccesso(i), { negato: 403, motivo: "due-fattori" });
});

test("super admin membro con due fattori: entra con i suoi ruoli, senza assistenza", () => {
  const i = superadmin();
  i.ruoliMembro = "vendite";
  i.assistenza = null;
  const r = decidiAccesso(i);
  assert.ok(!("negato" in r));
  if (!("negato" in r)) {
    assert.deepEqual(r.ruoli, ["vendite"]);
    assert.equal(r.superadmin, true);
    assert.equal(r.assistenza, undefined);
  }
});

test("utente non superadmin con assistenza (dati incoerenti): non-membro", () => {
  const i = base();
  i.ruoliMembro = null;
  i.assistenza = { id: "s1", organizationId: "a1", motivo: "x", scade: ORA + 1000 };
  assert.deepEqual(decidiAccesso(i), { negato: 403, motivo: "non-membro" });
});

test("sessione impersonata: 403 impersonazione, anche per un membro valido", () => {
  const i = base();
  i.sessione = { ...i.sessione!, impersonata: true };
  assert.deepEqual(decidiAccesso(i), { negato: 403, motivo: "impersonazione" });
});

test("sessione impersonata: negata anche con super admin, due fattori e assistenza valida", () => {
  const i = superadmin();
  i.sessione = { ...i.sessione!, impersonata: true };
  assert.deepEqual(decidiAccesso(i), { negato: 403, motivo: "impersonazione" });
});

test("PIN senza dispositivo valido (revocato, sparito o di un'altra azienda): 401 dispositivo-revocato", () => {
  const i = base();
  i.sessione = { ...i.sessione!, tipo: "pin", ultimaAttivita: ORA };
  assert.deepEqual(decidiAccesso(i), { negato: 401, motivo: "dispositivo-revocato" });
});

test("PIN con dispositivo valido: accesso con il nome del dispositivo", () => {
  const i = base();
  i.sessione = { ...i.sessione!, tipo: "pin", dispositivo: DISP, ultimaAttivita: ORA };
  const r = decidiAccesso(i);
  assert.ok(!("negato" in r));
  if ("negato" in r) return;
  assert.equal(r.tipo, "pin");
  assert.deepEqual(r.dispositivo, DISP);
});

test("PIN scaduto e senza dispositivo: prima la scadenza", () => {
  const i = base();
  i.sessione = { ...i.sessione!, tipo: "pin", ultimaAttivita: ORA - PIN_INATTIVITA_MS - 1 };
  assert.deepEqual(decidiAccesso(i), { negato: 401, motivo: "sessione-scaduta" });
});

test("sessione password senza dispositivo: accesso (il dispositivo serve solo al PIN)", () => {
  assert.ok(!("negato" in decidiAccesso(base())));
});

test("scheda partita con un'altra azienda (x-azienda diversa dalla sessione): rifiuto", () => {
  assert.equal(aziendaCambiata("b", "c"), true);
  // La sessione non ha più un'azienda (uscita dall'assistenza in un'altra scheda): rifiuto
  assert.equal(aziendaCambiata("b", null), true);
  assert.equal(aziendaCambiata(" b ", "b"), false);
  assert.equal(aziendaCambiata("b", "b"), false);
});

test("senza intestazione x-azienda (o vuota) decide solo la sessione", () => {
  assert.equal(aziendaCambiata(null, "c"), false);
  assert.equal(aziendaCambiata(undefined, "c"), false);
  assert.equal(aziendaCambiata("", "c"), false);
  assert.equal(aziendaCambiata("  ", null), false);
});

test("password su dispositivo condiviso: 5 minuti senza attività, 401 sessione-scaduta", () => {
  const i = base();
  i.sessione = { ...i.sessione!, dispositivoCondiviso: true, ultimaAttivita: ORA - PIN_INATTIVITA_MS - 1 };
  assert.deepEqual(decidiAccesso(i), { negato: 401, motivo: "sessione-scaduta" });
});

test("password su dispositivo condiviso: turno di 10 ore anche con attività recente", () => {
  const i = base();
  i.sessione = { ...i.sessione!, dispositivoCondiviso: true, creata: ORA - PIN_TURNO_MS - 1, ultimaAttivita: ORA };
  assert.deepEqual(decidiAccesso(i), { negato: 401, motivo: "sessione-scaduta" });
});

test("password su dispositivo condiviso e attiva: accesso, con dispositivoCondiviso per il blocco nel browser", () => {
  const i = base();
  i.sessione = { ...i.sessione!, dispositivoCondiviso: true, ultimaAttivita: ORA - 1000 };
  const r = decidiAccesso(i);
  assert.ok(!("negato" in r));
  if ("negato" in r) return;
  assert.equal(r.dispositivoCondiviso, true);
});

test("password fuori da un dispositivo condiviso: nessun limite di inattività", () => {
  const i = base();
  i.sessione = { ...i.sessione!, ultimaAttivita: ORA - PIN_TURNO_MS * 2, creata: ORA - PIN_TURNO_MS * 2 };
  const r = decidiAccesso(i);
  assert.ok(!("negato" in r));
  if ("negato" in r) return;
  assert.equal(r.dispositivoCondiviso, undefined);
});
