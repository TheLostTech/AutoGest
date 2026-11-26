import type { MetadataRoute } from "next";
import { ARTICOLI } from "@/lib/news";
import { SITO } from "@/components/sito/Sito";
import { INFORMATIVA_PRIVACY } from "@/lib/legale/privacy";
import { CONDIZIONI } from "@/lib/legale/condizioni";

// Solo le pagine pubbliche: il gestionale vero e proprio non va nei motori di ricerca.
export default function sitemap(): MetadataRoute.Sitemap {
  const ultima = ARTICOLI.map((a) => a.aggiornato ?? a.data).sort().at(-1);
  return [
    { url: `${SITO}/scopri`, changeFrequency: "monthly", priority: 1 },
    { url: `${SITO}/news`, lastModified: ultima, changeFrequency: "weekly", priority: 0.8 },
    { url: `${SITO}/privacy`, lastModified: INFORMATIVA_PRIVACY.versione, changeFrequency: "yearly", priority: 0.3 },
    { url: `${SITO}/condizioni`, lastModified: CONDIZIONI.versione, changeFrequency: "yearly", priority: 0.3 },
    ...ARTICOLI.map((a) => ({
      url: `${SITO}/news/${a.slug}`,
      lastModified: a.aggiornato ?? a.data,
      changeFrequency: "monthly" as const,
      priority: 0.7,
    })),
  ];
}
