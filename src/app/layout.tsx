import type { Metadata, Viewport } from "next";
import { Barlow, Barlow_Condensed } from "next/font/google";
import "./globals.css";
import { Hydrator } from "@/components/Hydrator";
import { BRAND } from "@/lib/config";

const barlow = Barlow({
  variable: "--font-barlow",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const barlowCondensed = Barlow_Condensed({
  variable: "--font-barlow-condensed",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

export const metadata: Metadata = {
  title: `${BRAND.azienda} · Gestionale`,
  description: "Prototipo del gestionale integrato per autodemolizione: veicoli, smontaggio, magazzino, etichette, vendite e negozio.",
};

export const viewport: Viewport = {
  themeColor: "#1240a8",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="it" className={`${barlow.variable} ${barlowCondensed.variable} h-full antialiased`}>
      <body className="min-h-full">
        <Hydrator>{children}</Hydrator>
      </body>
    </html>
  );
}
