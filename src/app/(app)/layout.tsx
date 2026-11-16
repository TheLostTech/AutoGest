// L'app è renderizzata lato client (dati demo nel browser): niente validazione di navigazione istantanea.
export const instant = false;

import { AppShell } from "@/components/AppShell";

export default function AppLayout({ children }: LayoutProps<"/">) {
  return <AppShell>{children}</AppShell>;
}
