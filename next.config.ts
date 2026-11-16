import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  devIndicators: false,
  // Apertura dal telefono sulla rete locale (es. http://192.168.1.100:3210):
  // senza questa voce Next blocca il canale di sviluppo e la pagina resta in caricamento.
  allowedDevOrigins: ["192.168.*.*", "10.*.*.*", "*.local"],
  cacheComponents: true,
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
