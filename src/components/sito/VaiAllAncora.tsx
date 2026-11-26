"use client";

import { useEffect } from "react";

// Il contenuto arriva dopo la schermata di caricamento dell'app: il browser non trova l'ancora (#clausole, #accordo…)
// e lascia la pagina in cima. Dopo il montaggio si porta all'elemento indicato dall'indirizzo, senza animazione.
export function VaiAllAncora() {
  useEffect(() => {
    const hash = window.location.hash.slice(1);
    if (!hash) return;
    let id = hash;
    try {
      id = decodeURIComponent(hash);
    } catch {
      /* ancora non decodificabile: si prova com'è */
    }
    document.getElementById(id)?.scrollIntoView({ behavior: "auto", block: "start" });
  }, []);
  return null;
}
