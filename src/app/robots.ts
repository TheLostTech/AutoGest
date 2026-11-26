import type { MetadataRoute } from "next";
import { SITO } from "@/components/sito/Sito";

// Si indicizzano solo presentazione, normative e informativa privacy; tutto il resto è il gestionale dell'azienda.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: ["/scopri", "/news", "/privacy", "/_next/", "/renders/"], disallow: ["/"] },
    sitemap: `${SITO}/sitemap.xml`,
  };
}
