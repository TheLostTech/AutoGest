import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  devIndicators: false,
  // Apertura dal telefono sulla rete locale (es. http://192.168.1.100:3210):
  // senza questa voce Next blocca il canale di sviluppo e la pagina resta in caricamento.
  allowedDevOrigins: ["192.168.*.*", "10.*.*.*", "*.local"],
  cacheComponents: true,
  // Certificato di Supabase letto a runtime con fs (db/pool.ts): non è un import, quindi va incluso a mano
  // nei file di ogni funzione (su Vercel). '/*' con contains: tutte le route.
  outputFileTracingIncludes: { "/*": ["src/lib/db/supabase-ca.crt"] },
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
