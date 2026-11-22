import { readFile } from "node:fs/promises";
import path from "node:path";
import { connection } from "next/server";
import { accessoDaRichiesta } from "@/lib/accesso/server";
import { leggiStato } from "@/lib/archivio-azienda";
import { fotoPubblica } from "@/lib/catalogo-pubblico";
import { aziendaNegozio } from "@/lib/negozio-server";
import { cartellaFotoAzienda } from "@/lib/server-data";

const NON_TROVATA = () => new Response("Foto non trovata", { status: 404 });

async function leggi(aziendaId: string, name: string): Promise<Uint8Array | null> {
  try {
    return new Uint8Array(await readFile(path.join(cartellaFotoAzienda(aziendaId), name)));
  } catch {
    return null;
  }
}
const jpeg = (bytes: Uint8Array, cache: string) => new Response(bytes as BodyInit, { headers: { "Content-Type": "image/jpeg", "Cache-Control": cache } });

export async function GET(req: Request, { params }: { params: Promise<{ name: string }> }) {
  await connection();
  const { name } = await params;
  // Solo nomi generati dal server: niente percorsi verso altre cartelle
  if (!/^[a-z0-9]+\.jpg$/.test(name)) return NON_TROVATA();
  // Con una sessione valida: la cartella dell'azienda della sessione
  const a = await accessoDaRichiesta(req);
  if (!(a instanceof Response)) {
    const bytes = await leggi(a.azienda.id, name);
    if (bytes) return jpeg(bytes, "private, max-age=31536000, immutable");
  }
  // Senza sessione (o foto non dell'azienda della sessione): solo le foto dei pezzi in vendita sul negozio pubblico,
  // dall'azienda del negozio. Qualunque altra foto: 404.
  const az = await aziendaNegozio();
  if (!az) return NON_TROVATA();
  try {
    const s = await leggiStato(az);
    if (!s.state || !fotoPubblica(s.state, name)) return NON_TROVATA();
  } catch {
    return NON_TROVATA();
  }
  const bytes = await leggi(az, name);
  // Pubblica ma non per sempre: un pezzo ritirato smette di avere la foto, quindi niente "immutable"
  return bytes ? jpeg(bytes, "public, max-age=300") : NON_TROVATA();
}
