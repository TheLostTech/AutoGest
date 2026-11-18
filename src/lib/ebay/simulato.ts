// Ponte eBay simulato: nessuna chiamata vera, numero e link finti. Modulo puro.
import type { EsitoAllinea, Ponte, RichiestaAllinea, StatoPonte, VenditaEbay } from "./contratto";

const attesa = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export function creaPonteSimulato(): Ponte {
  return {
    async allinea(r: RichiestaAllinea): Promise<EsitoAllinea> {
      await attesa(300);
      // Errore di prova: così si vede come l'app tratta un rifiuto di eBay
      if (Math.round(r.prezzo * 100) % 100 === 13) {
        return { stato: "errore", avvisi: [], errore: "eBay simulato: il prezzo non è accettato (prova di errore: i centesimi sono ,13)" };
      }
      const stato = !r.attivo ? "ritirato" : r.quantita === 0 ? "esaurito" : "online";
      return {
        stato,
        listingId: `SIM-${r.sku}`,
        url: `/ebay-simulato/${encodeURIComponent(r.sku)}`,
        categoria: r.categoriaId ? { id: r.categoriaId, nome: "Categoria scelta" } : { id: "33710", nome: "Ricambi auto (simulata)" },
        avvisi: [],
      };
    },
    async vendite(): Promise<VenditaEbay[]> {
      return [];
    },
    async stato(): Promise<StatoPonte> {
      return { modo: "Simulato", collegato: true, esauritoAttivo: true };
    },
  };
}
