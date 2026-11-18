// Copie locali dell'archivio nel browser (localStorage): una per azienda, chiave "<schema>:<id azienda>".
// All'ingresso in un'azienda si tolgono le copie delle altre aziende e quelle di versioni vecchie dello schema
// (cambio di azienda = dati locali svuotati). Restano solo le code delle modifiche in sospeso ("…:in-sospeso") dello
// schema attuale: sono lavoro non ancora inviato, partono al prossimo ingresso in quell'azienda e dopo 24 ore si scartano.
// Puro.

/** Famiglia delle chiavi dell'archivio: lo schema senza il numero di versione finale (es. "gestionale-demolizione-demo-"). */
const famiglia = (schema: string) => schema.replace(/v\d+$/, "");

export function chiaviDaTogliere(chiavi: string[], schema: string, aziendaId: string): string[] {
  const pref = famiglia(schema);
  const mia = `${schema}:${aziendaId}`;
  return chiavi.filter((k) => {
    if (!k.startsWith(pref) || !k.includes(":")) return false;
    if (k === mia || k === `${mia}:in-sospeso`) return false;
    // Modifiche in sospeso di un'altra azienda, stesso schema: si tengono
    if (k.startsWith(`${schema}:`) && k.endsWith(":in-sospeso")) return false;
    return true;
  });
}
