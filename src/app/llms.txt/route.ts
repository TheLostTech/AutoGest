import { ARTICOLI } from "@/lib/news";
import { BRAND, PRODUTTORE } from "@/lib/config";
import { SITO } from "@/components/sito/Sito";

// Indice per gli assistenti AI (convenzione llms.txt, https://llmstxt.org): chi siamo, le pagine pubbliche e,
// per ogni scheda normativa, la risposta in breve con le fonti. Si aggiorna da solo da src/lib/news.ts.
// Nessun dato dinamico: con Cache Components la risposta si genera una volta in fase di build.
export function GET() {
  const schede = [...ARTICOLI]
    .sort((a, b) => b.data.localeCompare(a.data))
    .map((a) =>
      [
        `### [${a.titolo}](${SITO}/news/${a.slug})`,
        `Norma: ${a.norma}. Aggiornato il ${a.aggiornato ?? a.data}.`,
        "",
        a.inBreve ?? a.descrizione,
        ...(a.domande?.length ? ["", ...a.domande.map((q) => `- ${q.d} ${q.r}`)] : []),
        "",
        `Fonti ufficiali: ${a.fonti.map((f) => `[${f.nome}](${f.url})`).join(" · ")}`,
      ].join("\n"),
    );
  const testo = [
    `# ${BRAND.azienda}`,
    "",
    `> ${BRAND.azienda} è il gestionale per autodemolizioni (centri di raccolta dei veicoli fuori uso) di ${PRODUTTORE.nome}: accettazione e pratiche RVFU, bonifica, registro rifiuti e RENTRI, formulari, magazzino ricambi e vendita online.`,
    "",
    "Le schede normative riassumono le norme italiane ed europee che toccano un'autodemolizione, con i riferimenti ufficiali. Sono informative: per il singolo impianto fa fede il testo ufficiale.",
    "",
    "## Pagine",
    "",
    `- [Il gestionale](${SITO}/scopri): cosa fa e per chi`,
    `- [Normative](${SITO}/news): tutte le schede`,
    "",
    "## Schede normative",
    "",
    schede.join("\n\n"),
    "",
  ].join("\n");
  return new Response(testo, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
}
