// Caricamento della richiesta scritta (PDF, JPEG o PNG, al massimo 10 MB). Solo super admin.
import { superadminDaRichiesta } from "@/lib/accesso/server";
import { RICHIESTA_MAX_BYTE, tipoRichiesta } from "@/lib/accesso/richieste";
import { salvaFileRichiesta } from "@/lib/piattaforma/richieste-file";
import { aziendaEsiste, daAltroSito, errore, ok } from "@/lib/piattaforma/server";

export async function POST(req: Request) {
  const g = await superadminDaRichiesta(req);
  if (g instanceof Response) return g;
  // Un modulo con file non è JSON: basta l'Origin di questo sito (un'altra pagina non può inviarlo con i cookie)
  const x = daAltroSito(req, false);
  if (x) return x;
  const lunghezza = Number(req.headers.get("content-length") ?? 0);
  if (lunghezza > RICHIESTA_MAX_BYTE + 65_536) return errore(413, "Il file è troppo grande: massimo 10 MB.");
  let form: FormData;
  try {
    form = await req.formData();
  } catch {
    return errore(400, "Richiesta non valida.");
  }
  const azienda = await aziendaEsiste(form.get("aziendaId"));
  if (!azienda) return errore(404, "Azienda non trovata.");
  const file = form.get("file");
  if (!(file instanceof File)) return errore(400, "Scegli il file della richiesta.");
  if (file.size > RICHIESTA_MAX_BYTE) return errore(413, "Il file è troppo grande: massimo 10 MB.");
  const dati = new Uint8Array(await file.arrayBuffer());
  const tipo = tipoRichiesta(dati.subarray(0, 16));
  if (!tipo) return errore(415, "Sono ammessi solo PDF, JPEG o PNG.");
  const fileId = await salvaFileRichiesta(azienda.id, tipo, dati);
  return ok({ fileId }, 201);
}
