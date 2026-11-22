import { createHash, randomBytes } from "node:crypto";
import { ALFABETO_INVITO, INVITO_MS, LUNGHEZZA_INVITO, formatoCodice, invitoValido } from "@/lib/accesso/inviti-regole";
import type { Contesto } from "./server";

// Codici invito per la registrazione: monouso, 30 giorni, si salva solo sha256 del codice senza trattini.

type Riga = { id: string; codiceHash: string; scade: unknown; usato?: unknown };

const hashDi = (normalizzato: string) => createHash("sha256").update(normalizzato).digest("hex");
const ms = (d: unknown) => (d == null ? null : new Date(d as string | number | Date).getTime());

function nuovoCodice(): string {
  // 256 è multiplo di 32: il resto non sbilancia i caratteri.
  let s = "";
  for (const b of randomBytes(LUNGHEZZA_INVITO)) s += ALFABETO_INVITO[b % ALFABETO_INVITO.length];
  return `${s.slice(0, 4)}-${s.slice(4, 8)}-${s.slice(8)}`;
}

export async function creaInvito(c: Contesto, creatoDa: string, nota: string): Promise<{ codice: string; scade: number }> {
  const ora = Date.now();
  const scade = ora + INVITO_MS;
  const codice = nuovoCodice();
  await c.adapter.create({
    model: "invito",
    data: { codiceHash: hashDi(codice.replaceAll("-", "")), nota, creatoDa, creato: new Date(ora), scade: new Date(scade) },
  });
  return { codice, scade };
}

async function trova(c: Contesto, codice: string): Promise<Riga | null> {
  const f = formatoCodice(codice);
  if (!f) return null;
  return c.adapter.findOne<Riga>({ model: "invito", where: [{ field: "codiceHash", value: hashDi(f.replaceAll("-", "")) }] });
}

const valido = (r: Riga | null) => invitoValido(r ? { scade: ms(r.scade) ?? 0, usato: ms(r.usato) } : null, Date.now());

export async function verificaInvito(c: Contesto, codice: string): Promise<boolean> {
  return valido(await trova(c, codice));
}

// Un solo processo Node (docs/ACCESSO.md): la fila in memoria rende atomico leggi-controlla-scrivi.
let coda: Promise<unknown> = Promise.resolve();

export function usaInvito(c: Contesto, codice: string, aziendaId: string): Promise<boolean> {
  const lavoro = coda.then(async () => {
    const r = await trova(c, codice);
    if (!r || !valido(r)) return false;
    await c.adapter.update({ model: "invito", where: [{ field: "id", value: r.id }], update: { usatoDa: aziendaId, usato: new Date() } });
    return true;
  });
  coda = lavoro.catch(() => undefined);
  return lavoro;
}

export type StatoInvito = "valido" | "usato" | "scaduto";
export type RigaInvito = { id: string; nota: string; creato: string; scade: string; stato: StatoInvito; azienda: string | null };

export async function elencoInviti(c: Contesto): Promise<RigaInvito[]> {
  const righe = await c.adapter.findMany<{ id: string; nota: string; creato: unknown; scade: unknown; usato?: unknown; usatoDa?: string | null }>({
    model: "invito",
    sortBy: { field: "creato", direction: "desc" },
  });
  const ora = Date.now();
  const nomi = new Map<string, string>();
  for (const r of righe) {
    if (r.usatoDa && !nomi.has(r.usatoDa)) {
      const o = await c.adapter.findOne<{ name: string }>({ model: "organization", where: [{ field: "id", value: r.usatoDa }] });
      if (o) nomi.set(r.usatoDa, o.name);
    }
  }
  return righe.map((r) => ({
    id: r.id,
    nota: r.nota,
    creato: new Date(r.creato as string | number | Date).toISOString(),
    scade: new Date(r.scade as string | number | Date).toISOString(),
    stato: r.usato != null ? "usato" : (ms(r.scade) ?? 0) <= ora ? "scaduto" : "valido",
    azienda: r.usatoDa ? (nomi.get(r.usatoDa) ?? null) : null,
  }));
}
