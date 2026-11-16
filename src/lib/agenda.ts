// Coda "Da fare": le attività nascono dai dati, non da una lista compilata a mano.
// Ogni voce ha un ruolo destinatario, una scadenza (se esiste) e porta all'azione.
import { typeById } from "./catalog";
import { eerByCode, fmtKg, stockByEer } from "./ambiente";
import type { Fir, Order, Part, Role, SalesDoc, StockRule, Vehicle, WasteMove } from "./types";

export type Urgency = "scaduto" | "oggi" | "settimana" | "quando-puoi";

export interface AgendaItem {
  id: string;
  title: string;
  detail: string;
  action: string; // verbo del pulsante
  href: string;
  due?: string; // ISO
  roles: Role[];
  kind: "veicolo" | "pratica" | "ricambi" | "ordine" | "scorte" | "ambiente";
}

// Termini dimostrativi, da configurare per impianto e da validare con il consulente.
export const TERMS = {
  verificaIdentita: 1, // giorni dall'ingresso
  registraPratica: 2,
  radiazione: 30,
  bozza: 2,
  posizione: 1,
  pagamento: 2, // dopo questo termine la riserva va rivista
  spedizione: 1,
  preventivo: 5, // giorni dopo i quali richiamare il cliente
  bonifica: 10,
  rentri: 2,
};

const DAY = 864e5;
const addDays = (iso: string, d: number) => new Date(new Date(iso).getTime() + d * DAY).toISOString();
const oldest = (xs: { createdAt: string }[]) => xs.map((x) => x.createdAt).sort()[0];

export function urgencyOf(due: string | undefined, now = new Date()): Urgency {
  if (!due) return "quando-puoi";
  const d = new Date(due);
  const endOfToday = new Date(now);
  endOfToday.setHours(23, 59, 59, 999);
  const startOfToday = new Date(now);
  startOfToday.setHours(0, 0, 0, 0);
  if (d < startOfToday) return "scaduto";
  if (d <= endOfToday) return "oggi";
  if (d.getTime() - endOfToday.getTime() <= 7 * DAY) return "settimana";
  return "quando-puoi";
}

