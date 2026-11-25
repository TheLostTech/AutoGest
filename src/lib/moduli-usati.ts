// Moduli usati davvero durante la prova (spec prova-15-giorni, sezione 4): il riquadro di pagamento li propone già
// spuntati. Un modulo è usato se nell'archivio c'è almeno un dato che solo quel modulo salva. Modulo puro: legge lo
// stato salvato così com'è e non si fida dei campi (assenti o non validi non contano e non fanno errori).
import { ORDINE_MODULI, type Modulo } from "./moduli.ts";

type Oggetto = Record<string, unknown>;

const oggetti = (v: unknown): Oggetto[] =>
  Array.isArray(v) ? v.filter((x): x is Oggetto => !!x && typeof x === "object" && !Array.isArray(x)) : [];

const oggetto = (v: unknown): Oggetto | null => (v && typeof v === "object" && !Array.isArray(v) ? (v as Oggetto) : null);

// Pratica avviata dall'Accettazione: documenti ricevuti, visura, radiazione, distruzione, documento di chi consegna,
// oppure la pratica non più "da registrare". La pratica vuota c'è in ogni veicolo; chi consegna, il numero del
// certificato e la presa in carico li scrive anche Ambiente (dati per il registro), quindi da soli non contano.
function praticaAvviata(v: Oggetto): boolean {
  if (Array.isArray(v.documenti) && v.documenti.length > 0) return true;
  if (oggetto(v.visura) || oggetto(v.visuraRichiesta) || oggetto(v.radiazione) || oggetto(v.distruzione)) return true;
  if (typeof oggetto(v.conferente)?.documento === "string") return true;
  const stato = oggetto(v.dossier)?.status;
  return typeof stato === "string" && stato !== "da registrare";
}

// Registro rifiuti scritto con Ambiente: ogni registrazione tranne il carico d'ingresso (causale *T), che nasce da sola
// all'ingresso del veicolo anche con il solo Magazzino. Oppure una bonifica con i materiali (quella "semplice" è del
// Magazzino).
function ambienteUsato(state: Oggetto): boolean {
  if (oggetti(state.firs).length > 0) return true;
  if (oggetti(state.wasteMoves).some((m) => m.causale !== "*T")) return true;
  return oggetti(state.vehicles).some((v) => {
    const b = oggetto(v.bonifica);
    return !!b && b.semplice !== true;
  });
}

// Vendite: una vendita al banco (gli ordini del negozio e di eBay sono del Magazzino) o un preventivo.
function venditeUsate(state: Oggetto): boolean {
  return oggetti(state.orders).some((o) => o.channel === "banco") || oggetti(state.docs).some((d) => d.type === "preventivo");
}

export function moduliUsati(state: Record<string, unknown> | null): Modulo[] {
  const usati = new Set<Modulo>(["magazzino"]);
  const s = oggetto(state);
  if (s) {
    if (oggetti(s.vehicles).some(praticaAvviata)) usati.add("accettazione");
    if (ambienteUsato(s)) usati.add("ambiente");
    if (venditeUsate(s)) usati.add("vendite");
  }
  return ORDINE_MODULI.filter((m) => usati.has(m));
}
