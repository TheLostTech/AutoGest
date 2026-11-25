// Prove del deposito su disco, su una cartella dati temporanea (DATI_DIR sempre nuova, mai i dati veri).
import { mkdtempSync } from "node:fs";
import { rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { provaContratto } from "./contratto.ts";

const cartella = mkdtempSync(path.join(tmpdir(), "prova-deposito-"));
process.env.DATI_DIR = cartella;

provaContratto(
  "disco",
  async () => (await import("./disco.ts")).depositoDisco(),
  () => rm(cartella, { recursive: true, force: true }),
);
