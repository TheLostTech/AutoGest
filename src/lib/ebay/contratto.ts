// Contratto tra l'app e il ponte eBay sul server. Solo tipi.
import type { Condition, Gpsr, StatoEbay, VeicoloCompat } from "../types";

export type ModoEbay = "Simulato" | "Sandbox";
export type SpedizioneEbay = "corriere" | "voluminoso" | "ritiro";
export interface RichiestaAllinea {
  sku: string; attivo: boolean; quantita: number; prezzo: number;
  titolo: string; descrizione: string; categoriaQuery: string; categoriaId?: string;
  condizione: Condition; caratteristiche: Record<string, string>; foto: string[];
  compatibilita: VeicoloCompat[]; spedizione: SpedizioneEbay; gpsr: Gpsr;
}
export interface EsitoAllinea { stato: StatoEbay; listingId?: string; url?: string; categoria?: { id: string; nome: string }; avvisi: string[]; errore?: string;
  /** eBay ha rifiutato la categoria usata: l'app dimentica quella proposta da eBay */
  categoriaRifiutata?: boolean }
export interface VenditaEbay { orderId: string; sku: string; quantita: number; prezzoUnitario: number; acquirente: string; at: string }
export interface StatoPonte { modo: ModoEbay; collegato: boolean; esauritoAttivo?: boolean; politiche?: Record<"pagamento" | "reso" | SpedizioneEbay, { id: string; nome: string } | undefined>; errore?: string }
export interface Ponte { allinea(r: RichiestaAllinea): Promise<EsitoAllinea>; vendite(da: string): Promise<VenditaEbay[]>; stato(): Promise<StatoPonte> }
