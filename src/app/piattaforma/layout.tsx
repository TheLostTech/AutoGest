// L'area Piattaforma ha il suo guscio: niente AppShell della gestione e nessun dato di un'azienda.
export const instant = false;

import type { Metadata } from "next";
import { Guscio } from "./comune";

export const metadata: Metadata = { title: "Piattaforma · Gestionale" };

export default function PiattaformaLayout({ children }: LayoutProps<"/piattaforma">) {
  return <Guscio>{children}</Guscio>;
}
