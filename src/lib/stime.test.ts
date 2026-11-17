// Stime dei componenti della bonifica per modello e confronto con le pesate. Si eseguono con: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { differenzaPesata, pesoDiverso, stimaComponenti } from "./stime.ts";

const panda = { massaKg: 975, fuel: "Benzina", year: 2013 };
const golfDiesel = { massaKg: 1260, fuel: "Diesel", year: 2011 };

test("la batteria e le gomme di un'auto più pesante pesano di più", () => {
  const a = stimaComponenti(panda);
  const b = stimaComponenti(golfDiesel);
  assert.ok(b.batteria.kgPerUnit > a.batteria.kgPerUnit);
  assert.ok(b.pneumatici.kgPerUnit > a.pneumatici.kgPerUnit);
  assert.ok(a.batteria.kgPerUnit >= 11 && b.batteria.kgPerUnit <= 25);
  assert.equal(a.pneumatici.qty, 4);
});

test("il carburante pesa per litro secondo l'alimentazione", () => {
  assert.equal(stimaComponenti(golfDiesel).carburante.kgPerUnit, 0.84);
  assert.equal(stimaComponenti(panda).carburante.kgPerUnit, 0.74);
});

test("airbag: 2 prima del 2008, di più dopo", () => {
  assert.equal(stimaComponenti({ ...panda, year: 2005 }).airbag.qty, 2);
  assert.ok(stimaComponenti(golfDiesel).airbag.qty >= 4);
});

test("pesoDiverso: avviso se pesa e libretto differiscono di oltre il 25%", () => {
  assert.equal(pesoDiverso(1000, 975), false);
  assert.equal(pesoDiverso(700, 975), true);
  assert.equal(pesoDiverso(1300, 975), true);
});

test("differenzaPesata: quanto aggiungere o togliere per tornare al peso vero", () => {
  assert.equal(differenzaPesata(420, 398), -22);
  assert.equal(differenzaPesata(100, 112.36), 12.4);
  assert.equal(differenzaPesata(50, 50), 0);
});
