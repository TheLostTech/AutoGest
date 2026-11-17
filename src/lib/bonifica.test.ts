// Termini della bonifica: obiettivo interno 7 giorni di calendario, legge 10 giorni lavorativi
// (art. 6 c. 2 lett. a D.Lgs. 209/2003 come modificato dal D.Lgs. 119/2020). Si eseguono con: npm test
process.env.TZ = "Europe/Rome";

import { test } from "node:test";
import assert from "node:assert/strict";
import { bonificaStato } from "./periodo.ts";

const intake = "2026-11-16T09:00:00+01:00"; // lunedì

test("entro l'obiettivo interno: giorni rimasti e nessun avviso", () => {
  const s = bonificaStato(intake, new Date("2026-11-18T10:00:00+01:00"));
  assert.equal(s.days, 2);
  assert.equal(s.left, 5);
  assert.equal(s.level, "ok");
  assert.equal(s.fuoriLegge, false);
});

test("a 2 giorni dall'obiettivo: attenzione; il settimo giorno: oggi", () => {
  assert.equal(bonificaStato(intake, new Date("2026-11-21T10:00:00+01:00")).level, "attenzione");
  assert.equal(bonificaStato(intake, new Date("2026-11-23T10:00:00+01:00")).level, "oggi");
});

test("oltre i 7 giorni ma dentro la legge: scaduta, non fuori legge, con la data di legge", () => {
  const s = bonificaStato(intake, new Date("2026-11-25T10:00:00+01:00"));
  assert.equal(s.level, "scaduta");
  assert.equal(s.fuoriLegge, false);
  const legge = new Date(s.legalDue);
  assert.deepEqual([legge.getMonth(), legge.getDate()], [10, 30]);
  assert.match(s.label, /legge entro/);
});

test("oltre i 10 giorni lavorativi: fuori termine di legge", () => {
  const s = bonificaStato(intake, new Date("2026-12-01T10:00:00+01:00"));
  assert.equal(s.fuoriLegge, true);
  assert.match(s.label, /termine di legge/);
});
