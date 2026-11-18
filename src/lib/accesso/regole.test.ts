import { test } from "node:test";
import assert from "node:assert/strict";
import { decidiAccesso, PIN_INATTIVITA_MS, PIN_TURNO_MS, ASSISTENZA_MS } from "./regole.ts";
import { RUOLI } from "./ruoli.ts";
import type { SessioneVista, AziendaVista, AssistenzaVista } from "./regole.ts";

const ORA = 1_800_000_000_000;

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
  i.sessione = { ...i.sessione!, tipo: "pin", ultimaAttivita: ORA - PIN_INATTIVITA_MS - 1 };
  assert.deepEqual(decidiAccesso(i), { negato: 401, motivo: "sessione-scaduta" });
});

test("PIN fermo da 4 min 59 s: accesso", () => {
  const i = base();
  i.sessione = { ...i.sessione!, tipo: "pin", ultimaAttivita: ORA - 299_000 };
  assert.ok(!("negato" in decidiAccesso(i)));
});

test("PIN fermo da esattamente 5 minuti: accesso (limite escluso)", () => {
  const i = base();
  i.sessione = { ...i.sessione!, tipo: "pin", ultimaAttivita: ORA - PIN_INATTIVITA_MS };
  assert.ok(!("negato" in decidiAccesso(i)));
});

test("PIN creato 10 ore + 1 ms fa ma attivo ora: scaduta", () => {
  const i = base();
  i.sessione = { ...i.sessione!, tipo: "pin", creata: ORA - PIN_TURNO_MS - 1, ultimaAttivita: ORA };
  assert.deepEqual(decidiAccesso(i), { negato: 401, motivo: "sessione-scaduta" });
});

test("PIN creato da esattamente 10 ore e attivo: accesso", () => {
  const i = base();
  i.sessione = { ...i.sessione!, tipo: "pin", creata: ORA - PIN_TURNO_MS, ultimaAttivita: ORA };
  assert.ok(!("negato" in decidiAccesso(i)));
});

test("sessione password ferma da 3 ore: accesso", () => {
  const i = base();
  i.sessione = { ...i.sessione!, ultimaAttivita: ORA - 3 * 3_600_000, creata: ORA - 20 * 3_600_000 };
  assert.ok(!("negato" in decidiAccesso(i)));
});

test("la scadenza del PIN viene prima di tutto il resto", () => {
  const i = base();
  i.sessione = { ...i.sessione!, tipo: "pin", aziendaAttiva: null, ultimaAttivita: ORA - PIN_INATTIVITA_MS - 1 };
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
