// Stime dei componenti della bonifica per modello, senza dipendenze (testate con `npm test`).
// Servono a tenere aggiornata la giacenza auto per auto: il peso vero arriva con la pesata del contenitore
// all'uscita (formulario) e la differenza si registra da sola.
// Coefficienti DIMOSTRATIVI ricavati da massa, alimentazione e anno: nel prodotto arriveranno dai dati tecnici
// del veicolo (catalogo ricambi / banca dati per targa: capacità batteria, misura pneumatici, litri dei liquidi).

export interface Profilo {
  massaKg: number; // massa da libretto (campo G)
  fuel: string;
  year: number;
}

export type Voce = "batteria" | "carburante" | "oli" | "freni" | "antigelo" | "gas" | "filtro" | "airbag" | "catalizzatore" | "pneumatici";

const r1 = (n: number) => Math.round(n * 10) / 10;
const r2 = (n: number) => Math.round(n * 100) / 100;
const clamp = (n: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, n));

export function stimaComponenti(p: Profilo): Record<Voce, { qty: number; kgPerUnit: number }> {
  const m = p.massaKg > 0 ? p.massaKg : 1000;
  const diesel = p.fuel === "Diesel";
  return {
    batteria: { qty: 1, kgPerUnit: clamp(Math.round(8 + m * 0.007 + (diesel ? 3 : 0)), 11, 25) },
    carburante: { qty: 6, kgPerUnit: diesel ? 0.84 : 0.74 }, // residuo tipico nel serbatoio
    oli: { qty: r1(2.5 + m / 500 + (diesel ? 1 : 0)), kgPerUnit: 0.88 },
    freni: { qty: 0.5, kgPerUnit: 1.05 },
    antigelo: { qty: r1(3 + m / 400), kgPerUnit: 1.07 },
    gas: { qty: r2(0.35 + m / 4000), kgPerUnit: 1 },
    filtro: { qty: 1, kgPerUnit: 0.4 },
    airbag: { qty: p.year >= 2008 ? (m > 1100 ? 6 : 4) : 2, kgPerUnit: 1.2 },
    catalizzatore: { qty: 1, kgPerUnit: r1(3 + m / 500 + (diesel ? 2 : 0)) },
    pneumatici: { qty: 4, kgPerUnit: clamp(r1(4 + m * 0.004), 6, 12) },
  };
}

// Pesa e libretto molto diversi (oltre il 25%): spesso un errore di battitura o un'auto incompleta
export const pesoDiverso = (pesaKg: number, librettoKg: number) => librettoKg > 0 && Math.abs(pesaKg - librettoKg) / librettoKg > 0.25;

// Quanto aggiungere (positivo) o togliere (negativo) alla giacenza stimata per tornare al peso pesato
export const differenzaPesata = (giacenzaKg: number, pesatoKg: number) => r1(pesatoKg - giacenzaKg);
