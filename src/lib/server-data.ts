import path from "node:path";

// Dove il server tiene i dati condivisi dell'azienda (archivio e foto).
// Di serie è la cartella .demo-data del progetto; sul server dell'azienda si sceglie con DATI_DIR,
// es. D:\AutoGest\dati su Windows Server: per il backup basta copiare quella cartella.
// Nel passaggio al cloud questo modulo è l'unico punto da sostituire (database + archivio di file).
export const DATA_DIR = path.resolve(/*turbopackIgnore: true*/ process.env.DATI_DIR || path.join(process.cwd(), ".demo-data"));
export const PHOTO_DIR = path.join(DATA_DIR, "foto");
export const ALLEGATI_DIR = path.join(DATA_DIR, "allegati");
