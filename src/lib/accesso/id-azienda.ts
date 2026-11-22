// L'id dell'azienda diventa il nome di una cartella: solo lettere, cifre, trattino e trattino basso.
export function idAziendaValido(id: string): boolean {
  return typeof id === "string" && /^[A-Za-z0-9_-]{1,64}$/.test(id);
}
