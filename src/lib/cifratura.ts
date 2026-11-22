// Cifratura delle credenziali dei collegamenti (solo server). Vedi src/app/api/collegamenti/route.ts.
import { createCipheriv, createDecipheriv, randomBytes } from "node:crypto";
import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import { creaUnaVolta } from "@/lib/file-una-volta";
import { DATA_DIR } from "@/lib/server-data";

const KEY_FILE = path.join(DATA_DIR, ".chiave-collegamenti");

let chiave: Buffer | undefined;
async function key() {
  if (chiave) return chiave;
  const env = process.env.CHIAVE_COLLEGAMENTI;
  if (env && /^[0-9a-f]{64}$/i.test(env)) return (chiave = Buffer.from(env, "hex"));
  try {
    return (chiave = Buffer.from((await readFile(KEY_FILE, "utf8")).trim(), "hex"));
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code !== "ENOENT") throw e;
  }
  // Prima volta: se due processi la generano insieme vince la prima scritta, e l'altro usa quella
  // (due chiavi diverse renderebbero illeggibili le credenziali cifrate con la perdente)
  await mkdir(DATA_DIR, { recursive: true });
  const nuova = randomBytes(32);
  if (await creaUnaVolta(KEY_FILE, nuova.toString("hex"))) return (chiave = nuova);
  return (chiave = Buffer.from((await readFile(KEY_FILE, "utf8")).trim(), "hex"));
}

export async function cifra(dati: Buffer) {
  const iv = randomBytes(12);
  const c = createCipheriv("aes-256-gcm", await key(), iv);
  const out = Buffer.concat([c.update(dati), c.final()]);
  return [iv, c.getAuthTag(), out].map((b) => b.toString("base64")).join(".");
}

// Per le chiamate vere ai servizi (integrazioni future)
export async function decifra(s: string) {
  const [iv, tag, dati] = s.split(".").map((x) => Buffer.from(x, "base64"));
  const d = createDecipheriv("aes-256-gcm", await key(), iv);
  d.setAuthTag(tag);
  return Buffer.concat([d.update(dati), d.final()]);
}
