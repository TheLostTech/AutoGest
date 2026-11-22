// Scarica una richiesta scritta. Solo super admin; sempre come allegato, con il tipo giusto.
import { connection } from "next/server";
import { superadminDaRichiesta } from "@/lib/accesso/server";
import { RICHIESTA_CONTENT_TYPE, type TipoRichiesta } from "@/lib/accesso/richieste";
import { FILE_RICHIESTA, leggiFileRichiesta } from "@/lib/piattaforma/richieste-file";
import { aziendaEsiste, errore } from "@/lib/piattaforma/server";

const TIPO_DA_ESTENSIONE: Record<string, TipoRichiesta> = { pdf: "pdf", jpg: "jpeg", png: "png" };

export async function GET(req: Request, { params }: { params: Promise<{ file: string }> }) {
  await connection();
  const g = await superadminDaRichiesta(req);
  if (g instanceof Response) return g;
  const { file } = await params;
  const azienda = await aziendaEsiste(new URL(req.url).searchParams.get("aziendaId"));
  if (!azienda || !FILE_RICHIESTA.test(file)) return errore(404, "File non trovato.");
  const dati = await leggiFileRichiesta(azienda.id, file);
  if (!dati) return errore(404, "File non trovato.");
  const tipo = TIPO_DA_ESTENSIONE[file.split(".")[1]];
  return new Response(new Uint8Array(dati), {
    headers: {
      "Content-Type": RICHIESTA_CONTENT_TYPE[tipo],
      "Content-Disposition": `attachment; filename="richiesta-${file}"`,
      "X-Content-Type-Options": "nosniff",
      "Cache-Control": "no-store",
    },
  });
}
