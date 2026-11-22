// Carte di prova di Stripe, mostrate solo con le chiavi di prova (spec registrazione-pagamento, sezione 7).
export const CARTE_DI_PROVA: { numero: string; cosa: string }[] = [
  { numero: "4242 4242 4242 4242", cosa: "pagamento riuscito (scadenza futura e CVC qualunque)" },
  { numero: "4000 0027 6000 3184", cosa: "chiede il codice della banca (3D Secure)" },
  { numero: "4000 0000 0000 0341", cosa: "la carta si salva ma l'addebito fallisce al rinnovo" },
];
