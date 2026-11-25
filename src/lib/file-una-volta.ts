// File che si creano una volta sola (segreto dell'accesso, chiave dei collegamenti, archivio di un'azienda nuova).
// Con flag "wx" il file nasce vuoto e si riempie dopo: un altro processo che lo legge in quel momento (es. i 9 worker
// della build, o due route al primo avvio) lo trova vuoto o a metà. Qui si scrive tutto in un file temporaneo e lo si
// collega al nome finale: il collegamento fallisce se il file c'è già, e chi legge vede il file assente o completo.
import { randomBytes } from "node:crypto";
import { linkSync, unlinkSync, writeFileSync } from "node:fs";
import { link, unlink, writeFile } from "node:fs/promises";

const temporaneo = (file: string) => `${file}.${process.pid}.${randomBytes(4).toString("hex")}.tmp`;
const esisteGia = (e: unknown) => (e as NodeJS.ErrnoException).code === "EEXIST";

/** true se l'ha creato questa chiamata, false se c'era già (in quel caso il file non si tocca). */
export function creaUnaVoltaSync(file: string, contenuto: string, mode = 0o600): boolean {
  const tmp = temporaneo(file);
  writeFileSync(tmp, contenuto, { mode });
  try {
    linkSync(tmp, file);
    return true;
  } catch (e) {
    if (esisteGia(e)) return false;
    throw e;
  } finally {
    try {
      unlinkSync(tmp);
    } catch {}
  }
}

export async function creaUnaVolta(file: string, contenuto: string, mode = 0o600): Promise<boolean> {
  const tmp = temporaneo(file);
  await writeFile(tmp, contenuto, { mode });
  try {
    await link(tmp, file);
    return true;
  } catch (e) {
    if (esisteGia(e)) return false;
    throw e;
  } finally {
    await unlink(tmp).catch(() => undefined);
  }
}
