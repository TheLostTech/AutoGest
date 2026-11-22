// Regola pura: il dispositivo può mandare al server il proprio stato locale intero solo se l'azienda è demo
// e sul server lo stato manca o ha uno schema diverso. Un'azienda vera non viene mai riempita dal browser.
export function devePubblicareStatoLocale(server: { state: unknown; schema: string; demo: boolean }, schemaLocale: string): boolean {
  if (!server.demo) return false;
  return !server.state || server.schema !== schemaLocale;
}
