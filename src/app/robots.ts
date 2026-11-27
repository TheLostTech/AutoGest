import type { MetadataRoute } from "next";
import { SITO } from "@/components/sito/Sito";

// Si indicizzano solo presentazione, normative, informativa privacy, condizioni del servizio e llms.txt (indice per gli
// assistenti AI); tutto il resto è il gestionale dell'azienda.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: ["/$", "/scopri", "/news", "/privacy", "/condizioni", "/llms.txt", "/_next/", "/renders/"], disallow: ["/"] },
    sitemap: `${SITO}/sitemap.xml`,
  };
}