export function buildAgenda(
  {
    vehicles,
    parts,
    orders,
    rules,
    activeVehicleId,
    wasteMoves = [],
    firs = [],
    docs = [],
  }: { vehicles: Vehicle[]; parts: Part[]; orders: Order[]; rules: StockRule[]; activeVehicleId?: string; wasteMoves?: WasteMove[]; firs?: Fir[]; docs?: SalesDoc[] },
  role: Role,
): AgendaItem[] {
  const items: AgendaItem[] = [];
  const name = (v: Vehicle) => `${v.make} ${v.model} · ${v.plate}`;

  // Veicoli e pratiche
  for (const v of vehicles) {
    if (v.verification === "da verificare")
      items.push({
        id: `verifica-${v.id}`,
        kind: "veicolo",
        title: `Verifica identificazione ${v.id}`,
        detail: `${name(v)}${v.notes ? ` · ${v.notes}` : ""}`,
        action: "Verifica",
        href: `/veicoli/${v.id}`,
        due: addDays(v.intakeAt, TERMS.verificaIdentita),
        roles: ["accettazione", "responsabile"],
      });
    if (v.visura?.fermo)
      items.push({
        id: `fermo-${v.id}`,
        kind: "pratica",
        title: `Fermo amministrativo su ${v.id}`,
        detail: `${name(v)} · presa in carico bloccata: contatta chi conferisce`,
        action: "Apri pratica",
        href: `/veicoli/${v.id}#pratica`,
        due: v.visura.at,
        roles: ["accettazione", "responsabile"],
      });
    else if (!v.presaInCarico)
      items.push({
        id: `pratica-${v.id}`,
        kind: "pratica",
        title: `Completa la presa in carico di ${v.id}`,
        detail: `${name(v)} · ${!v.conferente ? "conferente e documenti da registrare" : !v.visura ? "visura PRA da fare" : "certificato da generare"}`,
        action: "Apri pratica",
        href: `/veicoli/${v.id}#pratica`,
        due: addDays(v.intakeAt, TERMS.registraPratica),
        roles: ["accettazione", "responsabile"],
      });
    else if (v.radiazione?.stato !== "completata")
      items.push({
        id: `radiazione-${v.id}`,
        kind: "pratica",
        title: v.radiazione?.stato === "richiesta" ? `Registra l'esito della radiazione di ${v.id}` : `Richiedi la radiazione di ${v.id}`,
        detail: `${name(v)} · pratica ${v.dossier.number}`,
        action: "Apri pratica",
        href: `/veicoli/${v.id}#pratica`,
        due: addDays(v.intakeAt, TERMS.radiazione),
        roles: ["accettazione", "responsabile"],
      });
    if (!v.bonifica)
      items.push({
        id: `bonifica-${v.id}`,
        kind: "ambiente",
        title: `Bonifica ${v.id}`,
        detail: `${name(v)} · liquidi, batteria, airbag, catalizzatore, pneumatici`,
        action: "Bonifica",
        href: `/veicoli/${v.id}/bonifica`,
        due: addDays(v.intakeAt, TERMS.bonifica),
        roles: ["smontatore", "responsabile"],
      });
    if (v.work === "accettato" && v.bonifica)
      items.push({
        id: `smonta-${v.id}`,
        kind: "veicolo",
        title: `Avvia lo smontaggio di ${v.id}`,
        detail: `${name(v)} · in piazzale dal ${new Date(v.intakeAt).toLocaleDateString("it-IT", { day: "numeric", month: "short" })}`,
        action: "Avvia",
        href: `/campo/${v.id}`,
        roles: ["smontatore", "responsabile"],
      });
    if (v.work === "in smontaggio" && v.id === activeVehicleId)
      items.push({
        id: `riprendi-${v.id}`,
        kind: "veicolo",
        title: `Riprendi lo smontaggio di ${v.id}`,
        detail: `${name(v)} · ${parts.filter((p) => p.vehicleId === v.id).length} pezzi catalogati finora`,
        action: "Riprendi",
        href: `/campo/${v.id}`,
        due: new Date().toISOString(),
        roles: ["smontatore"],
      });
  }

  // Ricambi: raggruppati, perché sono tanti e si lavorano in serie
  const drafts = parts.filter((p) => p.status === "bozza");
  if (drafts.length)
    items.push({
      id: "bozze",
      kind: "ricambi",
      title: `Approva ${drafts.length} ${drafts.length === 1 ? "scheda in bozza" : "schede in bozza"}`,
      detail: "Controlla foto, condizioni e prezzo prima che diventino vendibili",
      action: "Controlla",
      href: "/pubblicazione",
      due: addDays(oldest(drafts), TERMS.bozza),
      roles: ["responsabile"],
    });
  const noLoc = parts.filter((p) => p.status === "disponibile" && !p.location);
  if (noLoc.length)
    items.push({
      id: "posizioni",
      kind: "ricambi",
      title: `Metti a scaffale ${noLoc.length} ${noLoc.length === 1 ? "ricambio" : "ricambi"}`,
      detail: noLoc.slice(0, 3).map((p) => p.id).join(", ") + (noLoc.length > 3 ? "…" : ""),
      action: "Assegna",
      href: "/ricambi?filtro=senza-posizione",
      due: addDays(oldest(noLoc), TERMS.posizione),
      roles: ["magazziniere", "responsabile"],
    });
  const noLabel = parts.filter((p) => p.labelPrints === 0 && p.status !== "scartato" && p.status !== "venduto");
  if (noLabel.length)
    items.push({
      id: "etichette",
      kind: "ricambi",
      title: `Stampa ${noLabel.length} ${noLabel.length === 1 ? "etichetta" : "etichette"}`,
      detail: noLabel.slice(0, 3).map((p) => p.id).join(", ") + (noLabel.length > 3 ? "…" : ""),
      action: "Stampa",
      href: `/ricambi/${noLabel[0].id}`,
      roles: ["magazziniere", "smontatore"],
    });
  const offline = parts.filter((p) => p.status === "disponibile" && p.listing !== "pubblicato");
  if (offline.length)
    items.push({
      id: "online",
      kind: "ricambi",
      title: `Porta online ${offline.length} ${offline.length === 1 ? "ricambio disponibile" : "ricambi disponibili"}`,
      detail: "Sono in magazzino ma non si vedono sul negozio",
      action: "Pubblica",
      href: "/pubblicazione",
      roles: ["responsabile", "vendite"],
    });

  // Scorte sotto la soglia minima
  const low = rules.filter((r) => r.min > 0 && parts.filter((p) => p.typeId === r.typeId && p.status === "disponibile").length < r.min);
  if (low.length)
    items.push({
      id: "scorte",
      kind: "scorte",
      title: `${low.length} ${low.length === 1 ? "tipologia sotto" : "tipologie sotto"} la scorta minima`,
      detail: low.slice(0, 3).map((r) => typeById(r.typeId).name).join(", ") + (low.length > 3 ? "…" : "") + " · da privilegiare nei prossimi smontaggi",
      action: "Vedi",
      href: "/regole",
      roles: ["responsabile"],
    });

  // Ordini
  for (const o of orders) {
    if (o.status === "in attesa di pagamento")
      items.push({
        id: `paga-${o.id}`,
        kind: "ordine",
        title: `Incassa l'ordine ${o.id}`,
        detail: `${o.customer} · ${o.partIds.length} ${o.partIds.length === 1 ? "pezzo riservato" : "pezzi riservati"} · ${o.channel}`,
        action: "Apri",
        href: "/vendite",
        due: addDays(o.createdAt, TERMS.pagamento),
        roles: ["vendite", "responsabile"],
      });
    if (o.status === "pagato")
      items.push({
        id: `spedisci-${o.id}`,
        kind: "ordine",
        title: o.channel === "banco" ? `Consegna l'ordine ${o.id}` : `Prepara e spedisci ${o.id}`,
        detail: `${o.customer} · ${o.partIds.join(", ")}`,
        action: o.channel === "banco" ? "Consegna" : "Spedisci",
        href: "/vendite",
        due: addDays(o.createdAt, TERMS.spedizione),
        roles: ["vendite", "magazziniere", "responsabile"],
      });
  }

  for (const d of docs.filter((x) => x.type === "preventivo" && x.status === "aperto"))
    items.push({
      id: `preventivo-${d.id}`,
      kind: "ordine",
      title: `Richiama ${d.customer.name} per il preventivo`,
      detail: `${d.id} · ${d.lines.length} ${d.lines.length === 1 ? "pezzo" : "pezzi"} · ${d.total} € · i pezzi non sono riservati`,
      action: "Apri",
      href: "/vendite/documenti",
      due: addDays(d.at, TERMS.preventivo),
      roles: ["vendite", "responsabile"],
    });

  // Ambiente: registro, formulari e limiti dell'autorizzazione
  const pending = wasteMoves.filter((m) => m.rentri === "da trasmettere");
  if (pending.length)
    items.push({
      id: "rentri",
      kind: "ambiente",
      title: `Trasmetti ${pending.length} movimenti al RENTRI`,
      detail: "Generati da ingressi, bonifiche e formulari: controlla e invia",
      action: "Trasmetti",
      href: "/ambiente",
      due: addDays(pending.map((m) => m.at).sort()[0], TERMS.rentri),
      roles: ["accettazione", "responsabile"],
    });
  for (const f of firs) {
    if (f.status === "da firmare")
      items.push({
        id: `firma-${f.id}`,
        kind: "ambiente",
        title: `Firma il formulario ${f.id}`,
        detail: `${eerByCode(f.eer)?.short} · ${fmtKg(f.kg)} → ${f.destinatario}`,
        action: "Firma",
        href: "/ambiente/formulari",
        due: f.at,
        roles: ["accettazione", "responsabile"],
      });
    if (f.status === "firmato")
      items.push({
        id: `fir-rentri-${f.id}`,
        kind: "ambiente",
        title: `Trasmetti il formulario ${f.id}`,
        detail: `${eerByCode(f.eer)?.short} · ${fmtKg(f.kg)} · ${f.destinatario}`,
        action: "Trasmetti",
        href: "/ambiente/formulari",
        due: addDays(f.at, 1),
        roles: ["accettazione", "responsabile"],
      });
  }
  for (const st of stockByEer(wasteMoves).filter((x) => x.pct >= 0.8 && x.code !== "16 01 04*"))
    items.push({
      id: `limite-${st.code}`,
      kind: "ambiente",
      title: `Programma il ritiro: ${st.short.toLowerCase()} al ${Math.round(st.pct * 100)}% del limite`,
      detail: `${fmtKg(st.kg)} su ${fmtKg(st.limitKg)} autorizzati · ${st.code}`,
      action: "Formulario",
      href: `/ambiente/formulari?eer=${encodeURIComponent(st.code)}`,
      due: addDays(new Date().toISOString(), st.pct >= 0.95 ? 0 : 3),
      roles: ["accettazione", "responsabile"],
    });

  const rank: Record<Urgency, number> = { scaduto: 0, oggi: 1, settimana: 2, "quando-puoi": 3 };
  return items
    .filter((i) => i.roles.includes(role))
    .sort((a, b) => rank[urgencyOf(a.due)] - rank[urgencyOf(b.due)] || (a.due ?? "~").localeCompare(b.due ?? "~"));
}
