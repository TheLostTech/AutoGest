// La vista è un componente client che legge l'abbonamento e la sessione dal browser: sul server non produce contenuto,
// quindi questa pagina esce dalla validazione di navigazione istantanea (vedi instant.md nei docs di Next).
export const instant = false;

export { default } from "./view";
