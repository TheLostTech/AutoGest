import type { Metadata, Viewport } from "next";
import { Barlow, Barlow_Condensed } from "next/font/google";
import "./globals.css";
import { Hydrator } from "@/components/Hydrator";
import { BRAND } from "@/lib/config";
import { PressFeedback } from "@/components/PressFeedback";
import { Conferme } from "@/components/Conferme";

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
    // suppressHydrationWarning: alcuni browser (es. Chrome su iPhone) aggiungono attributi propri a <html>
    // prima che React si attivi; vale solo per gli attributi di questo tag, non per il contenuto.
    <html lang="it" className={`${barlow.variable} ${barlowCondensed.variable} h-full antialiased`} suppressHydrationWarning>
      <body className="min-h-full">
        <PressFeedback />
        <Hydrator>
          {children}
          <Conferme />
        </Hydrator>
      </body>
    </html>
  );
}
