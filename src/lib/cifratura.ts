// Cifratura delle credenziali dei collegamenti (solo server). Vedi src/app/api/collegamenti/route.ts.
import { createCipheriv, createDecipheriv, randomBytes } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { DATA_DIR } from "@/lib/server-data";

const KEY_FILE = path.join(DATA_DIR, ".chiave-collegamenti");

let chiave: Buffer | undefined;
async function key() {
  if (chiave) return chiave;
  const env = process.env.CHIAVE_COLLEGAMENTI;
  if (env && /^[0-9a-f]{64}$/i.test(env)) return (chiave = Buffer.from(env, "hex"));
  try {
    chiave = Buffer.from((await readFile(KEY_FILE, "utf8")).trim(), "hex");
  } catch {
    chiave = randomBytes(32);
    await mkdir(DATA_DIR, { recursive: true });
    await writeFile(KEY_FILE, chiave.toString("hex"), { mode: 0o600 });
  }
  return chiave;
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
